bits 16
org 0x7C00

%define OPL_ADDR  0x388
%define OPL_DATA  0x389

jmp short start
nop
db "BEATFM  ", 0x00, 0x02, 0x01, 0x01, 0x00, 0xE0, 0x00, 0x0B, 0x00, 0x12, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x29, 0xEF, 0xBE, 0x37, 0x13, "BEATFM   ", "FAT12   "

start:
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7C00
    sti

    call opl_detect
    
    mov di, 0x0300
    xor ax, ax
    rep stosw
    mov word [di], 0x0100
    mov word [di+4], 120
    mov word [di+6], 6
    mov word [di+8], 0
    mov word [di+10], 0
    mov word [di+12], 0
    mov word [di+14], 100
    mov word [di+16], 0

    mov ax, 0x0204
    mov bx, 0x1000
    mov cx, 0x0002
    xor dx, dx
    int 0x13

    call opl_init
    call load_instruments

main_loop:
    mov ah, 1
    int 0x16
    jz no_key
    mov ah, 0
    int 0x16
    call handle_key
no_key:
    call sequencer_tick
    jmp main_loop

opl_detect:
    mov dx, OPL_ADDR
    mov al, 1
    out dx, al
    mov dx, OPL_DATA
    in al, dx
    mov dx, OPL_ADDR
    xor al, al
    out dx, al
    mov dx, OPL_ADDR
    mov al, 5
    out dx, al
    mov dx, OPL_DATA
    mov al, 1
    out dx, al
    in al, dx
    test al, 6
    jz is_opl2
    mov word [0x0316], 1
    ret
is_opl2:
    mov word [0x0316], 0
    ret

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
    call load_instruments
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

load_instruments:
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

set_instrument:
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

handle_key:
    cmp al, 0x13
    jne .q
    mov ax, 0x0204
    mov bx, 0x0100
    mov cx, 0x0002
    xor dx, dx
    int 0x13
    mov si, msg_reload
    call puts
    iret
.q:
    cmp al, 0x10
    jne .r
    call spk_toggle
.r:
    iret

; --- SUBROUTINES (defined ONCE) ---

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

puts:
    lodsb
    test al, al
    jz puts_ret
    mov ah, 0x0E
    int 10h
    jmp puts
puts_ret:
    ret

spk_off:
    in al, 61h
    and al, 0FCh
    out 61h, al
    ret

spk_on:
    in al, 61h
    or al, 3
    out 61h, al
    ret

spk_toggle:
    in al, 61h
    xor al, 3
    out 61h, al
    ret

son:
    in al, 61h
    or al, 3
    out 61h, al
    ret

sof:
    in al, 61h
    and al, 0FCh
    out 61h, al
    ret

fnum_table:
    times 96 dw 0

note_table:
    dw 262, 277, 294, 311, 330, 349, 370, 392, 415, 440, 466, 494

msg_reload db "RELOAD!", 0
msg_err db "LOAD ERR", 0

times 510-($-$$) db 0
dw 0xAA55

times 1474560-($-$$) db 0