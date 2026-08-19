bits 16
org 0x7C00

%define OPL_ADDR   0x388
%define OPL_DATA   0x389

jmp short start
nop
db "BEATPRO ", 0x00, 0x02, 0x01, 0x01, 0x00, 0xE0, 0x00, 0x0B, 0x00, 0x12, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x29, 0xEF, 0xBE, 0x37, 0x13, "BEATPRO  ", "FAT12   "

start:
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7C00
    sti

    call opl_init
    call load_instruments

main_loop:
    call sequencer_tick
    jmp main_loop

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
    mov dx, OPL_ADDR
    out dx, al
    in al, dx
    in al, dx
    in al, dx
    pop ax
    mov dx, OPL_DATA
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
    mov si, fnum_table
    add si, ax
    mov ax, [si]
    pop ax
    mov dl, OPL_ADDR
    mov al, 0xA0
    add al, [0x0300]
    out dx, al
    mov dx, OPL_DATA
    mov al, ah
    out dx, al
    mov dl, OPL_ADDR
    mov al, 0xB0
    add al, [0x0300]
    out dx, al
    mov dx, OPL_DATA
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
    mov dx, OPL_ADDR
    mov al, 0xB0
    add al, [0x0300]
    out dx, al
    mov dx, OPL_DATA
    mov al, 0
    out dx, al
    ret

sequencer_tick:
    dec word [0x0306]
    jnz .done
    mov ax, [0x0304]
    mov [0x0306], ax
    inc word [0x030A]
    cmp word [0x030A], 64
    jl .same
    mov word [0x030A], 0
    inc word [0x0308]
.same:
    call play_pattern_row
.done:
    ret

play_pattern_row:
    mov si, 0x1000
    mov ax, [0x0308]
    shl ax, 8
    add si, ax
    mov ax, [0x030A]
    shl ax, 4
    add si, ax
    mov cx, 9
.ch_loop:
    lodsb
    test al, al
    jz .next
    mov ah, al
    mov al, cl
    mov bl, 4
    call play_note
.next:
    dec cx
    jnz .ch_loop
    ret

wait_t:
    push ax
    push dx
    mov ah, 0
    int 1Ah
    add cx, dx
.w: int 1Ah; cmp dx, cx; jl .w
    pop dx
    pop ax
    ret

fnum_table:
    times 96 dw 0

note_table:
    dw 262, 277, 294, 311, 330, 349, 370, 392, 415, 440, 466, 494

times 510-($-$$) db 0
dw 0xAA55