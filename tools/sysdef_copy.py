#!/usr/bin/env python3
"""En la Raspberry: copia una imagen NAOMI .bin.gz cambiando SOLO uno de los dos ajustes del parche de free play
(las 8 regiones de 0x1E0), para averiguar cuál de los dos le sienta mal a un juego. El original no se toca.

    python3 sysdef_copy.py ORIGEN.bin.gz DESTINO.bin.gz --sound   # solo attract mudo (bit 1 de +1)
    python3 sysdef_copy.py ORIGEN.bin.gz DESTINO.bin.gz --coins   # solo FREE PLAY (+3 = 27)

La copia lleva el mismo número de serie que el original: la BIOS no vuelve a aplicar los ajustes si se cargan seguidas.
Entre una prueba y otra hay que cargar un juego distinto. Para el menú, añadir su fila con
naomi-pi-tools/pi/add_romsinfo_rows.py e importar con /sbin/piforce/importcsv.py ORIGEN DESTINO.
"""
import os, subprocess, sys
src, dst, mode = sys.argv[1:4]
tmp = dst + '.tmp'
d = subprocess.Popen(['pigz', '-dc', src], stdout=subprocess.PIPE)
h = bytearray(d.stdout.read(0x500))
orig = bytes(h)
assert h[:5].upper() == b'NAOMI'
for r in range(8):
    o = 0x1E0 + 16 * r
    if mode == '--sound':
        h[o + 1] |= 2
    elif mode == '--coins':
        h[o + 3] = 27
    else:
        sys.exit(__doc__)
with open(tmp, 'wb') as out:
    c = subprocess.Popen(['pigz', '-c', '-6', '-p', '4'], stdin=subprocess.PIPE, stdout=out)
    c.stdin.write(bytes(h))
    while True:
        b = d.stdout.read(1 << 20)
        if not b:
            break
        c.stdin.write(b)
    c.stdin.close(); c.wait(); d.wait()
assert d.returncode == 0 and c.returncode == 0 and subprocess.call(['pigz', '-t', tmp]) == 0
os.replace(tmp, dst)
print('ok', dst, 'bytes cambiados:', sum(a != b for a, b in zip(orig, h)))
