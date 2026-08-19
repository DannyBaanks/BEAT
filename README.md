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
| `S` | alterna el altavoz — sostiene la última nota indefinidamente |
| `H` | detiene la máquina |

El registro y la cinta son dos almacenes distintos: `R` y `W` los conectan. Eso
permite escribir un valor calculado con aritmética de Brainfuck y luego usarlo
como altura de nota.

`N` lee dígitos decimales hasta el primer byte que no lo sea, así que la
frecuencia se escribe tal cual: `N440.` toca un La4. La duración real de una
nota sale de las dos instrucciones a la vez —
`ticks = (1092 / BPM) × D / 4`, sobre el tick de 18.2065 Hz del BIOS.

`S` no es un mute: hace `xor` sobre los dos bits del puerto `61h`, o sea que
**alterna**. Como el divisor del 8253 sigue cargado con la última nota,
encenderlo deja ese tono sonando mientras el programa continúa ejecutando —
es la única forma de sostener una nota más allá del máximo que permite `D`.
`H` sí apaga el altavoz antes de parar la máquina.

`J` y `Z` saltan a direcciones **absolutas**. El motor empieza a ejecutar en
`0x0600`, así que un programa con saltos solo funciona si es el primero del
sector: no es reubicable.

Dos advertencias sobre la mitad Brainfuck. `+` `-` y `[` `]` operan sobre el
**registro**, no sobre la celda: los idiomas habituales de Brainfuck que usan
varias celdas como acumuladores (`>+++++[<+++++>-]<`) aquí no cierran nunca,
porque el saldo por vuelta es positivo y el registro no llega a cero. Y `W`
escribe solo el byte bajo, así que la cinta guarda valores de 0 a 255: como
altura, eso son frecuencias graves.

## Programas de ejemplo

El fuente trae nueve programas en el sector 4; el motor ejecuta el primero y
los demás son catálogo. El primero es una escala:

```
T4D9N440.N494.N523.N587.N659.N698.N784.H
```

Tempo 4 (140 BPM), duración 9, siete notas ascendentes desde La4, halt. Lo que
suena de verdad es 440.1, 494.1, 523.1, 587.2, 659.2, 698.2 y 784.5 Hz: el 8253
solo acepta divisores enteros de 1193182, así que la afinación es la que el
hardware puede dar, no la que se le pide.

| | qué demuestra |
|---|---|
| 1 | escala mayor de La4 a Sol5 |
| 2 | arpegio de Do con `P` separando las notas |
| 3 | `T9D0N440[.----]H` — glissando de 110 notas; el registro *es* el contador del bucle |
| 4 | tres alturas guardadas con `W` y releídas con `R` |
| 5 | motivo repetido cuatro veces, con el contador viviendo en la cinta (`Z` + `J`) |
| 6 | ocho pulsos de 80 a 220 Hz, altura acumulada en una celda entre vueltas |
| 7 | dos voces en una quinta multiplexadas a 55 ms: el altavoz es monofónico, el oído no |
| 8 | drone sostenido con `S` por encima del límite de `D` |
| 9 | la misma celda leída como altura y como cuenta atrás |

Los nueve terminan y los nueve suenan; están verificados ejecutándolos desde la
imagen construida, no desde el fuente.

## Reproducibilidad

`BEAT.img` se construye desde `BEAT.asm` y nada más. El hash de la imagen que
produce este fuente está en `BEAT.img.sha256`; `./build.sh` debe reproducirlo
exactamente.

## Verificación

Que el motor ensamble no dice nada sobre si suena. `tools/` trae lo necesario
para comprobarlo de verdad:

```sh
python tools/test_qemu.py     # arranca la imagen y mide el altavoz
```

Arranca `BEAT.img` en QEMU, graba lo que sale por el altavoz interno y verifica
que las siete notas de la escala están, en orden, con su altura y su duración.

Vale la pena insistir en por qué existe: de los cinco bugs que tuvo este motor,
cuatro eran invisibles leyendo el fuente y sólo aparecieron al arrancar el
disco. Nada de `tools/` participa en la construcción de la imagen — ver
[tools/README.md](tools/README.md).

## Versiones anteriores

`legacy/` conserva cuatro imágenes arrancables del 14 de agosto de 2026 y tres
variantes del fuente que no compilan. Tres de esas imágenes ocupan **un solo
sector de 512 bytes**, frente a los tres sectores de la versión actual — pero
ninguna interpreta nada: se desensamblaron las tres y no contienen intérprete,
sino un reproductor OPL2 al que además nadie llega a llamar. Ver
[legacy/README.md](legacy/README.md).

## Licencia

MIT — ver [LICENSE](LICENSE).
