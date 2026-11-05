#!/usr/bin/env python3
"""Genera el parche de controles de Jambo! Safari (NAOMI, 840-0013) para el mueble Crazy Taxi.

Reescribe la función 0x0C0217CC (copia de entradas JVS -> estructuras por jugador) en su
mismo espacio (0x68 bytes) e inyecta los bits ARRIBA/ABAJO del jugador 1 (donde Crazy Taxi
cablea la palanca D/R) en la estructura del jugador 2 (donde Jambo! Safari la lee).

Uso: python3 build_patch.py  -> escribe jambo_ct_cruzado.ips y jambo_ct_directo.ips
No contiene ni necesita la ROM: solo código propio.
"""
import struct, sys, os

BASE   = 0x0C020000          # dirección de carga del offset 0 de la ROM
FUNC   = 0x0C0217CC          # inicio de la función original
FEND   = 0x0C021834          # siguiente función (no se toca)
X_JVS  = 0x0C021334          # función que copia la respuesta JVS al búfer crudo
# literales ya existentes en el pool que sigue a la función siguiente (no se modifican)
L_SW, L_CNT, L_RAW, L_AN, L_AD = 0x0C0218A8, 0x0C0218AC, 0x0C0218B0, 0x0C0218B4, 0x0C0218B8

def r(n): return n & 0xF
class Asm:
    def __init__(s, org): s.org=org; s.code=[]; s.labels={}; s.fix=[]
    @property
    def pc(s): return s.org + 2*len(s.code)
    def label(s,n): s.labels[n]=s.pc
    def w(s,v): s.code.append(v & 0xFFFF)
    # instrucciones
    def nop(s): s.w(0x0009)
    def rts(s): s.w(0x000B)
    def sts_l_pr_push(s): s.w(0x4F22)
    def lds_l_pr_pop(s): s.w(0x4F26)
    def bsr(s,t): d=(t-(s.pc+4))//2; assert -2048<=d<2048; s.w(0xB000|(d&0xFFF))
    def bra(s,lbl): s.fix.append((len(s.code),'bra',lbl)); s.w(0xA000)
    def bts(s,lbl): s.fix.append((len(s.code),'bts',lbl)); s.w(0x8D00)
    def bfs(s,lbl): s.fix.append((len(s.code),'bfs',lbl)); s.w(0x8F00)
    def movl_pc(s,lit,n):
        base=(s.pc & ~3)+4; d=(lit-base)//4; assert lit%4==0 and 0<=d<256, hex(lit)
        s.w(0xD000|r(n)<<8|d)
    def movb_ld(s,m,n): s.w(0x6000|r(n)<<8|r(m)<<4|0)   # mov.b @Rm,Rn
    def movw_ld(s,m,n): s.w(0x6000|r(n)<<8|r(m)<<4|1)   # mov.w @Rm,Rn
    def movl_ld(s,m,n): s.w(0x6000|r(n)<<8|r(m)<<4|2)   # mov.l @Rm,Rn
    def mov(s,m,n):     s.w(0x6000|r(n)<<8|r(m)<<4|3)
    def movw_inc(s,m,n):s.w(0x6000|r(n)<<8|r(m)<<4|5)   # mov.w @Rm+,Rn
    def extub(s,m,n):   s.w(0x6000|r(n)<<8|r(m)<<4|0xC)
    def movb_st(s,m,n): s.w(0x2000|r(n)<<8|r(m)<<4|0)   # mov.b Rm,@Rn
    def movw_st(s,m,n): s.w(0x2000|r(n)<<8|r(m)<<4|1)   # mov.w Rm,@Rn
    def and_(s,m,n):    s.w(0x2009|r(n)<<8|r(m)<<4)
    def xor(s,m,n):     s.w(0x200A|r(n)<<8|r(m)<<4)
    def or_(s,m,n):     s.w(0x200B|r(n)<<8|r(m)<<4)
    def and_i(s,i):     s.w(0xC900|(i&0xFF))
    def movi(s,i,n):    s.w(0xE000|r(n)<<8|(i&0xFF))
    def addi(s,i,n):    s.w(0x7000|r(n)<<8|(i&0xFF))
    def shll(s,n):  s.w(0x4000|r(n)<<8)
    def shlr(s,n):  s.w(0x4001|r(n)<<8)
    def shll8(s,n): s.w(0x4018|r(n)<<8)
    def shlr8(s,n): s.w(0x4019|r(n)<<8)
    def dt(s,n):    s.w(0x4010|r(n)<<8)
    def cmppl(s,n): s.w(0x4015|r(n)<<8)
    def movb_r0_d(s,d,n): s.w(0x8000|r(n)<<4|d)        # mov.b R0,@(d,Rn)
    def movb_d_r0(s,d,m): s.w(0x8400|r(m)<<4|d)        # mov.b @(d,Rm),R0
    def movw_r0_d(s,d,n): s.w(0x8100|r(n)<<4|(d//2))   # mov.w R0,@(d,Rn)
    def movw_d_r0(s,d,m): s.w(0x8500|r(m)<<4|(d//2))   # mov.w @(d,Rm),R0
    def finish(s):
        for idx,kind,lbl in s.fix:
            a=s.org+2*idx; d=(s.labels[lbl]-(a+4))//2
            if kind=='bra': assert -2048<=d<2048; s.code[idx]|=d&0xFFF
            else: assert -128<=d<128; s.code[idx]|=d&0xFF
        return b''.join(struct.pack('<H',v) for v in s.code)

def build(variant):
    a=Asm(FUNC)
    a.sts_l_pr_push(); a.bsr(X_JVS); a.nop(); a.lds_l_pr_pop()   # lectura JVS (igual que el original)
    a.movl_pc(L_RAW,7)            # r7 = búfer crudo, jugador 1 (byte0: START SERV UP DOWN LEFT RIGHT B1 B2)
    a.movb_ld(7,0); a.and_i(0x30) # r0 = ARRIBA|ABAJO del J1
    a.mov(0,6)
    if variant=='cruzado':        # intercambia ARRIBA<->ABAJO
        a.shll(0); a.shlr(6); a.or_(6,0); a.and_i(0x30)
    else:
        a.nop(); a.nop(); a.nop(); a.nop()
    a.mov(0,6)                    # r6 = bits a inyectar en J2 y siguientes
    a.movl_pc(L_CNT,1); a.movl_ld(1,5)   # r5 = número de jugadores JVS
    a.movl_pc(L_SW,4)             # r4 = estructuras de botones (8 bytes por jugador)
    a.bra('chk'); a.movi(0,2)     # r2 = inyección para el jugador actual (0 en J1)
    a.label('body')               # (r1 = anterior, cargado en el hueco de retardo de bt/s)
    a.mov(1,0); a.movw_r0_d(2,4)  # +2 anterior = actual previo
    a.movb_d_r0(1,7); a.movb_ld(7,3); a.addi(16,7)
    a.extub(3,3); a.or_(2,3); a.shll8(0); a.or_(3,0)   # r0 = actual = b1<<8 | b0 | inyección
    a.movw_st(0,4)                # +0 actual
    a.xor(0,1); a.and_(1,0); a.movw_r0_d(4,4)          # +4 pulsado = actual & cambiado
    a.xor(1,0); a.movw_r0_d(6,4)                       # +6 soltado = pulsado ^ cambiado = anterior & ~actual
    a.mov(6,2); a.addi(8,4); a.dt(5)
    a.label('chk'); a.cmppl(5); a.bts('body'); a.movw_ld(4,1)
    # analógicos (sin cambios de comportamiento): 8 canales, byte alto actual y anterior
    a.movl_pc(L_AD,4); a.movl_pc(L_AN,5); a.movi(8,6)
    a.label('an')
    a.movb_ld(4,0); a.movb_r0_d(1,4); a.movw_inc(5,3); a.shlr8(3); a.movb_st(3,4)
    a.dt(6); a.bfs('an'); a.addi(4,4)
    a.rts(); a.nop()
    code=a.finish()
    assert FUNC+len(code)<=FEND, f'no cabe: {len(code)} bytes'
    code+=b'\x09\x00'*((FEND-FUNC-len(code))//2)
    return code

def ips(records):
    out=bytearray(b'PATCH')
    for off,data in records:
        out+=struct.pack('>I',off)[1:]+struct.pack('>H',len(data))+data
    return bytes(out+b'EOF')

if __name__=='__main__':
    here=os.path.dirname(os.path.abspath(__file__))
    for v in ('cruzado','directo'):
        code=build(v)
        p=os.path.join(here,f'jambo_ct_{v}.ips')
        open(p,'wb').write(ips([(FUNC-BASE,code)]))
        print(f'{v}: {len(code)} bytes en 0x{FUNC-BASE:06X} -> {os.path.basename(p)}')
