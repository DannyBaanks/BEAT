bits 16
org 0x7C00

%define OPL_ADDR   0x388
%define OPL_DATA   0x389

jmp short start
nop
db "BEAT    ", 0x00, 0x02, 0x01, 0x01, 0x00, 0xE0, 0x00, 0x0B, 0x00, 0x12, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x29, 0xEF, 0xBE, 0x37, 0x13, "BEAT    ", "FAT12   "

start:
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7C00
    sti
    call opl_init

main:
    call play_song
    jmp $

opl_init:
    mov cx, 256
    xor al, al
.clr:
    call opl_write
    inc al
    loop .clr
    mov al, 1
    mov ah, 32
    call opl_write
    ret

opl_write:
    push dx
    push ax
    mov dx, 0x388
    out dx, al
    in al, dx
    in al, dx
    in al, dx
    pop ax
    mov dx, 0x389
    mov al, ah
    out dx, al
    mov cx, 35
.w: loop .w
    pop dx
    ret

play_note:
    test bx, bx
    jz .done
    push ax
    push bx
    push cx
    push dx
    mov cl, 4
    shl ax, cl
    mov cl, 3
    shl bx, cl
    push ax
    mov si, fnum
    add si, ax
    mov ax, [si]
    pop ax
    mov dl, 0x388
    mov al, 0xA0
    add al, 0
    out dx, al
    mov dx, 0x389
    mov al, ah
    out dx, al
    mov dl, 0x388
    mov al, 0xB0
    out dx, al
    mov dx, 0x389
    mov al, 0x20
    or al, bl
    or al, ah
    out dx, al
    pop dx
    pop cx
    pop bx
    pop ax
.done:
    ret

note_off:
    mov dx, 0x388
    mov al, 0xB0
    out dx, al
    mov dx, 0x389
    mov al, 0
    out dx, al
    ret

fnum:
    dw 0x021B, 0x023C, 0x025F, 0x0284, 0x02AB, 0x02D4, 0x0300, 0x032F, 0x0361, 0x0396, 0x03CE, 0x040A

times 510-($-$$) db 0
dw 0xAA55