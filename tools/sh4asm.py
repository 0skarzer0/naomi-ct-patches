"""Ensamblador SH-4 mínimo para escribir parches a mano (usado por los build_patch.py)."""
import struct

def r(n): return n & 0xF
class Asm:
    """Ensamblador SH-4 mínimo (little endian). Admite saltar huecos con org()."""
    def __init__(s, org): s.org=org; s.code=[]; s.labels={}; s.fix=[]; s.addrs=[]; s._pc=org
    @property
    def pc(s): return s._pc
    def org_(s, addr): s._pc=addr
    def label(s,n): s.labels[n]=s.pc
    def w(s,v): s.code.append(v & 0xFFFF); s.addrs.append(s._pc); s._pc+=2
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

    # instrucciones extra (18 Wheeler)
    def bt(s,lbl): s.fix.append((len(s.code),'bts',lbl)); s.w(0x8900)
    def bf(s,lbl): s.fix.append((len(s.code),'bts',lbl)); s.w(0x8B00)
    def tst_i(s,i): s.w(0xC800|(i&0xFF))
    def or_i(s,i):  s.w(0xCB00|(i&0xFF))
    def tst(s,m,n): s.w(0x2008|r(n)<<8|r(m)<<4)
    def cmpge(s,m,n): s.w(0x3003|r(n)<<8|r(m)<<4)   # n >= m (con signo)
    def cmphs(s,m,n): s.w(0x3002|r(n)<<8|r(m)<<4)   # n >= m (sin signo)
    def cmpgt(s,m,n): s.w(0x3007|r(n)<<8|r(m)<<4)
    def extuw(s,m,n): s.w(0x600D|r(n)<<8|r(m)<<4)
    def movb_r0idx(s,m,n): s.w(0x000C|r(n)<<8|r(m)<<4)  # mov.b @(R0,Rm),Rn
    def movl_st_d(s,m,d,n): assert d%4==0 and 0<=d<64; s.w(0x1000|r(n)<<8|r(m)<<4|(d//4))  # mov.l Rm,@(d,Rn)
    def movl_st(s,m,n): s.w(0x2002|r(n)<<8|r(m)<<4)     # mov.l Rm,@Rn
    def finish(s):
        for idx,kind,lbl in s.fix:
            a=s.addrs[idx]; d=(s.labels[lbl]-(a+4))//2
            if kind=='bra': assert -2048<=d<2048; s.code[idx]|=d&0xFFF
            else: assert -128<=d<128; s.code[idx]|=d&0xFF
        # devuelve segmentos contiguos [(dir, bytes)]
        segs=[]
        for a,v in zip(s.addrs,s.code):
            if segs and segs[-1][0]+len(segs[-1][1])==a: segs[-1][1].extend(struct.pack('<H',v))
            else: segs.append((a,bytearray(struct.pack('<H',v))))
        return [(a,bytes(b)) for a,b in segs]

