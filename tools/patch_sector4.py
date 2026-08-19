"""
patch_sector4.py -- escribe un programa BEAT en el sector 4 de una imagen.

El motor vive en los sectores 2-3 y el programa en el 4, asi que cambiar la
musica no requiere reensamblar nada: son 511 bytes y un NUL en el offset 0x600.
"""

import hashlib
import shutil
import sys

SECTOR4 = 0x600
BUDGET = 511


def patch(src_img: str, program: bytes, dst_img: str):
    if len(program) > BUDGET:
        raise ValueError(f"{len(program)} bytes: no cabe en el sector ({BUDGET})")

    shutil.copyfile(src_img, dst_img)
    with open(dst_img, "r+b") as fh:
        fh.seek(SECTOR4)
        fh.write(program + b"\x00" * (512 - len(program)))

    with open(dst_img, "rb") as fh:
        data = fh.read()

    assert data[510:512] == b"\x55\xAA", "la firma de arranque se ha perdido"
    assert data[SECTOR4:SECTOR4 + len(program)] == program, "el sector 4 no cuadra"

    return hashlib.sha256(data).hexdigest(), len(data)


if __name__ == "__main__":
    src, prog_path, dst = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(prog_path, "rb") as fh:
        program = fh.read()
    digest, size = patch(src, program, dst)
    print(f"programa : {len(program)}/{BUDGET} bytes")
    print(f"imagen   : {size} bytes -> {dst}")
    print(f"sha256   : {digest}")
    print("firma 0x55AA en 510: ok")
