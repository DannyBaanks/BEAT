"""
analiza_wav.py -- extrae las notas de una grabacion del PC speaker.

La onda del altavoz es cuadrada, asi que la frecuencia sale de contar cruces
por cero: no hace falta FFT y el resultado es exacto hasta el ancho de la
ventana. Sirve para contrastar lo que QEMU emitio de verdad contra lo que el
simulador dijo que iba a sonar.
"""

import struct
import sys
import wave


def leer(path):
    with wave.open(path, "rb") as w:
        n, ch, sw, rate = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(n)
    if sw != 2:
        raise SystemExit(f"esperaba 16 bits, no {sw*8}")
    total = len(raw) // 2
    muestras = struct.unpack(f"<{total}h", raw)
    if ch > 1:                      # quedarse con un canal
        muestras = muestras[::ch]
    return list(muestras), rate


def segmentar(muestras, rate, umbral=600, hueco_min=0.03):
    """Parte la señal en tramos con sonido, tolerando huecos cortos."""
    activo = [abs(v) > umbral for v in muestras]
    seg, ini = [], None
    silencio = 0
    hueco = int(rate * hueco_min)
    for i, a in enumerate(activo):
        if a:
            if ini is None:
                ini = i
            silencio = 0
        elif ini is not None:
            silencio += 1
            if silencio > hueco:
                seg.append((ini, i - silencio))
                ini = None
    if ini is not None:
        seg.append((ini, len(muestras) - 1))
    return [(a, b) for a, b in seg if (b - a) / rate > 0.05]


def notas(muestras, rate, ventana=0.1, tol=0.05):
    """Parte la señal por CAMBIO DE ALTURA, no por silencio.

    Entre nota y nota el motor apaga y reenciende el altavoz en microsegundos,
    asi que no hay hueco que detectar: lo que cambia es la frecuencia.

    La ventana no puede ser corta: contar cruces por cero da una resolucion de
    1/(2*ventana) Hz, o sea 25 Hz con ventanas de 20 ms -- bastante para
    trocear una sola nota en pedazos que no coinciden entre si. Con 100 ms la
    resolucion baja a 5 Hz, por debajo de la tolerancia de agrupacion.
    """
    n = int(rate * ventana)
    trozos = []
    for i in range(0, len(muestras) - n, n):
        amp = max(abs(v) for v in muestras[i:i + n])
        f, _ = frecuencia(muestras, i, i + n, rate)
        trozos.append((f if amp > 600 else 0.0, i))

    grupos, cur = [], []
    for f, i in trozos:
        if cur and abs(f - cur[0][0]) > tol * max(cur[0][0], 1):
            grupos.append(cur)
            cur = []
        cur.append((f, i))
    if cur:
        grupos.append(cur)

    salida = []
    for g in grupos:
        fs = sorted(f for f, _ in g)
        mediana = fs[len(fs) // 2]
        if mediana <= 0 or len(g) < 2:      # silencio o transicion suelta
            continue
        salida.append((mediana, len(g) * ventana))
    return salida


def notas_precisas(muestras, rate, tol=0.04, min_periodos=3):
    """Mide el periodo entre cruces individuales, sin promediar por ventana.

    Promediar en ventanas fijas impone un compromiso entre resolucion de
    frecuencia y de tiempo: con 100 ms se distinguen 5 Hz pero no se ven notas
    de 55 ms. Cronometrar cada semiciclo de la onda cuadrada da las dos cosas,
    porque el altavoz produce una señal limpia sin armonicos que confundan.
    """
    cruces = []
    prev = muestras[0] >= 0
    for i, v in enumerate(muestras[1:], 1):
        cur = v >= 0
        if cur and not prev:            # solo flancos de subida
            cruces.append(i)
        prev = cur

    if len(cruces) < 2:
        return []

    grupos, cur_f, ini, n = [], None, cruces[0], 0
    for a, b in zip(cruces, cruces[1:]):
        periodo = (b - a) / rate
        if periodo <= 0:
            continue
        f = 1.0 / periodo
        if cur_f is None or abs(f - cur_f) <= tol * cur_f:
            cur_f = f if cur_f is None else (cur_f * n + f) / (n + 1)
            n += 1
        else:
            if n >= min_periodos:
                grupos.append((cur_f, (a - ini) / rate))
            cur_f, ini, n = f, a, 1
    if n >= min_periodos:
        grupos.append((cur_f, (cruces[-1] - ini) / rate))
    return grupos


def frecuencia(muestras, a, b, rate):
    """Cruces por cero -> frecuencia. Exacto para onda cuadrada."""
    tramo = muestras[a:b]
    cruces = 0
    prev = tramo[0] >= 0
    for v in tramo[1:]:
        cur = v >= 0
        if cur != prev:
            cruces += 1
        prev = cur
    dur = (b - a) / rate
    return (cruces / 2) / dur if dur > 0 else 0.0, dur


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "qemu_beat.wav"
    muestras, rate = leer(path)
    print(f"{path}: {len(muestras)} muestras a {rate} Hz = {len(muestras)/rate:.2f} s\n")

    seg = segmentar(muestras, rate)
    print(f"{len(seg)} tramos con sonido:\n")
    print(f"  {'#':>2}  {'inicio':>8}  {'dur':>8}  {'frecuencia':>12}")
    notas = []
    for i, (a, b) in enumerate(seg, 1):
        f, d = frecuencia(muestras, a, b, rate)
        notas.append((f, d))
        print(f"  {i:2d}  {a/rate:7.2f}s  {d*1000:7.1f}ms  {f:9.1f} Hz")
    return notas


if __name__ == "__main__":
    main()
