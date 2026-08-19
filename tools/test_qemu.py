"""
test_qemu.py -- prueba de integracion real: arranca BEAT.img en x86 emulado y
comprueba que el altavoz emite la escala que el programa pide.

No mide intenciones ni semantica: graba lo que el PC speaker saca de verdad y
cuenta cruces por cero. Es la unica prueba que no comparte cerebro con el
simulador.
"""

import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from analiza_wav import leer, notas as detectar_notas

REPO = Path(__file__).resolve().parent.parent
IMG_POR_DEFECTO = REPO / "BEAT.img"


def busca_qemu() -> Path:
    """qemu-system-i386, del PATH o de las rutas habituales de instalacion."""
    entorno = os.environ.get("QEMU")
    if entorno:
        return Path(entorno)
    hallado = shutil.which("qemu-system-i386")
    if hallado:
        return Path(hallado)
    for c in [
        Path.home() / "scoop/apps/qemu/current/qemu-system-i386.exe",
        Path(r"C:\Program Files\qemu\qemu-system-i386.exe"),
        Path("/usr/bin/qemu-system-i386"),
    ]:
        if c.exists():
            return c
    raise SystemExit(
        "no encuentro qemu-system-i386: ponlo en el PATH o exporta QEMU=/ruta/al/binario"
    )


QEMU = busca_qemu()

# prog1: T4D9N440.N494.N523.N587.N659.N698.N784.H
# T4 = 140 BPM, D9 -> (1092//140)*9>>2 = 15 ticks = 824 ms
ESPERADO = [440.1, 494.1, 523.1, 587.2, 659.2, 698.2, 784.5]
DUR_MS = 824.0
# Contar cruces por cero en ventanas de 100 ms resuelve 1/(2*0.1) = 5 Hz, asi
# que todo lo medido cae en multiplos de 5. Exigir menos que un paso de
# cuantizacion seria medir el instrumento, no el disco.
TOL_HZ = 5.0
# La duracion solo puede salir en multiplos del tamano de ventana (100 ms),
# mas un tick del BIOS (55 ms) de holgura real. Por nota la medida es basta;
# la comprobacion fina es la duracion TOTAL, que no sufre cuantizacion.
TOL_MS = 160.0
TOL_TOTAL = 0.05    # 5 % sobre 7 x 824 ms


def arranca(img: Path, wav: Path, segundos: int = 14):
    if wav.exists():
        wav.unlink()
    subprocess.run(
        [str(QEMU), "-drive", f"file={img},format=raw,if=floppy",
         "-audiodev", f"wav,id=snd0,path={wav}",
         "-machine", "pc,pcspk-audiodev=snd0",
         "-display", "none", "-no-reboot"],
        timeout=segundos, capture_output=True, check=False,
    )


def repara(wav: Path) -> Path:
    """QEMU escribe los tamanos del RIFF al cerrar; si lo matamos, quedan en 0."""
    d = bytearray(wav.read_bytes())
    struct.pack_into("<I", d, 4, len(d) - 8)
    struct.pack_into("<I", d, 40, len(d) - 44)
    fixed = wav.with_name(wav.stem + "_fix.wav")
    fixed.write_bytes(bytes(d))
    return fixed


def main():
    img = Path(sys.argv[1]) if len(sys.argv) > 1 else IMG_POR_DEFECTO
    wav = Path("test_run.wav")

    print(f"arrancando {img.name} en QEMU...")
    try:
        arranca(img, wav)
    except subprocess.TimeoutExpired:
        pass                      # esperado: el guest hace hlt y no sale solo

    if not wav.exists():
        print("FALLO: QEMU no produjo audio")
        return 1

    muestras, rate = leer(str(repara(wav)))
    notas = detectar_notas(muestras, rate)

    print(f"\n{len(notas)} notas detectadas (esperaba {len(ESPERADO)}):\n")
    print(f"  {'#':>2}  {'medido':>10}  {'esperado':>10}  {'error':>8}  {'dur':>9}")

    fallos = []
    for i, esperado in enumerate(ESPERADO):
        if i >= len(notas):
            print(f"  {i+1:2d}  {'AUSENTE':>10}  {esperado:9.1f}Hz")
            fallos.append(f"nota {i+1} no sono")
            continue
        f, d = notas[i]
        err = f - esperado
        ok_hz = abs(err) <= TOL_HZ
        ok_ms = abs(d * 1000 - DUR_MS) <= TOL_MS
        marca = "" if (ok_hz and ok_ms) else "   <-- FALLA"
        print(f"  {i+1:2d}  {f:9.1f}Hz  {esperado:9.1f}Hz  {err:+7.1f}  {d*1000:7.1f}ms{marca}")
        if not ok_hz:
            fallos.append(f"nota {i+1}: {f:.1f} Hz, esperaba {esperado:.1f}")
        if not ok_ms:
            fallos.append(f"nota {i+1}: {d*1000:.0f} ms, esperaba {DUR_MS:.0f}")

    if len(notas) > len(ESPERADO):
        fallos.append(f"sobran {len(notas)-len(ESPERADO)} notas")

    # comprobacion agregada: inmune al redondeo de ventana
    total = sum(d for _, d in notas) * 1000
    esperado_total = DUR_MS * len(ESPERADO)
    desvio = abs(total - esperado_total) / esperado_total
    print(f"  duracion total: {total:.0f} ms  (esperada {esperado_total:.0f} ms, "
          f"desvio {desvio*100:.1f} %)")
    if desvio > TOL_TOTAL:
        fallos.append(f"duracion total {total:.0f} ms, esperaba {esperado_total:.0f}")

    print()
    if fallos:
        print("FALLA:")
        for f in fallos[:10]:
            print(f"  - {f}")
        return 1
    print("PASA: el disco toca la escala en x86 emulado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
