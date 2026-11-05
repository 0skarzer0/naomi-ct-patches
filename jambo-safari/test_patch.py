"""Prueba: python3 test_patch.py ROM.bin ../tools build_patch.py  (compara la función original + puente físico simulado con la parcheada)"""
import sys, random, importlib.util
sys.path.insert(0, sys.argv[2]); from sh4mini import CPU
spec=importlib.util.spec_from_file_location('bp', sys.argv[3]); bp=importlib.util.module_from_spec(spec); spec.loader.exec_module(bp)
rom=open(sys.argv[1],'rb').read(); B=bp.BASE
def mem_with(code=None):
    lo,hi=0x0C021000,0x0C022000
    m={B+i-0:rom[i-0] for i in range(lo-B,hi-B)}
    if code:
        for i,b in enumerate(code): m[bp.FUNC+i]=b
    return m
RAW, CNT, SW, AN, AD = 0x0C2892F5, 0x0C289738, 0x0C2AB3B0, 0x0C289536, 0x0C2AB3D0
def swap(b, cross): x=b&0x30; return (((x<<1)|(x>>1))&0x30) if cross else x
for variant in ('cruzado','directo'):
    cross = variant=='cruzado'
    mo=mem_with(); mp=mem_with(bp.build(variant))
    co=CPU(mo,bp.X_JVS); cp=CPU(mp,bp.X_JVS)
    rnd=random.Random(1); frames=0
    for f in range(3000):
        players=rnd.choice([2,2,2,2,1,0,3])
        raw=[rnd.randrange(256) for _ in range(16*4)]
        an=[rnd.randrange(65536) for _ in range(8)]
        for m in (mo,mp):
            for i,b in enumerate(raw): m[RAW+i]=b
            for i,w in enumerate(an): m[AN+2*i]=w&0xFF; m[AN+2*i+1]=w>>8
            for i in range(4): m[CNT+i]=(players>>(8*i))&0xFF
        # el original ve en J2.. el byte0 con la palanca del J1 añadida (lo que haría el puente físico)
        inj=swap(raw[0],cross)
        for p in range(1,players): mo[RAW+16*p]=raw[16*p]|inj
        co.call(bp.FUNC); cp.call(bp.FUNC)
        for a in range(SW, AD+32):
            assert mo.get(a,0)==mp.get(a,0), (variant,f,players,hex(a),mo.get(a,0),mp.get(a,0))
        frames+=1
    print(f'{variant}: {frames} frames idénticos al original con el puente físico simulado')
# comprobación semántica directa
m=mem_with(bp.build('cruzado')); c=CPU(m,bp.X_JVS)
for i in range(4): m[CNT+i]=[2,0,0,0][i]
for i in range(32): m[RAW+i]=0
m[RAW]=0x20  # palanca de Crazy Taxi hacia delante (Drive = ARRIBA del J1)
c.call(bp.FUNC); c.call(bp.FUNC)
print('cruzado, palanca adelante -> J2 actual = %04x (0x0010 = ABAJO del J2 = "LEVER UP"/lazo en Jambo)'%(m[SW+8]|m[SW+9]<<8))
