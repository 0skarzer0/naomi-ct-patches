"""Prueba del lector virtual COMPILADO PARA SH-4 dentro del intérprete (../tools/sh4mini.py), entrando por el
gancho del juego (0x0C13A9E0) igual que en la placa. Comprueba el código máquina real, no solo el C.
Uso: python3 test_sh4.py IMAGEN_PARCHEADA.bin.gz"""
import gzip, struct, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from sh4mini import CPU

rom = gzip.decompress(open(sys.argv[1], 'rb').read())
mem = {}
for i in range(8):                                   # cargar como la BIOS: entradas de la tabla de carga
    o, d, s = struct.unpack_from('<3I', rom, 0x360 + 12 * i)
    if o == 0xFFFFFFFF: break
    if d == 0x0C020000:                               # del programa solo hace falta la zona del gancho
        for a in range(0x0C13A900, 0x0C13AB00): mem[a] = rom[o + a - d]
    else:
        for k in range(s): mem[d + k] = rom[o + k]
PORT = 0x0C700000
def ctl(i): return PORT + 0x7FC + 4 * i
def rd32(a): return sum(mem.get(a + k, 0) << (8 * k) for k in range(4))
def wr32(a, v):
    for k in range(4): mem[a + k] = (v >> (8 * k)) & 0xFF
for k in range(0x1200): mem[PORT + k] = 0
def putc(b):
    w = rd32(ctl(5)); mem[PORT + 0x10 + w] = b; wr32(ctl(5), (w + 1) & 0x3FF); wr32(ctl(7), rd32(ctl(7)) + 1)
def getc():
    n = rd32(ctl(8))
    if not n: return None
    b = mem[PORT + 0x410 + ((rd32(ctl(6)) - n + 0x400) & 0x3FF)]; wr32(ctl(8), n - 1); return b
steps = 0
def poll():
    global steps
    c = CPU(mem, None); c.R[4] = PORT; c.R[15] = 0x0CFF0000
    steps += c.call(0x0C13A9E0)
def packet(cmd, params=b''):
    ln = 6 + len(params); bcc = ln; body = bytes([cmd, 0, 0, 0]) + params + b'\x03'
    for b in body: bcc ^= b
    for b in b'\x02' + bytes([ln]) + body + bytes([bcc]): putc(b)
    poll(); assert getc() == 6, 'sin ACK'
    for _ in range(10):
        putc(5); poll()
        r = []
        while True:
            b = getc()
            if b is None: break
            r.append(b)
        assert r[0] == 2 and r[r[1]] == 3, r
        if r[5] != 0x33: return r
    return r
r = packet(0x10, b'\x30'); assert r[4] == 0x30
r = packet(0xB0, b'\x31'); assert r[3] & 0x1F == 0x18, hex(r[3])
data = bytes((i * 3 + 5) & 0xFF for i in range(207))
r = packet(0x53, b'\x30\x31\x36' + data); assert r[4] == 0x30
card = rd32(0x0DF00000 + 12)
assert bytes(mem[card + 16 + k] for k in range(207)) == data and rd32(card + 8) == 1 and rd32(card + 4) == 1
r = packet(0x80); assert r[3] & 0x1F == 1
r = packet(0x33, b'\x32\x31\x36'); assert r[5] == 0x30, hex(r[5])
r = packet(0x33, b'\x30\x31\x36'); assert bytes(r[6:6 + 207]) == data
dbg = rd32(0x0DF00000 + 16)
print('OK en SH-4: %d instrucciones ejecutadas; paquetes=%d NAK=%d ENQ=%d seq=%d' %
      (steps, rd32(dbg + 12), rd32(dbg + 16), rd32(dbg + 20), rd32(card + 4)))
