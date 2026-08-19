"""
flow2beat.py -- compila un ExecutionTrace de FlowGen a un programa BEAT.

FlowGen escanea un repositorio, lo compila a un programa FLOW (una imagen PNG
que es un campo vectorial) y lo ejecuta en la VM real de FLOW. El resultado es
un trace: particulas que nacen, se mueven, giran, ejecutan y mueren.

Este compilador traduce ese trace a los 511 bytes del sector 4 de BEAT. El
disco arranca sin sistema operativo y toca por el altavoz interno el flujo de
particulas del repositorio escaneado.

Mapeo:
    altura        <- posicion Y de la particula (arriba = agudo), cuantizada a
                     una escala pentatonica de cinco octavas
    voz           <- pid; varias particulas vivas en el mismo tick se emiten
                     como arpegio rapido (multiplexacion por division de
                     tiempo: el altavoz es monofonico, el oido no)
    PARTICLE_DEATH-> silencio (P)
    STATE_CHANGE  -> el valor pasa por la cinta (W ... R .), usando la mitad
                     Brainfuck del lenguaje como memoria musical
    tempo         <- densidad de eventos del trace

El presupuesto es duro: 511 bytes mas el NUL. Lo que no cabe, no suena.
"""

import json
from collections import defaultdict

SECTOR_BUDGET = 511

# Pentatonica mayor de Do sobre cinco octavas. Cualquier subconjunto suena
# consonante, que es lo que permite arpegiar particulas sin pedir permiso.
SCALE = [
    131, 147, 165, 196, 220,
    262, 294, 330, 392, 440,
    523, 587, 659, 784, 880,
    1047,
]

# Indice en tempo_table del motor: 60,80,100,120,140,160,180,200,220,240 BPM
TEMPO_SLOW, TEMPO_MID, TEMPO_FAST = 1, 4, 7


def load_events(trace_path: str):
    with open(trace_path, encoding="utf-8") as fh:
        trace = json.load(fh)
    return trace["events"], trace.get("metadata", {})


def y_range(events):
    ys = []
    for e in events:
        p = e.get("payload", {})
        for key in ("y", "y_to", "y_from"):
            if key in p:
                ys.append(p[key])
                break
    if not ys:
        return 0.0, 1.0
    lo, hi = min(ys), max(ys)
    return (lo, hi) if hi > lo else (lo, lo + 1.0)


def event_y(e):
    p = e.get("payload", {})
    for key in ("y", "y_to", "y_from"):
        if key in p:
            return p[key]
    return None


def pitch_for(y, lo, hi):
    """Y crece hacia abajo en FLOW, asi que arriba tiene que sonar agudo."""
    frac = (y - lo) / (hi - lo)
    idx = int(round((1.0 - frac) * (len(SCALE) - 1)))
    return SCALE[max(0, min(len(SCALE) - 1, idx))]


def spread(pitches):
    """Grave, media y aguda del enjambre.

    Quedarse con las tres primeras aplastaria el acorde contra el registro
    grave: lo que interesa es cuanto se ha dispersado la nube de particulas,
    no donde empieza.
    """
    uniq = sorted(set(pitches))
    if len(uniq) <= 3:
        return uniq
    return [uniq[0], uniq[len(uniq) // 2], uniq[-1]]


def compile_trace(events, arpeggio=True):
    """Devuelve el programa BEAT como bytes, recortado al sector."""
    lo, hi = y_range(events)

    by_tick = defaultdict(list)
    for e in events:
        by_tick[e["tick"]].append(e)

    density = len(events) / max(1, len(by_tick))
    tempo = TEMPO_FAST if density > 12 else TEMPO_MID if density > 6 else TEMPO_SLOW

    out = bytearray()
    out += f"T{tempo}".encode()
    cur_dur = None

    def set_dur(d):
        nonlocal cur_dur
        if d != cur_dur:
            out.extend(f"D{d}".encode())
            cur_dur = d

    def note(freq, dur):
        set_dur(dur)
        out.extend(f"N{freq}.".encode())

    for tick in sorted(by_tick):
        evs = by_tick[tick]

        deaths = [e for e in evs if e["type"] == "PARTICLE_DEATH"]
        states = [e for e in evs if e["type"] == "STATE_CHANGE"]
        turns = [e for e in evs if e["type"] == "PARTICLE_TURN"]
        # una voz por particula viva, ordenada por pid para que sea determinista
        voices = {}
        for e in evs:
            if e["type"] in ("PARTICLE_SPAWN", "INSTRUCTION_EXECUTED", "PARTICLE_MOVE"):
                y = event_y(e)
                if y is not None:
                    voices.setdefault(e["pid"], y)

        pitches = [pitch_for(voices[pid], lo, hi) for pid in sorted(voices)]

        if not pitches and not deaths and not states:
            continue

        if len(pitches) <= 1:
            for f in pitches:
                note(f, 4)
        elif arpeggio:
            # acorde por multiplexacion: notas cortas repetidas dos vueltas.
            # el altavoz sigue siendo monofonico; a esta velocidad se percibe
            # como una triada.
            for _ in range(2):
                for f in spread(pitches):
                    note(f, 1)
        else:
            for f in spread(pitches):
                note(f, 2)

        # un giro de particula es un acento: nota mas larga sobre la mas aguda
        if turns and pitches:
            note(max(pitches), 6)

        # el estado de la particula viaja por la cinta antes de sonar
        for e in states[:1]:
            val = e["payload"].get("to", 0)
            # 19 Hz es el suelo del 8253; por debajo el motor no toca nada
            if 19 <= val < 256:
                out.extend(f"N{val}".encode())  # el estado crudo, 0-255
                out.extend(b"W")               # a la celda de la cinta
                out.extend(b"R.")              # releido y tocado como frecuencia

        # la muerte de una particula deja un hueco
        for _ in deaths[:1]:
            set_dur(3)
            out.extend(b"P")

        if len(out) > SECTOR_BUDGET - 8:
            break

    out.extend(b"H")
    return bytes(out[:SECTOR_BUDGET])


def main():
    import argparse

    ap = argparse.ArgumentParser(description="ExecutionTrace de FlowGen -> programa BEAT")
    ap.add_argument("trace", help="execution.trace.json")
    ap.add_argument("-o", "--output", default="flow.beat", help="programa BEAT resultante")
    ap.add_argument("--no-arpeggio", action="store_true", help="una voz por tick, sin TDM")
    args = ap.parse_args()

    events, meta = load_events(args.trace)
    prog = compile_trace(events, arpeggio=not args.no_arpeggio)

    with open(args.output, "wb") as fh:
        fh.write(prog)

    print(f"trace  : {len(events)} eventos, motor {meta.get('engine_version', '?')}")
    print(f"sha256 : {meta.get('program_sha256', '?')[:16]}...")
    print(f"salida : {len(prog)}/{SECTOR_BUDGET} bytes -> {args.output}")
    print(f"programa: {prog.decode('latin-1')[:200]}")


if __name__ == "__main__":
    main()
