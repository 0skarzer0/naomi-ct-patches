"""Intérprete SH-4 mínimo (solo las instrucciones de las funciones de entrada de Jambo) para pruebas."""
import struct
def sx8(v): v&=0xFF; return v-0x100 if v&0x80 else v
def sx16(v): v&=0xFFFF; return v-0x10000 if v&0x8000 else v
M=0xFFFFFFFF
class CPU:
    def __init__(s, mem, stub):   # mem: dict addr->byte ; stub: addr of function to skip
        s.m=mem; s.R=[0]*16; s.T=0; s.PR=0; s.stub=stub
    def rb(s,a): return s.m.get(a,0)
    def wb(s,a,v): s.m[a]=v&0xFF
    def rw(s,a): assert a%2==0,hex(a); return s.rb(a)|s.rb(a+1)<<8
    def ww(s,a,v): assert a%2==0,hex(a); s.wb(a,v); s.wb(a+1,v>>8)
    def rl(s,a): assert a%4==0,hex(a); return s.rw(a)|s.rw(a+2)<<16
    def wl(s,a,v): assert a%4==0,hex(a); s.ww(a,v); s.ww(a+2,v>>16)
    def call(s,pc,maxsteps=100000):
        R=s.R; s.PR=0xDEAD0000; R[15]=0x0CFF0000
        n=0
        while pc!=0xDEAD0000:
            n+=1; assert n<maxsteps
            pc=s.step(pc)
        return n
    def step(s,pc,delay=False):
        R=s.R; op=s.rw(pc); hi=op>>12; n=(op>>8)&15; m=(op>>4)&15; lo=op&15; i8=op&0xFF
        nxt=pc+2
        def dslot(target):
            s.step(pc+2,True); return target
        if op==0x0009: pass
        elif op==0x000B: return dslot(s.PR)
        elif op==0x4F22: R[15]=(R[15]-4)&M; s.wl(R[15],s.PR)
        elif op==0x4F26: s.PR=s.rl(R[15]); R[15]=(R[15]+4)&M
        elif hi==0xB:
            d=op&0xFFF; d=d-0x1000 if d&0x800 else d; t=pc+4+d*2
            if t==s.stub: s.step(pc+2,True); return pc+4   # función JVS simulada: no hace nada
            s.PR=pc+4; return dslot(t)
        elif hi==0xA:
            d=op&0xFFF; d=d-0x1000 if d&0x800 else d; return dslot(pc+4+d*2)
        elif hi==0x8 and n in (0x9,0xB,0xD,0xF):
            d=sx8(i8); t=pc+4+d*2
            take = (s.T==1) if n in (0x9,0xD) else (s.T==0)
            if n in (0xD,0xF): s.step(pc+2,True); return t if take else pc+4
            return t if take else nxt
        elif hi==0xD: a=((pc+4)&~3)+i8*4; R[n]=s.rl(a)
        elif hi==0x9: a=pc+4+i8*2; R[n]=sx16(s.rw(a))&M
        elif hi==0xE: R[n]=sx8(i8)&M
        elif hi==0x7: R[n]=(R[n]+sx8(i8))&M
        elif op>>8==0xC9: R[0]&=i8
        elif op>>8==0xC8: s.T=int((R[0]&i8)==0)
        elif op>>8==0x88: s.T=int(R[0]==(sx8(i8)&M))
        elif op>>8==0x80: s.wb(R[m]+lo,R[0])
        elif op>>8==0x81: s.ww(R[m]+lo*2,R[0])
        elif op>>8==0x84: R[0]=sx8(s.rb(R[m]+lo))&M
        elif op>>8==0x85: R[0]=sx16(s.rw(R[m]+lo*2))&M
        elif hi==0x6:
            if lo==0: R[n]=sx8(s.rb(R[m]))&M
            elif lo==1: R[n]=sx16(s.rw(R[m]))&M
            elif lo==2: R[n]=s.rl(R[m])
            elif lo==3: R[n]=R[m]
            elif lo==5: v=sx16(s.rw(R[m]))&M; R[m]=(R[m]+2)&M; R[n]=v
            elif lo==7: R[n]=(~R[m])&M
            elif lo==0xC: R[n]=R[m]&0xFF
            elif lo==0xD: R[n]=R[m]&0xFFFF
            else: raise Exception(hex(op))
        elif hi==0x2:
            if lo==0: s.wb(R[n],R[m])
            elif lo==1: s.ww(R[n],R[m])
            elif lo==2: s.wl(R[n],R[m])
            elif lo==9: R[n]&=R[m]
            elif lo==0xA: R[n]^=R[m]
            elif lo==0xB: R[n]|=R[m]
            elif lo==8: s.T=int((R[n]&R[m])==0)
            else: raise Exception(hex(op))
        elif hi==0x3:
            a,b=R[n],R[m]; sa=a-(1<<32) if a>>31 else a; sb=b-(1<<32) if b>>31 else b
            if lo==0: s.T=int(a==b)
            elif lo==3: s.T=int(sa>=sb)
            elif lo==7: s.T=int(sa>sb)
            elif lo==0xC: R[n]=(a+b)&M
            else: raise Exception(hex(op))
        elif hi==0x4:
            k=op&0xFF
            if k==0x00: s.T=R[n]>>31; R[n]=(R[n]<<1)&M
            elif k==0x01: s.T=R[n]&1; R[n]>>=1
            elif k==0x08: R[n]=(R[n]<<2)&M
            elif k==0x18: R[n]=(R[n]<<8)&M
            elif k==0x19: R[n]>>=8
            elif k==0x10: R[n]=(R[n]-1)&M; s.T=int(R[n]==0)
            elif k==0x15: s.T=int(0<R[n]<0x80000000)
            else: raise Exception(hex(op))
        else: raise Exception(f'op {op:04x} @ {pc:08x}')
        return nxt
