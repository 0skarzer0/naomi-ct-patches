#!/usr/bin/env python3
"""Genera el parche de controles de 18 Wheeler Standard (NAOMI, 840-0036) para el mueble Crazy Taxi.

Comportamiento (palanca de Crazy Taxi de 2 posiciones con retorno, J1 ARRIBA/ABAJO):
  - toque adelante  -> marcha LARGA (J2 ARRIBA), se queda puesta
  - toque atrás     -> marcha CORTA (J2 ABAJO), se queda puesta
  - atrás mantenido HOLD frames pisando el freno, o LONG frames sin más -> MARCHA ATRÁS
    (J2 ABAJO + J2 IZQUIERDA, como el arnés de referencia); al soltar vuelve a CORTA
  - START pulsado y soltado antes de HORN frames -> VISTA (J1 ABAJO) durante 1 frame
  - START mantenido más de HORN frames -> BOCINA (J1 B1) mientras se mantenga
  - J1 ARRIBA/ABAJO de la palanca ya no llegan al J1 (antes la palanca atrás cambiaba la vista)
Volante, acelerador, freno y START siguen igual.

Se reescribe el bucle que llena las estructuras de jugador (0x0C021F4E-0x0C02205E, dejando intacto
el pool de literales 0x0C021F82-0x0C021FB3) en versión compacta, y en el espacio liberado va la lógica.
Estado en 3 bytes sin usar del hueco JVS del J1 (0x0C28949B-0x0C28949D).

Uso: python3 build_patch.py  -> 18wheeler_ct.ips
"""
import os, struct, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from sh4asm import Asm

BASE = 0x0C020000
A_START, A_END = 0x0C021F4E, 0x0C021F82   # hueco A (antes del pool)
B_START, B_END = 0x0C021FB4, 0x0C02205E   # hueco B (después del pool); en B_END sigue el código original
L_127A7C = 0x0C021FAC     # literal 0x0C127A7C (el original guarda ahí r11)
L_STRUCT = 0x0C021FB0     # literal 0x0C2892D0 (estructuras: 20 bytes por jugador)
# registros que llegan del código anterior: r11 (bandera), r12 = 0x0C289491 (crudo J1, 16 B/jugador),
# r14 = 0x0C2896B2 (analógicos, 8 palabras por jugador). r8-r10 se restauran al final: se usan libremente.

# Ajustes (frames a 60 Hz)
HOLD  = 15     # atrás mantenido + freno -> marcha atrás
LONG  = 45     # atrás mantenido sin freno -> marcha atrás
BRAKE = 0x50   # umbral del freno (byte alto del analógico 2)
HORN  = 20     # START mantenido más de esto -> bocina (si no, al soltar -> vista)

# bits del byte 0 de cada jugador JVS
UP, DOWN, LEFT, B1, START = 0x20, 0x10, 0x08, 0x02, 0x80

def build():
    a = Asm(A_START)
    # ---------- hueco A ----------
    a.movl_pc(L_127A7C, 3); a.movl_st(11, 3)           # igual que el original: *(0x0C127A7C) = r11
    a.movl_pc(L_STRUCT, 10)                             # r10 = estructuras (el pool no se alcanza desde B)
    a.mov(12, 2); a.addi(8, 2)                          # r2 = estado: +2 marcha, +3 cuenta atrás, +4 cuenta START
    a.movb_ld(12, 1)                                    # r1 = byte0 crudo del J1
    a.movb_d_r0(2, 2); a.mov(0, 5)                      # r5 = marcha (0 corta, 1 larga)
    a.movb_d_r0(3, 2); a.extub(0, 6)                    # r6 = frames con la palanca atrás
    a.mov(1, 0)
    a.tst_i(UP); a.bt('no_fwd'); a.movi(1, 5)           # adelante -> larga
    a.label('no_fwd')
    a.tst_i(DOWN); a.bfs('back'); a.movi(LONG, 3)
    a.bra('back_done'); a.movi(0, 6)                    # sin palanca atrás: cuenta = 0
    a.label('back')
    a.movi(0, 5)                                        # atrás -> corta
    a.cmpge(3, 6); a.bt('back_done'); a.addi(1, 6)      # cuenta++ (satura en LONG)
    a.label('back_done')
    a.bra('B'); a.nop()
    assert a.pc <= A_END, hex(a.pc)
    # ---------- hueco B ----------
    a.org_(B_START); a.label('B')
    a.mov(6, 0); a.movb_r0_d(3, 2); a.mov(5, 0); a.movb_r0_d(2, 2)
    a.movi(DOWN, 9); a.tst(5, 5); a.bt('gear_ok'); a.movi(UP, 9)       # r9 = bits de marcha del J2
    a.label('gear_ok')
    a.cmpge(3, 6); a.bt('rev')                                         # atrás >= LONG
    a.movi(HOLD, 0); a.cmpge(0, 6); a.bf('p2')                          # atrás >= HOLD ...
    a.movw_d_r0(4, 14); a.shlr8(0); a.extub(0, 0); a.movi(BRAKE, 7); a.cmphs(7, 0); a.bf('p2')  # ... y freno
    a.label('rev'); a.movi(DOWN | LEFT, 9)
    a.label('p2')
    a.movi(16, 0); a.movb_r0idx(12, 0); a.and_i(0xFF & ~(UP | DOWN | LEFT)); a.or_(0, 9)   # r9 = byte0 J2
    # START: vista / bocina
    a.mov(1, 0); a.and_i(0xFF & ~(UP | DOWN)); a.mov(0, 8)             # r8 = byte0 J1 sin la palanca
    a.movb_d_r0(4, 2); a.extub(0, 6); a.movi(HORN, 3)
    a.mov(1, 0); a.tst_i(START); a.bt('s_rel')
    a.cmpge(3, 6); a.bf('s_inc')
    a.mov(8, 0); a.or_i(B1); a.bra('s_done'); a.mov(0, 8)              # bocina
    a.label('s_inc'); a.bra('s_done'); a.addi(1, 6)
    a.label('s_rel')
    a.tst(6, 6); a.bt('s_zero'); a.cmpge(3, 6); a.bt('s_zero')
    a.mov(8, 0); a.or_i(DOWN); a.mov(0, 8)                             # vista (1 frame al soltar)
    a.label('s_zero'); a.movi(0, 6)
    a.label('s_done'); a.mov(6, 0); a.movb_r0_d(4, 2)
    # bucle compacto de estructuras (mismo resultado que el original desenrollado)
    a.tst(11, 11); a.bt('end')
    a.mov(10, 4); a.mov(12, 7); a.mov(14, 5); a.movi(2, 6)
    a.label('loop')
    a.movw_ld(4, 1); a.mov(1, 0); a.movw_r0_d(2, 4)                    # anterior = actual
    a.movb_d_r0(1, 7); a.addi(16, 7); a.extub(8, 3); a.shll8(0); a.or_(3, 0); a.movw_st(0, 4)
    a.mov(9, 8)                                                        # el J2 usa r9
    a.xor(0, 1); a.and_(1, 0); a.movw_r0_d(4, 4); a.xor(1, 0); a.movw_r0_d(6, 4)
    a.movw_ld(5, 0); a.extuw(0, 0); a.movl_st_d(0, 8, 4)
    a.movw_d_r0(2, 5); a.extuw(0, 0); a.movl_st_d(0, 12, 4)
    a.movw_d_r0(4, 5); a.extuw(0, 0); a.movl_st_d(0, 16, 4)
    a.addi(16, 5); a.dt(6); a.bfs('loop'); a.addi(20, 4)
    a.label('end')
    assert a.pc <= B_END, f'no cabe: {hex(a.pc)} > {hex(B_END)}'
    while a.pc < B_END: a.nop()
    return a.finish()

def ips(records):
    out = bytearray(b'PATCH')
    for addr, data in records:
        off = addr - BASE
        out += struct.pack('>I', off)[1:] + struct.pack('>H', len(data)) + data
    return bytes(out + b'EOF')

if __name__ == '__main__':
    segs = build()
    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, '18wheeler_ct.ips'), 'wb').write(ips(segs))
    for addr, data in segs:
        print(f'0x{addr:08X}: {len(data)} bytes')
