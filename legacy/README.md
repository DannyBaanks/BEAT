# legacy — versiones anteriores, preservadas tal cual

**Nada de esta carpeta se construye desde el fuente del repositorio.** Son
artefactos de las primeras versiones de BEAT, del 14 de agosto de 2026,
conservados porque son ejecutables y porque documentan un diseño distinto —
no porque sean reproducibles.

Si buscas la versión que funciona y se puede reconstruir, está en la raíz:
`BEAT.asm` + `build.sh`.

## Las imágenes

Las cuatro arrancan: llevan la firma `0x55AA` en el offset 510.

| archivo | tamaño | sectores | OEM | bytes no nulos | hora |
|---|---|---|---|---|---|
| `BEAT_1440K.img` | 1,474,560 B | diskette completo | `BEAT` | 725 | 03:33 |
| `BEAT_MIN.img` | 512 B | **uno solo** | `BEAT` | 252 | 04:54 |
| `BEAT_FINAL.img` | 512 B | **uno solo** | `BEAT` | 212 | 04:59 |
| `BEAT_DUAL.img` | 512 B | **uno solo** | `BEATDUAL` | 294 | 05:33 |

Lo interesante es la segunda columna: tres de ellas caben en un único sector,
mientras que la versión actual usa tres (cargador, motor, programa).

**Pero ninguna interpreta nada.** Se desensamblaron las cuatro con `ndisasm`:

| comprobación | `BEAT_MIN` | `BEAT_FINAL` | `BEAT_DUAL` |
|---|---|---|---|
| instrucciones `cmp al, <opcode>` | 0 | 0 | 0 |
| dispatch de `>` `<` `+` `-` `.` `,` `[` `]` | no | no | no |

No hay tabla de despacho porque no hay intérprete: son reproductores de una
canción fija sobre OPL2/AdLib (puertos `0x388`/`0x389`), no motores de BEAT.

Y no llegan ni a sonar. Las tres terminan en la misma secuencia:

```
E8 00 00    call <+0>     ; llamada con desplazamiento cero: a la instrucción siguiente
E8 00 00    call <+0>
EB FE       jmp $         ; bucle infinito sobre sí mismo
```

Un `call` con desplazamiento 0 no llama a nada: cae en la instrucción que le
sigue. Las rutinas `opl_init` y `opl_write` existen en la imagen, completas y
correctas, pero **nadie las invoca nunca**. Arrancan, no emiten un solo tono y
se cuelgan. Los "212 bytes no nulos" de `BEAT_FINAL.img` son código muerto.

`BEAT_MIN.img` y `BEAT_FINAL.img` comparten la cabecera BPB byte a byte
(offsets 0–61) pero **no** el código: difieren en 183 bytes repartidos por el
rango 134–475. Son dos compilaciones distintas, no la misma con otro nombre.
`BEAT_DUAL.img` se diferencia además en que lleva rutinas de altavoz interno
(`61h`) y del puerto paralelo (`0x37A`, un DAC tipo Covox) — también muertas.

Es decir: el intérprete de BEAT en un solo sector no ha existido nunca. La
versión de tres sectores de la raíz es la primera que suena.

`BEAT_1440K.img` se llamaba `BEAT.img`. Se renombró aquí para no confundirla
con la imagen reproducible de la raíz, que tiene el mismo tamaño y **distinto
contenido**: difieren en 1,249 bytes repartidos por los primeros diez sectores.

## Los fuentes que no compilan

Se incluyen tres variantes inacabadas. **Ninguna ensambla** — estos son los
errores exactos de `nasm`:

| archivo | error |
|---|---|
| `BEAT_MIN.asm` | `symbol 'play_song' not defined` |
| `BEAT_PRO.asm` | `symbol 'load_instruments' not defined` |
| `BEAT_FM.asm` | `TIMES value -217 is negative` — el código creció más allá del presupuesto del sector |

Se conservan porque muestran hacia dónde iban las variantes: `MIN` a reducir,
`FM` a síntesis FM, `PRO` a instrumentos cargables. El error de `BEAT_FM.asm`
es especialmente elocuente: −217 bytes es exactamente cuánto se pasó.

## Advertencia sobre la correspondencia

**Ninguno de estos fuentes produce ninguna de estas imágenes.** Se comprobó
ensamblando los cuatro `.asm` disponibles y comparando hashes: el único que
compila es el `BEAT.asm` de la raíz, y su salida no coincide con ninguna de las
cuatro imágenes de aquí.

Es decir: las imágenes se construyeron desde versiones del fuente que ya no
existen. Están preservadas como binarios, no como algo reconstruible.

Los hashes de todo el contenido están en `SHA256SUMS`.
