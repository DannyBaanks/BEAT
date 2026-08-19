; ============================================================================
; BEAT — music esolang + 16-bit x86 bootsector (KALEIDOSCOPE engine)
;
; Disco 1.44MB. Layout:
;   sector 1 (0x000): bootsector: BPB + mini-loader
;                     -> lee sectores 2-3 (engine, 1024B) a 0x0100, salta ahi
;   sectors 2-3 (0x200): motor BEAT completo (org 0x0100)
;                     -> lee sector 4 (programa, 512B) a 0x0600 y lo ejecuta
;   sector 4 (0x400): programa BEAT (max 511 bytes + NUL)
;
; Encabezado: BPB FAT12 estandar para imagen de 1.44MB.
; ============================================================================

bits 16
org 0x0100

; ---- Mapa de memoria -------------------------------------------------------
; El estado y la cinta viven por encima de 0x0500: la IVT (0x0000-0x03FF) y el
; BIOS Data Area (0x0400-0x04FF) quedan intactos. En particular 0x046C, el
; contador de ticks que INT 1Ah lee para medir las duraciones, ya no es
; alcanzable por el puntero de cinta.
%define PROG    0x0600          ; programa (sector 4), 511B + NUL
%define STATE   0x0500          ; bloque de estado del motor
%define IP_     STATE+0         ; puntero de instruccion dentro del programa
%define REG     STATE+2         ; registro: frecuencia en Hz / acumulador
%define TEMPO   STATE+4         ; tempo actual en BPM
%define DUR     STATE+6         ; duracion actual (indice 0-9, semicorcheas)
%define TAPEP   STATE+8         ; puntero de celda de la cinta
%define TAPE    0x0800          ; cinta (2KB, hasta 0x0FFF)

jmp short start
nop
db "BEAT    ", 0x00, 0x02, 0x01, 0x01, 0x00, 0xE0, 0x00, 0x0B, 0x00, 0x12, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x29, 0xEF, 0xBE, 0x37, 0x13, "BEATLANG   ", "FAT12   "

start:
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7C00
    sti

    mov ax, 0x0202
    mov bx, 0x0100
    mov cx, 0x0002
    xor dx, dx
    int 0x13
    jc err

    db 0xEA
    dw 0x0100, 0x0000
err:
    cli
    hlt
    jmp err

times 510-($-$$) db 0
dw 0xAA55

; ----------------------------------------------------------------------------
; Motor (cargado en 0x0100, CS:IP = 0x0000:0x0100, DS=ES=SS=0)
; Todos los saltos del motor son IP-relativos y el bootsector no referencia
; absolutas, asi que un unico org 0x0100 cubre ambos espacios de direcciones.
; ----------------------------------------------------------------------------

engine:
    mov di, STATE
    xor ax, ax
    mov cx, 8
    rep stosw

    mov di, TAPE
    xor ax, ax
    mov cx, 1024
    rep stosw

    mov word [IP_], PROG
    mov word [TEMPO], 120
    mov word [DUR], 4
    mov word [TAPEP], TAPE

    mov ax, 0x0201
    mov bx, PROG
    mov cx, 0x0004
    xor dx, dx
    int 0x13
    jc load_fail

main_loop:
    mov si, [IP_]
    lodsb
    test al, al
    jz halt

    cmp al, '>'
    je op_1
    cmp al, '<'
    je op_2
    cmp al, '+'
    je op_3
    cmp al, '-'
    je op_4
    cmp al, '.'
    je op_5
    cmp al, ','
    je op_6
    cmp al, '['
    je op_7
    cmp al, ']'
    je op_8
    cmp al, 'T'
    je op_9
    cmp al, 'D'
    je op_A
    cmp al, 'P'
    je op_B
    cmp al, 'R'
    je op_C
    cmp al, 'W'
    je op_D
    cmp al, 'J'
    je op_E
    cmp al, 'Z'
    je op_F
    cmp al, 'S'
    je op_G
    cmp al, 'N'
    je op_H
    cmp al, 'H'
    je halt
    jmp next_ip

op_1:
    inc word [TAPEP]
    jmp next_ip

op_2:
    dec word [TAPEP]
    jmp next_ip

op_3:
    inc word [REG]
    jmp next_ip

op_4:
    dec word [REG]
    jmp next_ip

op_5:
    mov bx, [REG]
    call play
    jmp next_ip

op_6:
    mov ah, 0
    int 16h
    test al, al
    jz op_6
    sub al, '0'
    jl op_6
    cmp al, 12
    jg op_6
    movzx bx, al
    shl bx, 1
    mov bx, [note_table+bx]
    mov [REG], bx
    jmp next_ip

op_7:
    cmp word [REG], 0
    jne next_ip
    mov di, si
    mov cx, 1
op7_scan:
    lodsb
    cmp al, '['
    je nf1
    cmp al, ']'
    je cf1
    test al, al
    jz halt
    jmp op7_scan
nf1:
    inc cx
    jmp op7_scan
cf1:
    dec cx
    jnz op7_scan
    mov [IP_], si
    jmp main_loop

op_8:
    cmp word [REG], 0
    je next_ip
    mov di, si
    dec di
    dec di
    mov cx, 1
op8_scan:
    cmp di, PROG
    jl halt
    mov al, [di]
    cmp al, ']'
    je nb2
    cmp al, '['
    je cb2
    dec di
    jmp op8_scan
nb2:
    inc cx
    dec di
    jmp op8_scan
cb2:
    dec cx
    jnz op8_scan
    mov [IP_], di
    inc word [IP_]
    jmp main_loop

; T<n> -- tempo: indice 0-9 en la tabla de BPM
op_9:
    lodsb
    sub al, '0'
    jl t9_skip
    cmp al, 9
    jg t9_skip
    movzx bx, al
    shl bx, 1
    mov ax, [tempo_table+bx]
    mov [TEMPO], ax
    jmp next_ip
t9_skip:
    jmp next_ip

; D<n> -- duracion: indice 0-9, en semicorcheas
op_A:
    lodsb
    sub al, '0'
    jl d9_skip
    cmp al, 9
    jg d9_skip
    movzx ax, al
    mov [DUR], ax
    jmp next_ip
d9_skip:
    jmp next_ip

op_B:
    call dur_ticks
    call wait_t
    jmp next_ip

op_C:
    mov bx, [TAPEP]
    mov al, [bx]
    movzx ax, al
    mov [REG], ax
    jmp next_ip

op_D:
    mov bx, [TAPEP]
    mov al, [REG]
    mov [bx], al
    jmp next_ip

op_E:
    lodsw
    mov [IP_], ax
    jmp main_loop

op_F:
    cmp word [REG], 0
    je dj
    add si, 2
    jmp next_ip
dj:
    lodsw
    mov [IP_], ax
    jmp main_loop

op_G:
    in al, 61h
    xor al, 3
    out 61h, al
    jmp next_ip

; N<decimal> -- carga una frecuencia en Hz escrita en ASCII decimal: N440 -> 440
op_H:
    xor bx, bx
nh_digit:
    lodsb
    sub al, '0'
    jb nh_done
    cmp al, 9
    ja nh_done
    mov ah, 0
    push ax
    mov ax, bx
    shl bx, 1
    shl ax, 3
    add bx, ax                  ; bx *= 10
    pop ax
    add bx, ax                  ; += digito
    jmp nh_digit
nh_done:
    dec si                      ; devuelve el byte no-digito al flujo
    mov [REG], bx
    jmp next_ip

next_ip:
    mov [IP_], si
    jmp main_loop

halt:
    call spk_off
    cli
    hlt

load_fail:
    mov si, msg_err
    call puts
    jmp halt

; ----------------------------------------------------------------------------
; Duracion en ticks del PIT (18.2065 Hz) a partir de tempo y duracion:
;   ticks_por_negra = 1092 / BPM        (1092 = 18.2065 ticks/s * 60 s/min)
;   ticks           = ticks_por_negra * D / 4    (D en semicorcheas)
; Devuelve CX, con un minimo de 1 tick.
; ----------------------------------------------------------------------------
dur_ticks:
    push ax
    push dx
    mov ax, 1092
    xor dx, dx
    div word [TEMPO]
    mul word [DUR]
    shr ax, 2
    or ax, ax
    jnz dt_ok
    inc ax
dt_ok:
    mov cx, ax
    pop dx
    pop ax
    ret

play:
    test bx, bx
    jz rest
    push ax
    mov al, 0B6h
    out 43h, al
    mov dx, 0x0012
    mov ax, 0x34DE
    div bx
    out 42h, al
    mov al, ah
    out 42h, al
    call son
    call dur_ticks
    call wait_t
    call sof
    pop ax
    ret

rest:
    call dur_ticks
    call wait_t
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

; ----------------------------------------------------------------------------
; Espera CX ticks del BIOS. La cuenta va en BX porque INT 1Ah/AH=00h devuelve
; en AL el flag de medianoche, y ahi es donde el codigo anterior guardaba la
; duracion: se perdia en cada llamada y toda nota duraba cero.
; ----------------------------------------------------------------------------
wait_t:
    push ax
    push bx
    push dx
    mov bx, cx
    xor ah, ah
    int 1Ah
    add bx, dx                  ; bx = tick objetivo
wt_w:
    xor ah, ah
    int 1Ah
    cmp dx, bx
    jb wt_w
    pop dx
    pop bx
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

; Data
note_table:
    dw 262, 277, 294, 311, 330, 349, 370, 392, 415, 440, 466, 494
tempo_table:
    dw 60, 80, 100, 120, 140, 160, 180, 200, 220, 240
msg_err db "LOAD ERR", 0

ENGINE_END:
times 1536-($-$$) db 0

; ----------------------------------------------------------------------------
; Programas (sector 4, cargado a 0x0600)
; ----------------------------------------------------------------------------
prog1: db 'T4D9N440.N494.N523.N587.N659.N698.N784.H', 0
prog2: db 'T3D6>+++++[<+++++>-]<++.>.+.+.+.+.+.', 0
prog3: db 'T2D4>+++++[<+++++>-]<[Z>+.<-]H', 0
prog4: db 'T3D4>+++++[<+++++>-]<W<W<W<W<R.R.R.R.H', 0
prog5: db 'T3D4>+W>+W<Z>[<R.+>W>R.<-]H', 0
prog6: db 'T3D4I.R.I.R.I.R.H', 0
prog7: db 'T3D4N440.P.N523.P.N587.P.N659.H', 0
prog8: db 'T2D3>++W>++++W<<[Z>R.<-]>[Z>R.<-]H', 0
prog9: db 'T3D4>+++++[<+++++>-]<N440.W+W+W.W.W.H', 0

times 1474560-($-$$) db 0
