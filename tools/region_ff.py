#!/usr/bin/env python3
"""En la Raspberry (WiPi): pone a 0xFF la máscara de regiones de la cabecera NAOMI (0x428) de una imagen .bin.gz,
sobrescribiéndola. Arregla el ERROR 02 ("THIS GAME IS NOT ACCEPTABLE BY MAIN BOARD") de imágenes que solo admiten
Japón (0x428 = 01), como Capcom vs SNK Pro (GDL-0004) o Guilty Gear XX #Reload (GDL-0019), en una placa con otra región.

    python3 region_ff.py /boot/roms/JUEGO.bin.gz

Bits de 0x428 (docs/naomi.md de DragonMinded/netboot): 0 Japón, 1 USA, 2 Export, 3 Corea, 4 Australia.
Haz antes una copia (p. ej. en /boot/roms_backup/): el script no guarda el original.
"""
import os, subprocess, sys
src = sys.argv[1]; tmp = src + '.tmp'
d = subprocess.Popen(['pigz', '-dc', src], stdout=subprocess.PIPE)
head = bytearray(d.stdout.read(0x500))
assert head[:5].upper() == b'NAOMI', 'no es NAOMI'
print('0x428 antes: %02x' % head[0x428])
head[0x428] = 0xFF
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
os.replace(tmp, src)
print('ok')
