"""Prueba del parche de Initial D en el intérprete SH-4.
Uso: python3 test_patch.py ROM.bin[.gz] ../tools build_patch.py

1) Equivalencia: los bucles originales alimentados con lo que mandaría un arnés con la lógica acordada
   (modelo en Python) dan las mismas estructuras que los bucles parcheados alimentados con lo que manda
   el mueble Crazy Taxi. Varía jugadores (0-3) y bytes por jugador (0-8).
2) Escenarios: palanca adelante/atrás, START corto/largo.
"""
import sys, random, importlib.util, gzip
sys.path.insert(0, sys.argv[2]); from sh4mini import CPU
spec=importlib.util.spec_from_file_location('bp', sys.argv[3]); bp=importlib.util.module_from_spec(spec); spec.loader.exec_module(bp)
data=open(sys.argv[1],'rb').read()
rom=gzip.decompress(data) if data[:2]==b'\x1f\x8b' else data
B=bp.BASE; RO=bp.ROMOFF
CNT=0x0C8D85FC; SYSB=0x0C8D860C; RAW=0x0C8D860D; SYS=0x0C7DDFF0; PST=0x0C7DE030
def mem(patched):
    m={a:rom[a-B+RO] for a in range(0x0C157800,0x0C157C00)}
    if patched:
        for addr,d in bp.build():
            for i,b in enumerate(d): m[addr+i]=b
    return m
def put32(m,a,v):
    for i in range(4): m[a+i]=(v>>(8*i))&0xFF
def run(m, sysb, raw, npl, bpp):
    put32(m,CNT,npl); put32(m,CNT+4,bpp); put32(m,CNT+8,0)
    m[SYSB]=sysb
    for p in range(4):
        for j in range(bpp): m[RAW+16*p+j]=raw[16*p+j]
    c=CPU(m,None); c.R[15]=0x0CFF0000; c.R[14]=0x0CFF0000; c.PR=0x0CABCDE0
    c.run_until(bp.START, bp.END)
    st=bytes(m.get(SYS+i,0) for i in range(64))+bytes(m.get(PST+i,0) for i in range(64*4))
    return st, c.R[10], c.R[11]

class Model:
    def __init__(s): s.start=0
    def frame(s, b1, b2):
        view=0
        if b1&0x80:
            if s.start<bp.VIEW_MAX: s.start+=1
        else:
            if 0<s.start<bp.VIEW_MAX: view=0x10
            s.start=0
        return ((b1&0xCF)|view)&0xFF, (b2|(b1&0x30))&0xFF

mo=mem(False); mp=mem(True); model=Model(); rnd=random.Random(3)
lever=0; st=0; last0=0; last16=0   # lo que queda en el búfer crudo (con bpp=0 la I/O no escribe)
for f in range(8000):
    if rnd.random()<0.06: lever=rnd.choice([0,0,0x20,0x10])
    if rnd.random()<0.05: st=rnd.choice([0,0x80])
    npl=rnd.choice([2,2,2,2,1,0,3]); bpp=rnd.choice([2,2,2,3,1,0,8])
    raw=[rnd.randrange(256) for _ in range(64)]; raw[0]=(raw[0]&0x4F)|lever|st
    sysb=rnd.randrange(256)
    if bpp>0: last0=raw[0]
    if bpp>0 and npl>=2: last16=raw[16]
    p1,p2=model.frame(last0,last16)
    rawo=list(raw)
    if bpp>0: rawo[0]=p1
    if bpp>0 and npl>=2: rawo[16]=p2
    if bpp>=9: raise SystemExit('bpp>=9 no soportado')
    so=run(mo,sysb,rawo,npl,bpp); sp=run(mp,sysb,raw,npl,bpp)
    assert so==sp, (f,npl,bpp,[i for i in range(len(so[0])) if so[0][i]!=sp[0][i]][:8], so[1:], sp[1:])
print('Equivalencia: 8000 frames idénticos al original con el arnés lógico simulado')

m=mem(True); log=[]
def fr(lever=0,start=0):
    raw=[0]*64; raw[0]=lever|start
    s,_,_=run(m,0,raw,2,2)
    j1=s[64]; j2=s[64+64]; j1p=s[64+32]; j2p=s[64+64+32]
    return j1,j2,j1p,j2p
fr(); j1,j2,_,j2p=fr(lever=0x20); assert j2&0x20 and j2p&0x20 and not j1&0x30; log.append(('palanca adelante','SUBIR marcha (J2 ARRIBA), J1 sin palanca'))
j1,j2,_,j2p=fr(lever=0x20); assert j2&0x20 and not j2p&0x20; log.append(('mantenida','sin nueva pulsación'))
fr(); j1,j2,j1p,j2p=fr(lever=0x10); assert j2&0x10 and j2p&0x10 and not j1&0x10; log.append(('palanca atrás','BAJAR marcha (J2 ABAJO), sin vista'))
fr(); fr(start=0x80); fr(start=0x80); j1,_,j1p,_=fr(); assert j1&0x10 and j1p&0x10; log.append(('START corto, al soltar','VISTA (J1 ABAJO pulsado)'))
j1,_,_,_=fr(); assert not j1&0x10
for _ in range(bp.VIEW_MAX+5): j1,_,_,_=fr(start=0x80); assert j1&0x80 and not j1&0x10
j1,_,_,_=fr(); assert not j1&0x10; log.append((f'START mantenido {bp.VIEW_MAX+5} frames','START normal, sin vista'))
for k,v in log: print(f'  {k:32s} -> {v}')
print('Escenarios OK')
