#!/bin/sh
# Construye la imagen de diskette de 1.44 MB desde el fuente.
# Requiere nasm. La imagen resultante arranca en cualquier PC o emulador
# x86 que soporte disquetes: qemu-system-i386 -fda BEAT.img
set -e
nasm -f bin BEAT.asm -o BEAT.img
echo "BEAT.img: $(wc -c < BEAT.img) bytes"
