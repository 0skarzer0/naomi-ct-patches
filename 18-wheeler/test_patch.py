"""Prueba del parche de 18 Wheeler en el intérprete SH-4.
Uso: python3 test_patch.py ROM.bin ../tools build_patch.py

1) Equivalencia: la función original, alimentada con lo que mandaría un arnés físico que hiciera la
   lógica acordada (modelo en Python), da las mismas estructuras de jugador que la función parcheada
   alimentada con lo que manda el mueble Crazy Taxi.
2) Escenarios: toques, mantener, freno, START corto y largo.
"""
import sys, random, importlib.util, gzip
sys.path.insert(0, sys.argv[2]); from sh4mini import CPU
spec=importlib.util.spec_from_file_location('bp', sys.argv[3]); bp=importlib.util.module_from_spec(spec); spec.loader.exec_module(bp)
data=open(sys.argv[1],'rb').read()
rom=gzip.decompress(data) if data[:2]==b'\x1f\x8b' else data
B=bp.BASE; RAW=0x0C289491; AN=0x0C2896B2; ST=0x0C2892D0; STATE=RAW+8; END=bp.B_END
def mem(patched):
    m={B+i:rom[i] for i in range(0x1000,0x3000)}
    if patched:
        for addr,d in bp.build():
            for i,b in enumerate(d): m[addr+i]=b
    return m
def run(m, raw, an):
    for i in (0,1,16,17): m[RAW+i]=raw[i]     # la I/O solo escribe 2 bytes por jugador
    for i,w in enumerate(an): m[AN+2*i]=w&0xFF; m[AN+2*i+1]=(w>>8)&0xFF
    c=CPU(m,None); c.R[11]=1; c.R[12]=RAW; c.R[13]=0; c.R[14]=AN; c.R[15]=0x0CFF0000
    for r in (8,9,10): c.R[r]=0xDEADBEEF
    c.run_until(bp.A_START, END)
    return bytes(m.get(ST+i,0) for i in range(40))

class Model:   # la lógica acordada, en Python
    def __init__(s): s.gear=0; s.back=0; s.start=0
    def frame(s, b0p1, b0p2, brake):
        if b0p1&0x20: s.gear=1
        if b0p1&0x10:
            s.gear=0
            if s.back<bp.LONG: s.back+=1
        else: s.back=0
        p2 = 0x20 if s.gear else 0x10
        if s.back>=bp.LONG or (s.back>=bp.HOLD and (brake>>8)>=bp.BRAKE): p2=0x18
        p1 = b0p1 & ~0x30
        if b0p1&0x80:
            if s.start>=bp.HORN: p1|=0x02
            else: s.start+=1
        else:
            if 0<s.start<bp.HORN: p1|=0x10
            s.start=0
        return p1&0xFF, ((b0p2 & 0xC7) | p2)&0xFF

def u16(b,o): return b[o]|b[o+1]<<8
mo=mem(False); mp=mem(True); model=Model()
rnd=random.Random(7)
lever=0; startp=0
for f in range(6000):
    # entradas "humanas": la palanca y START cambian de vez en cuando y se mantienen
    if rnd.random()<0.05: lever=rnd.choice([0,0,0x20,0x10])
    if rnd.random()<0.04: startp=rnd.choice([0,0x80])
    raw=[rnd.randrange(256) for _ in range(32)]
    raw[0]=(raw[0]&0x4F)|lever|startp      # J1: el resto de bits aleatorios (SERVICE, botones...)
    an=[rnd.randrange(65536) for _ in range(16)]
    p1,p2=model.frame(raw[0],raw[16],an[2])
    rawo=list(raw); rawo[0]=p1; rawo[16]=p2
    so=run(mo,rawo,an); sp=run(mp,raw,an)
    assert so==sp, (f, so.hex(), sp.hex())
print('Equivalencia: 6000 frames idénticos al original con el arnés lógico simulado')

# Escenarios concretos con el parche
m=mem(True)
def frame(lever=0,start=0,brake=0):
    raw=[0]*32; raw[0]=lever|start; an=[0]*16; an[2]=brake
    s=run(m,raw,an); return u16(s,0), u16(s,20)   # (J1 actual, J2 actual)
def gear(w2): return {0x20:'LARGA',0x10:'CORTA',0x18:'ATRÁS',0:'—'}.get(w2&0x38,hex(w2))
log=[]
for _ in range(3): frame()
for _ in range(3): frame(lever=0x20)
j1,j2=frame(); log.append(('toque adelante',gear(j2))); assert gear(j2)=='LARGA'
for _ in range(60): j1,j2=frame()
assert gear(j2)=='LARGA'; log.append(('...1 s después',gear(j2)))
for _ in range(3): frame(lever=0x10)
j1,j2=frame(); assert gear(j2)=='CORTA'; log.append(('toque atrás',gear(j2)))
for i in range(bp.HOLD+2): j1,j2=frame(lever=0x10,brake=0xC000)
assert gear(j2)=='ATRÁS'; log.append((f'atrás {bp.HOLD+2} frames + freno',gear(j2)))
j1,j2=frame(); assert gear(j2)=='CORTA'; log.append(('soltar',gear(j2)))
for i in range(bp.HOLD+2): j1,j2=frame(lever=0x10)
assert gear(j2)=='CORTA'; log.append((f'atrás {bp.HOLD+2} frames sin freno',gear(j2)))
for i in range(bp.LONG): j1,j2=frame(lever=0x10)
assert gear(j2)=='ATRÁS'; log.append((f'atrás {bp.HOLD+2+bp.LONG} frames sin freno',gear(j2)))
for _ in range(2): frame(lever=0x20)
j1,j2=frame(); assert gear(j2)=='LARGA'; log.append(('toque adelante',gear(j2)))
# palanca ya no llega al J1
j1,j2=frame(lever=0x10); assert j1&0x30==0; log.append(('palanca atrás: J1 ABAJO (vista)', 'no' if not j1&0x10 else 'sí'))
frame()
# START corto -> vista 1 frame
frame(start=0x80); frame(start=0x80); j1,_=frame(); assert j1&0x10; log.append(('START corto, al soltar: VISTA', 'sí'))
j1,_=frame(); assert not j1&0x10
# START largo -> bocina, sin vista al soltar
hs=[frame(start=0x80)[0] for _ in range(bp.HORN+10)]
assert not any(h&0x02 for h in hs[:bp.HORN]) and all(h&0x02 for h in hs[bp.HORN:]) and all(h&0x80 for h in hs)
log.append(('START mantenido: BOCINA desde el frame', bp.HORN+1))
j1,_=frame(); assert not j1&0x12; log.append(('soltar tras bocina: vista', 'no'))
for k,v in log: print(f'  {k:38s} -> {v}')
print('Escenarios OK')
