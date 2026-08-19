"""
beat_sim.py -- simulador de referencia del motor BEAT, fiel a BEAT.asm.

No emula x86: reimplementa la semantica del motor instruccion por instruccion,
incluida la aritmetica del temporizador 8253, para poder oir un programa BEAT
sin arrancar el diskette. Emite WAV de onda cuadrada, que es literalmente lo
que hace el altavoz interno.

Fidelidad al hardware:
  - la frecuencia que suena NO es la pedida: el 8253 recibe un divisor entero
    div = 1193182 // f, y emite 1193182 / div.
  - las duraciones se miden en ticks del BIOS de 18.2065 Hz.
"""

import struct
import wave

PIT_HZ = 1193182.0          # frecuencia base del temporizador 8253
TICK_HZ = 1193182.0 / 65536  # 18.2065 Hz -- el tick del BIOS (INT 1Ah)

TEMPO_TABLE = [60, 80, 100, 120, 140, 160, 180, 200, 220, 240]
NOTE_TABLE = [262, 277, 294, 311, 330, 349, 370, 392, 415, 440, 466, 494]

TAPE_SIZE = 2048


class BeatMachine:
    """Ejecuta un programa BEAT y produce una lista de (freq_hz, segundos).

    freq_hz == 0 significa silencio.
    """

    def __init__(self, program: bytes, max_steps: int = 2_000_000):
        if len(program) > 511:
            raise ValueError(f"el programa excede el sector 4: {len(program)} > 511 bytes")
        self.prog = program + b"\x00"
        self.max_steps = max_steps
        # estado, igual que el bloque en 0x0500
        self.ip = 0
        self.reg = 0
        self.tempo = 120
        self.dur = 4
        self.tapep = 0
        self.tape = bytearray(TAPE_SIZE)
        self.score: list[tuple[float, float]] = []
        self.steps = 0
        # `S` hace `xor al,3` sobre el puerto 61h: alterna. Como el divisor
        # del 8253 sigue cargado con la ultima nota, encender deja ese tono
        # sonando indefinidamente -- un drone, no un mute.
        self.speaker = False
        self.last_freq = 0.0

    # -- temporizacion -----------------------------------------------------
    def dur_ticks(self) -> int:
        """Replica dur_ticks del asm: (1092 / BPM) * D / 4, minimo 1."""
        ticks = ((1092 // self.tempo) * self.dur) >> 2
        return max(1, ticks)

    def dur_seconds(self) -> float:
        return self.dur_ticks() / TICK_HZ

    def emit(self, freq: int):
        """Toca el registro como frecuencia, pasando por el divisor del 8253."""
        secs = self.dur_seconds()
        # Igual que el motor: por debajo de 19 Hz el divisor del 8253 se sale
        # de 16 bits y `div` desborda. No hay nota, hay silencio.
        if freq < 19:
            self.silence(secs)
            return
        divisor = int(PIT_HZ / freq) & 0xFFFF
        real = PIT_HZ / divisor if divisor else 0.0
        self.last_freq = real
        self.score.append((real, secs))

    def silence(self, secs: float):
        """Un hueco solo suena a nada si el drone de `S` esta apagado."""
        self.score.append((self.last_freq if self.speaker else 0.0, secs))

    # -- ejecucion ---------------------------------------------------------
    def peek(self, i: int) -> int:
        return self.prog[i] if 0 <= i < len(self.prog) else 0

    def run(self):
        while True:
            self.steps += 1
            if self.steps > self.max_steps:
                raise RuntimeError("limite de pasos: el programa no termina")
            op = self.peek(self.ip)
            if op == 0:
                return
            self.ip += 1
            c = chr(op)

            if c == ">":
                self.tapep = (self.tapep + 1) % TAPE_SIZE
            elif c == "<":
                self.tapep = (self.tapep - 1) % TAPE_SIZE
            elif c == "+":
                self.reg = (self.reg + 1) & 0xFFFF
            elif c == "-":
                self.reg = (self.reg - 1) & 0xFFFF
            elif c == ".":
                self.emit(self.reg)
            elif c == ",":
                # entrada de teclado: sin consola, se trata como silencio
                self.reg = 0
            elif c == "[":
                if self.reg == 0:
                    depth = 1
                    while depth:
                        ch = self.peek(self.ip)
                        if ch == 0:
                            return
                        self.ip += 1
                        if ch == ord("["):
                            depth += 1
                        elif ch == ord("]"):
                            depth -= 1
            elif c == "]":
                if self.reg != 0:
                    # el asm rebobina desde ip-2 buscando el '[' que empareja
                    i = self.ip - 2
                    depth = 1
                    while i >= 0:
                        ch = self.peek(i)
                        if ch == ord("]"):
                            depth += 1
                        elif ch == ord("["):
                            depth -= 1
                            if depth == 0:
                                break
                        i -= 1
                    if i < 0:
                        return
                    self.ip = i + 1
            elif c == "T":
                d = self.peek(self.ip) - 0x30
                self.ip += 1
                if 0 <= d <= 9:
                    self.tempo = TEMPO_TABLE[d]
            elif c == "D":
                d = self.peek(self.ip) - 0x30
                self.ip += 1
                if 0 <= d <= 9:
                    self.dur = d
            elif c == "P":
                self.silence(self.dur_seconds())
            elif c == "R":
                self.reg = self.tape[self.tapep]
            elif c == "W":
                self.tape[self.tapep] = self.reg & 0xFF
            elif c == "J":
                lo, hi = self.peek(self.ip), self.peek(self.ip + 1)
                self.ip = (lo | (hi << 8)) - 0x0600
            elif c == "Z":
                lo, hi = self.peek(self.ip), self.peek(self.ip + 1)
                if self.reg == 0:
                    self.ip = (lo | (hi << 8)) - 0x0600
                else:
                    self.ip += 2
            elif c == "S":
                self.speaker = not self.speaker
            elif c == "N":
                # parseo decimal ASCII: N440 -> 440
                val = 0
                while True:
                    ch = self.peek(self.ip)
                    if not (0x30 <= ch <= 0x39):
                        break
                    val = val * 10 + (ch - 0x30)
                    self.ip += 1
                self.reg = val & 0xFFFF
            elif c == "H":
                return
            # cualquier otro byte es no-op


def render_wav(score, path: str, rate: int = 44100, amp: int = 9000):
    """Onda cuadrada pura -- el altavoz interno solo sabe hacer eso."""
    frames = bytearray()
    for freq, secs in score:
        n = int(rate * secs)
        if freq <= 0:
            frames.extend(b"\x00\x00" * n)
            continue
        period = rate / freq
        for i in range(n):
            # envolvente corta al final para evitar el chasquido del corte
            env = 1.0
            tail = n - i
            if tail < 200:
                env = tail / 200.0
            v = amp if (i % period) < (period / 2) else -amp
            frames.extend(struct.pack("<h", int(v * env)))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
    return sum(s for _, s in score)


if __name__ == "__main__":
    import sys

    prog = sys.argv[1].encode() if len(sys.argv) > 1 else b"T4D9N440.N494.N523.N587.N659.N698.N784.H"
    out = sys.argv[2] if len(sys.argv) > 2 else "beat.wav"
    m = BeatMachine(prog)
    m.run()
    total = render_wav(m.score, out)
    print(f"programa: {len(prog)} bytes")
    print(f"eventos : {len(m.score)}")
    print(f"duracion: {total:.2f} s -> {out}")
    for freq, secs in m.score[:12]:
        print(f"  {freq:8.1f} Hz  {secs*1000:6.1f} ms")
