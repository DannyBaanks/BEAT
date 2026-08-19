# BEAT

**Un esolang de música que no corre sobre un sistema operativo: arranca en su lugar.**

BEAT es un lenguaje esotérico cuyo intérprete completo cabe en un diskette de
1.44 MB y se ejecuta en modo real de 16 bits, sin sistema operativo debajo. Las
notas salen por el altavoz interno de la máquina (puerto `61h`, temporizador
`8253`). No hay runtime, no hay libc, no hay kernel: el bootsector *es* el
intérprete.

```sh
./build.sh                       # requiere nasm
qemu-system-i386 -fda BEAT.img   # o grábalo en un diskette de verdad
```

## Disposición del disco

| sector | dirección | contenido |
|---|---|---|
| 1 | `0x000` | bootsector: BPB FAT12 + mini-cargador |
| 2–3 | `0x200` | motor BEAT completo (687 B usados de 1024, `org 0x0100`) |
| 4 | `0x400` | el programa BEAT (máx. 511 B + NUL) |

El cargador lee los sectores 2–3 a `0x0100` y salta ahí; el motor lee el sector
4 a `0x0600` y lo ejecuta. Todos los saltos del motor son relativos a IP y el
bootsector no referencia direcciones absolutas, así que un único `org 0x0100`
cubre los dos espacios de direcciones.

**El programa vive en su propio sector.** Para cambiarlo no hay que reensamblar
el motor: basta escribir 511 bytes en el sector 4 de la imagen.

## Memoria en tiempo de ejecución

| dirección | contenido |
|---|---|
| `0x0000`–`0x04FF` | IVT y BIOS Data Area — **el motor no los toca** |
| `0x0100` | el motor, cargado por el bootsector |
| `0x0500` | bloque de estado: IP, registro, tempo, duración, puntero de cinta |
| `0x0600` | el programa (sector 4) |
| `0x0800` | la cinta, 2 KB |

El estado y la cinta viven por encima de `0x0500` a propósito: `0x046C`, el
contador de ticks que `INT 1Ah` usa para medir las duraciones, queda fuera del
alcance del puntero de cinta.

## Instrucciones

Ocho vienen de Brainfuck y operan sobre la cinta:

| | |
|---|---|
| `>` `<` | mueve el puntero de celda |
| `+` `-` | incrementa / decrementa el registro |
| `.` `,` | salida (toca el registro) / entrada de teclado |
| `[` `]` | bucle mientras el registro no sea cero |

Nueve son propias de BEAT:

| | |
|---|---|
| `T<n>` | tempo — índice `0–9` en la tabla de tempos (60 a 240 BPM) |
| `D<n>` | duración de la nota — `0–9` semicorcheas al tempo actual |
| `N<hz>` | carga una frecuencia en hercios, escrita en decimal: `N440` |
| `P` | pausa por la duración actual |
| `R` | lee la celda bajo el puntero al registro |
| `W` | escribe el registro en la celda bajo el puntero |
| `J` | salto incondicional (dirección absoluta de 16 bits) |
| `Z` | salta si el registro es cero |
| `S` | silencia el altavoz |
| `H` | detiene la máquina |

El registro y la cinta son dos almacenes distintos: `R` y `W` los conectan. Eso
permite escribir un valor calculado con aritmética de Brainfuck y luego usarlo
como altura de nota.

`N` lee dígitos decimales hasta el primer byte que no lo sea, así que la
frecuencia se escribe tal cual: `N440.` toca un La4. La duración real de una
nota sale de las dos instrucciones a la vez —
`ticks = (1092 / BPM) × D / 4`, sobre el tick de 18.2065 Hz del BIOS.

## Programas de ejemplo

El fuente trae nueve programas en el sector 4. El primero es una escala:

```
T4D9N440.N494.N523.N587.N659.N698.N784.H
```

Tempo 4 (140 BPM), duración 9, siete notas ascendentes desde La4, halt. Lo que
suena de verdad es 440.1, 494.1, 523.1, 587.2, 659.2, 698.2 y 784.5 Hz: el 8253
solo acepta divisores enteros de 1193182, así que la afinación es la que el
hardware puede dar, no la que se le pide.

Otros mezclan las dos mitades del lenguaje:
`T3D4>+++++[<+++++>-]<N440.W+W+W.W.W.H` calcula 25 con un bucle de Brainfuck y
después lo usa como dato musical.

## Reproducibilidad

`BEAT.img` se construye desde `BEAT.asm` y nada más. El hash de la imagen que
produce este fuente está en `BEAT.img.sha256`; `./build.sh` debe reproducirlo
exactamente.

## Versiones anteriores

`legacy/` conserva cuatro imágenes arrancables del 14 de agosto de 2026 y tres
variantes del fuente que no compilan. Tres de esas imágenes ocupan **un solo
sector de 512 bytes**, frente a los tres sectores de la versión actual — pero
ninguna interpreta nada: se desensamblaron las tres y no contienen intérprete,
sino un reproductor OPL2 al que además nadie llega a llamar. Ver
[legacy/README.md](legacy/README.md).

## Licencia

MIT — ver [LICENSE](LICENSE).
