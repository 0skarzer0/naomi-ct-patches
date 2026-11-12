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
    def run_until(s,pc,stop,maxsteps=100000):
        n=0
        while pc!=stop:
            n+=1; assert n<maxsteps, hex(pc)
            pc=s.step(pc)
        return n
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
        elif op>>8==0xCB: R[0]|=i8
        elif hi==0x1: s.wl((R[n]+lo*4)&M,R[m])
        elif hi==0x0 and lo==0xC: R[n]=sx8(s.rb((R[0]+R[m])&M))&M
        elif hi==0x0 and lo==0xD: R[n]=sx16(s.rw((R[0]+R[m])&M))&M
        elif hi==0x0 and lo==0x6: s.wl((R[0]+R[n])&M,R[m])
        elif hi==0x0 and lo==0x4: s.wb((R[0]+R[n])&M,R[m])
        elif hi==0x0 and lo==0x5: s.ww((R[0]+R[n])&M,R[m])
        elif hi==0x0 and lo==0xE: R[n]=s.rl((R[0]+R[m])&M)
        elif hi==0x0 and (op&0xFF)==0x23: return dslot((pc+4+R[n])&M)    # braf Rn
        elif hi==0x0 and (op&0xFF)==0x29: R[n]=s.T                         # movt
        elif hi==0x0 and lo==0x7: s.MACL=(R[n]*R[m])&M                     # mul.l
        elif hi==0x0 and (op&0xFF)==0x1A: R[n]=getattr(s,'MACL',0)         # sts macl
        elif hi==0x0 and (op&0xFF)==0x08: s.T=0                            # clrt
        elif hi==0x0 and (op&0xFF)==0x18: s.T=1                            # sett
        elif hi==0x5: R[n]=s.rl((R[m]+lo*4)&M)
        elif op>>8==0xC8: s.T=int((R[0]&i8)==0)
        elif op>>8==0x88: s.T=int(R[0]==(sx8(i8)&M))
        elif op>>8==0xCA: R[0]^=i8
        elif op>>8==0xC7: R[0]=((pc+4)&~3)+i8*4                            # mova
        elif op>>8==0x80: s.wb(R[m]+lo,R[0])
        elif op>>8==0x81: s.ww(R[m]+lo*2,R[0])
        elif op>>8==0x84: R[0]=sx8(s.rb(R[m]+lo))&M
        elif op>>8==0x85: R[0]=sx16(s.rw(R[m]+lo*2))&M
        elif hi==0x6:
            if lo==0: R[n]=sx8(s.rb(R[m]))&M
            elif lo==1: R[n]=sx16(s.rw(R[m]))&M
            elif lo==2: R[n]=s.rl(R[m])
            elif lo==3: R[n]=R[m]
            elif lo==4: v=sx8(s.rb(R[m]))&M; R[m]=(R[m]+1)&M; R[n]=v
            elif lo==5: v=sx16(s.rw(R[m]))&M; R[m]=(R[m]+2)&M; R[n]=v
            elif lo==7: R[n]=(~R[m])&M
            elif lo==0xC: R[n]=R[m]&0xFF
            elif lo==0xD: R[n]=R[m]&0xFFFF
            elif lo==0xE: R[n]=sx8(R[m])&M
            elif lo==0xF: R[n]=sx16(R[m])&M
            elif lo==0xB: R[n]=(-R[m])&M
            elif lo==0x6: v=s.rl(R[m]); R[m]=(R[m]+4)&M; R[n]=v
            elif lo==0x8: R[n]=((R[m]&0xFFFF)<<16)|((R[m]>>16)&0xFFFF)   # swap.w
            elif lo==0x9: R[n]=(R[m]&0xFFFF0000)|((R[m]&0xFF)<<8)|((R[m]>>8)&0xFF)  # swap.b
            else: raise Exception(hex(op))
        elif hi==0x2:
            if lo==0: s.wb(R[n],R[m])
            elif lo==1: s.ww(R[n],R[m])
            elif lo==2: s.wl(R[n],R[m])
            elif lo==4: R[n]=(R[n]-1)&M; s.wb(R[n],R[m])
            elif lo==5: R[n]=(R[n]-2)&M; s.ww(R[n],R[m])
            elif lo==6: R[n]=(R[n]-4)&M; s.wl(R[n],R[m])
            elif lo==9: R[n]&=R[m]
            elif lo==0xA: R[n]^=R[m]
            elif lo==0xB: R[n]|=R[m]
            elif lo==8: s.T=int((R[n]&R[m])==0)
            else: raise Exception(hex(op))
        elif hi==0x3:
            a,b=R[n],R[m]; sa=a-(1<<32) if a>>31 else a; sb=b-(1<<32) if b>>31 else b
            if lo==0: s.T=int(a==b)
            elif lo==2: s.T=int(a>=b)
            elif lo==3: s.T=int(sa>=sb)
            elif lo==7: s.T=int(sa>sb)
            elif lo==0xC: R[n]=(a+b)&M
            elif lo==0x8: R[n]=(a-b)&M
            elif lo==0x6: s.T=int(a>b)
            elif lo==0x4: pass   # div1 (no usado)
            else: raise Exception(hex(op))
        elif hi==0x4 and (op&0xFF) in (0x2B,0x0B):      # jmp @Rm / jsr @Rm
            t=R[n]
            if (op&0xFF)==0x0B: s.PR=pc+4
            return dslot(t)
        elif hi==0x4 and (op&0xFF)==0x22: R[15]=(R[15]-4)&M; s.wl(R[15],s.PR)     # sts.l pr,@-Rn (n=15)
        elif hi==0x4 and (op&0xFF)==0x26: s.PR=s.rl(R[n]); R[n]=(R[n]+4)&M        # lds.l @Rn+,pr
        elif hi==0x4 and (op&0xF)==0xC:                    # shad Rm,Rn
            sh=R[m]; v=R[n]-(1<<32) if R[n]>>31 else R[n]
            if sh>>31:
                k=((~sh)&0x1F)+1; v=v>>k if k<32 else (-1 if v<0 else 0)
            else: v=v<<(sh&0x1F)
            R[n]=v&M
        elif hi==0x4 and (op&0xF)==0xD:                    # shld Rm,Rn
            sh=R[m]
            if sh>>31:
                k=((~sh)&0x1F)+1; R[n]=(R[n]>>k) if k<32 else 0
            else: R[n]=(R[n]<<(sh&0x1F))&M
        elif hi==0x4:
            k=op&0xFF
            if k==0x00: s.T=R[n]>>31; R[n]=(R[n]<<1)&M
            elif k==0x01: s.T=R[n]&1; R[n]>>=1
            elif k==0x08: R[n]=(R[n]<<2)&M
            elif k==0x09: R[n]>>=2
            elif k==0x28: R[n]=(R[n]<<16)&M
            elif k==0x29: R[n]>>=16
            elif k==0x11: s.T=int(not (R[n]>>31))                     # cmp/pz
            elif k==0x21: s.T=R[n]&1; R[n]=(R[n]>>1)|(R[n]&0x80000000)  # shar
            elif k==0x20: s.T=R[n]>>31; R[n]=(R[n]<<1)&M                # shal
            elif k==0x18: R[n]=(R[n]<<8)&M
            elif k==0x19: R[n]>>=8
            elif k==0x10: R[n]=(R[n]-1)&M; s.T=int(R[n]==0)
            elif k==0x15: s.T=int(0<R[n]<0x80000000)
            else: raise Exception(hex(op))
        else: raise Exception(f'op {op:04x} @ {pc:08x}')
        return nxt
