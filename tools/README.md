# tools — verificación, no construcción

`BEAT.img` se sigue construyendo desde `BEAT.asm` y nada más: `../build.sh` sólo
llama a `nasm`. Nada de este directorio participa en esa cadena.

Lo que hay aquí sirve para **comprobar que el disco hace lo que dice**, y existe
porque leer el ensamblador no basta. Cuatro de los cinco bugs que tuvo el motor
eran invisibles en el fuente y sólo aparecieron al arrancar la imagen de verdad:
frecuencias que el 8253 no puede expresar, una duración que `INT 1Ah` destruía
en `AL`, y tres referencias a datos que leían 512 bytes desviadas porque el
motor comparte el `org` con el bootsector pero se carga sin él.

## `test_qemu.py` — la prueba que importa

```sh
python tools/test_qemu.py            # sobre ../BEAT.img
python tools/test_qemu.py otra.img
```

Arranca la imagen en QEMU, graba lo que sale por el altavoz interno y comprueba
que las siete notas de la escala están, en orden, con su altura y su duración.
Es la única prueba que no comparte suposiciones con el simulador: mide el
hardware emulado.

Busca `qemu-system-i386` en el `PATH`; si no está, exporta `QEMU=/ruta/al/binario`.

Detalle que cuesta descubrir: QEMU escribe los tamaños de la cabecera RIFF al
cerrar el archivo, y aquí lo matamos por tiempo porque el guest termina en `hlt`
y no sale solo. El WAV queda con los tamaños en cero y hay que repararlos antes
de leerlo. `repara()` lo hace.

## `beat_sim.py` — modelo de referencia

Reimplementa la semántica del motor instrucción por instrucción y produce un
WAV, para oír un programa sin arrancar el diskette. No emula x86: reproduce las
decisiones del motor, incluida la aritmética del divisor entero del 8253, que es
la razón de que `N440` suene a 440.1 Hz y no a 440.

```sh
python tools/beat_sim.py 'T4D9N440.N494.N523.H' escala.wav
```

Está contrastado contra QEMU: predice 440.1 / 494.1 / 523.1 / 587.2 / 659.2 /
698.2 / 784.5 Hz, y el disco real entrega 440 / 495 / 525 / 590 / 660 / 700 /
785 — dentro de los 5 Hz que resuelve la medición.

**No lo uses como única verificación.** Es el mismo razonamiento que escribió el
motor: si el razonamiento está mal, ambos coinciden en el error. Para eso está
`test_qemu.py`.

## `analiza_wav.py` — leer notas de una grabación

Extrae altura y duración contando cruces por cero, que en una onda cuadrada da
el periodo exacto sin necesidad de FFT. Dos modos:

- `notas()` promedia en ventanas fijas. Simple, pero impone un compromiso:
  con 100 ms distingue 5 Hz y no ve notas de 55 ms.
- `notas_precisas()` cronometra cada semiciclo. Resuelve las dos cosas y es lo
  que hay que usar con programas rápidos.

## `patch_sector4.py` — cambiar la música sin reensamblar

```sh
python tools/patch_sector4.py BEAT.img programa.beat salida.img
```

El programa vive en su propio sector, así que cambiarlo son 511 bytes en el
offset `0x600`. Comprueba que la firma de arranque sobrevive.

## `flow2beat.py` — el disco toca un repositorio

Compila un `execution.trace.json` de [FlowGen](https://github.com/DannyBaanks/FlowGen)
a un programa BEAT. FlowGen escanea un repositorio, lo convierte en un programa
FLOW (una imagen que es un campo vectorial) y lo ejecuta; este compilador
traduce las partículas resultantes a notas.

```sh
python tools/flow2beat.py execution.trace.json -o flow.beat
python tools/patch_sector4.py BEAT.img flow.beat BEAT_FLOW.img
qemu-system-i386 -fda BEAT_FLOW.img
```

La altura sale de la posición Y de cada partícula; las partículas vivas en el
mismo tick se emiten como arpegio rápido, porque el altavoz es monofónico y el
oído no; y los `STATE_CHANGE` pasan por la cinta con `W` y `R` antes de sonar.

El presupuesto es duro: 511 bytes. Lo que no cabe, no suena.
