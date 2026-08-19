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
| 2–3 | `0x200` | motor BEAT completo (1024 B, `org 0x0100`) |
| 4 | `0x400` | el programa BEAT (máx. 511 B + NUL) |

El cargador lee los sectores 2–3 a `0x0100` y salta ahí; el motor lee el sector
4 a `0x0600` y lo ejecuta. Todos los saltos del motor son relativos a IP y el
bootsector no referencia direcciones absolutas, así que un único `org 0x0100`
cubre los dos espacios de direcciones.

**El programa vive en su propio sector.** Para cambiarlo no hay que reensamblar
el motor: basta escribir 511 bytes en el sector 4 de la imagen.

## Instrucciones

Ocho vienen de Brainfuck y operan sobre la cinta:

| | |
|---|---|
| `>` `<` | mueve el puntero de celda |
| `+` `-` | incrementa / decrementa la celda |
| `.` `,` | salida / entrada |
| `[` `]` | bucle mientras la celda no sea cero |

Nueve son propias de BEAT:

| | |
|---|---|
| `T<n>` | tempo — índice `0–9` en la tabla de tempos (60 a 240 BPM) |
| `D<n>` | duración de la nota — índice `0–9` |
| `N<n>` | toca una nota; la tabla cubre una octava cromática (262 a 494 Hz) |
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

## Programas de ejemplo

El fuente trae nueve programas en el sector 4. El primero es una escala:

```
T4D9N440.N494.N523.N587.N659.N698.N784.H
```

Tempo 4, duración 9, siete notas ascendentes desde La4, halt. Otros mezclan las
dos mitades del lenguaje: `T3D4>+++++[<+++++>-]<N440.W+W+W.W.W.H` calcula 25 con
un bucle de Brainfuck y después lo usa como dato musical.

## Reproducibilidad

`BEAT.img` se construye desde `BEAT.asm` y nada más. El hash de la imagen que
produce este fuente está en `BEAT.img.sha256`; `./build.sh` debe reproducirlo
exactamente.

## Licencia

MIT — ver [LICENSE](LICENSE).
