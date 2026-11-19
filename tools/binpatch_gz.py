#!/usr/bin/env python3
"""En la Raspberry: aplica parches .binpatch de DragonMinded/netboot (líneas 'OFFSET: bytes viejos -> bytes nuevos')
a una imagen .bin.gz, en streaming y comprobando antes los bytes viejos. No modifica el original.

    python3 binpatch_gz.py ORIGEN.bin.gz DESTINO.bin.gz PARCHE.binpatch [PARCHE2.binpatch ...]

Los parches están en el WiPi en /sbin/piforce/dm_netboot/patches/ (CrazyTaxi_freeplay, *_no_attract, *_noprotect…)
y no se redistribuyen aquí: son de DragonMinded/netboot.
"""
import os, subprocess, sys
if len(sys.argv) < 4:
    sys.exit(__doc__)
src, dst, patches = sys.argv[1], sys.argv[2], sys.argv[3:]
edits = []
for p in patches:
    for line in open(p):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        off, rest = line.split(':', 1)
        old, new = rest.split('->')
        edits.append((int(off, 16), bytes.fromhex(old), bytes.fromhex(new), os.path.basename(p)))
end = max(o + len(n) for o, _, n, _ in edits)
d = subprocess.Popen(['pigz', '-dc', src], stdout=subprocess.PIPE)
head = bytearray()
while len(head) < end:
    b = d.stdout.read(end - len(head))
    if not b:
        sys.exit('imagen demasiado corta')
    head += b
for o, old, new, name in edits:
    cur = bytes(head[o:o + len(old)])
    if cur == new:
        print('ya aplicado %s @%X' % (name, o)); continue
    if cur != old:
        d.kill(); sys.exit('NO coincide %s @%X: %s' % (name, o, cur.hex()))
    head[o:o + len(new)] = new
    print('ok %s @%X' % (name, o))
tmp = dst + '.tmp'
with open(tmp, 'wb') as out:
    c = subprocess.Popen(['pigz', '-c', '-6', '-p', '4'], stdin=subprocess.PIPE, stdout=out)
    c.stdin.write(bytes(head))
    while True:
        b = d.stdout.read(1 << 20)
        if not b:
            break
        c.stdin.write(b)
    c.stdin.close(); c.wait(); d.wait()
assert d.returncode == 0 and c.returncode == 0 and subprocess.call(['pigz', '-t', tmp]) == 0
os.replace(tmp, dst)
print('escrito', dst)
