#!/usr/bin/env python3
"""Genera el parche de controles de Initial D Arcade Stage (Export) Rev A (NAOMI 2, GDS-0025A)
para el mueble Crazy Taxi.

Comportamiento:
  - palanca adelante (J1 ARRIBA) -> SUBIR marcha  (J2 ARRIBA)
  - palanca atrás    (J1 ABAJO)  -> BAJAR marcha  (J2 ABAJO)
  - la palanca ya no llega al J1 (antes la palanca atrás era el botón VISTA)
  - START pulsado y soltado antes de VIEW_MAX frames -> VISTA (J1 ABAJO) durante 1 frame
Volante, acelerador, freno y START siguen igual.

La función 0x0C1579C0 lee la respuesta JVS (llamando a 0x0C157840) y rellena, byte a byte, las
estructuras de sistema (0x0C7DDFF0) y de jugadores (0x0C7DE030 + 64·p): actual +0, anterior +16,
pulsado +32, soltado +48. Se reescriben sus dos bucles (0x0C1579D6-0x0C157A7B) con una subrutina común
y en el espacio ganado va la lógica. Prólogo, epílogo y el resto de la función no cambian.
Estado: 1 byte libre del hueco JVS del J1 (0x0C8D8615 = crudo J1 + 8).

Uso: python3 build_patch.py  -> initiald_ct.ips
"""
import os, struct, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from sh4asm import Asm

BASE   = 0x0C020000   # dirección de carga
ROMOFF = 0x500        # offset de la ROM que se carga en BASE (cabecera: 0x500 -> 0x0C020000)
START, END = 0x0C1579D6, 0x0C157A7C
# literales del pool original de la función (no se tocan)
L_CNT  = 0x0C157AD8   # 0x0C8D85FC: [0] jugadores, [4] bytes por jugador, [8] analógicos
L_R11  = 0x0C157ADC   # 0x0C7DE450 (lo que el código siguiente espera en r11)
L_SYS  = 0x0C157AE0   # 0x0C7DDFF0 estructura del byte de sistema
L_SYSB = 0x0C157AE4   # 0x0C8D860C byte de sistema crudo
L_P    = 0x0C157AE8   # 0x0C7DE030 estructuras de jugador (64 bytes cada una)
L_RAW  = 0x0C157AEC   # 0x0C8D860D crudo del J1 (16 bytes por jugador)

# Lector de tarjetas (CARD R/W) apagado por defecto: bit 4 de la palabra +12 de los ajustes del juego.
# Inicialización de fábrica (programa principal y programa de test): (x & ~0x0F) | 0x14 -> (x & ~0x1F) | 0x04.
# Migración de ajustes antiguos, que forzaba el lector a ON: se anula.
TEST_ROMOFF = 0x300000   # el programa de test se carga desde aquí, también en BASE
CARD_OFF = [  # (programa, dirección, bytes originales, bytes nuevos)
    ('main', 0x0C04EE52, b'\xf0\xe3', b'\xe0\xe3'),   # mov #-16,r3 -> mov #-32,r3
    ('main', 0x0C04EE82, b'\x14\xcb', b'\x04\xcb'),   # or #20,r0  -> or #4,r0
    ('main', 0x0C04EFFA, b'\x10\xcb', b'\x09\x00'),   # or #16,r0  -> nop
    ('test', 0x0C0217B2, b'\xf0\xe3', b'\xe0\xe3'),
    ('test', 0x0C0217E2, b'\x14\xcb', b'\x04\xcb'),
    ('test', 0x0C0218BC, b'\x10\xcb', b'\x09\x00'),
]

VIEW_MAX = 30         # START más corto que esto (frames) -> vista al soltar
UP, DOWN, START_B = 0x20, 0x10, 0x80

def build():
    a = Asm(START)
    # --- byte de sistema (igual que el original) ---
    a.movl_pc(L_CNT, 10)
    a.movl_pc(L_SYS, 4); a.movl_pc(L_SYSB, 1); a.movb_ld(1, 2); a.movl_ld_d(4, 10, 9)
    a.cmppl(9); a.bf('sys_done')
    a.label('sys_loop'); a.bsr_l('upd'); a.nop(); a.dt(9); a.bfs('sys_loop'); a.addi(1, 4)
    a.label('sys_done')
    # --- START corto -> vista ---
    a.movl_pc(L_RAW, 7); a.movb_ld(7, 1)                 # r1 = byte0 crudo del J1
    a.movb_d_r0(8, 7); a.extub(0, 6)                     # r6 = frames con START (estado)
    a.movi(0, 13); a.movi(VIEW_MAX, 3)
    a.mov(1, 0); a.tst_i(START_B); a.bt('s_rel')
    a.cmpge(3, 6); a.bt('s_done'); a.bra('s_done'); a.addi(1, 6)
    a.label('s_rel')
    a.tst(6, 6); a.bt('s_zero'); a.cmpge(3, 6); a.bt('s_zero'); a.movi(DOWN, 13)
    a.label('s_zero'); a.movi(0, 6)
    a.label('s_done'); a.mov(6, 0); a.movb_r0_d(8, 7)
    # --- jugadores: el byte0 del J1 pierde la palanca y gana la vista; el J2 gana la palanca ---
    a.mov(1, 0); a.and_i(UP | DOWN); a.mov(0, 8)         # r8 = palanca del J1 (para el J2)
    a.movi(-((UP | DOWN) + 1), 12)                       # r12 = máscara del J1 = ~0x30
    a.movl_pc(L_P, 11); a.movl_ld(10, 6); a.cmppl(6); a.bf('p_done')
    a.label('p_loop')
    a.movl_ld_d(4, 10, 9); a.cmppl(9); a.bf('p_next')
    a.mov(11, 4); a.mov(7, 5)
    a.movb_inc(5, 2); a.and_(12, 2); a.or_(13, 2); a.bsr_l('upd'); a.nop()   # byte 0
    a.movi(-1, 12); a.mov(8, 13); a.movi(0, 8)          # siguiente jugador: J2 recibe la palanca
    a.dt(9); a.bt('p_next')
    a.label('b_loop'); a.addi(1, 4); a.movb_inc(5, 2); a.bsr_l('upd'); a.nop(); a.dt(9); a.bf('b_loop')
    a.label('p_next'); a.addi(16, 7); a.addi(64, 11); a.dt(6); a.bf('p_loop')
    a.label('p_done')
    a.movl_pc(L_R11, 11)
    a.bra('end'); a.nop()
    # --- subrutina: r4 = &actual, r2 = nuevo byte (usa r0, r1, r3) ---
    a.label('upd')
    a.movb_ld(4, 1); a.movi(16, 0); a.movb_st_r0idx(1, 4)          # anterior = actual
    a.movb_st(2, 4)                                                 # actual = nuevo
    a.not_(1, 3); a.and_(2, 3); a.movi(32, 0); a.movb_st_r0idx(3, 4)   # pulsado = nuevo & ~anterior
    a.not_(2, 3); a.and_(1, 3); a.movi(48, 0); a.rts(); a.movb_st_r0idx(3, 4)  # soltado
    assert a.pc <= END, f'no cabe: {hex(a.pc)} > {hex(END)}'
    while a.pc < END: a.nop()
    a.label('end')
    return a.finish()

def rom_records():
    """[(offset en ROM, bytes nuevos, bytes originales esperados o None)]"""
    recs = [(addr - BASE + ROMOFF, data, None) for addr, data in build()]
    for prog, addr, old, new in CARD_OFF:
        recs.append((addr - BASE + (ROMOFF if prog == 'main' else TEST_ROMOFF), new, old))
    return recs

def ips(records):
    out = bytearray(b'PATCH')
    for off, data, _ in records:
        out += struct.pack('>I', off)[1:] + struct.pack('>H', len(data)) + data
    return bytes(out + b'EOF')

if __name__ == '__main__':
    recs = rom_records()
    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, 'initiald_ct.ips'), 'wb').write(ips(recs))
    for off, data, _ in recs:
        print(f'ROM 0x{off:06X}: {len(data)} bytes')
