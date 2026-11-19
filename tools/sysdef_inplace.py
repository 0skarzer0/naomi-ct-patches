#!/usr/bin/env python3
"""En la Raspberry (WiPi): FREE PLAY + attract sound OFF en la cabecera de las imágenes NAOMI / NAOMI 2 /
Atomiswave de una carpeta, SOBRESCRIBIÉNDOLAS (no guarda originales, así que no hay que tocar romsinfo.csv).
Variante de sysdef_all.py con filtro por prefijo del nombre de fichero y modo de restauración.

    python3 sysdef_inplace.py /boot/roms                  # restaura dc-*/h-outrunners_dcport y parchea aw-/n1-/n2-
    python3 sysdef_inplace.py /boot/roms --patch-only
    python3 sysdef_inplace.py /boot/roms --restore-only

- PARCHEA solo los ficheros que empiezan por aw-, n1- o n2- (NAOMI, NAOMI 2 y Atomiswave convertido).
  NO toca las conversiones de Dreamcast (dc-*, dc2naomi) ni el homebrew (h-*): el usuario no las quiere parcheadas.
- RESTAURA (zona 0x1E0-0x25F a ceros) las dc-* y h-outrunners_dcport.bin.gz que estén parcheadas: así quedan
  las imágenes dc2naomi sin tocar, que tienen esa zona a ceros (comprobado con más de una docena de imágenes dc2naomi y
  homebrew sin parchear). Solo toca las que tienen exactamente el patrón del parche.
- Omite las que no tienen cabecera "NAOMI" (p. ej. n1-ninja_assault y n1-the_house_of_the_dead_2 en la
  Raspberry del mueble estándar) y las que ya están como toca (se puede relanzar sin repetir trabajo).
- Cada imagen se escribe en NOMBRE.tmp, se comprueba (pigz -t y cabecera) y solo entonces reemplaza al original.
  Si falla algo, queda el original. Si la Pi se reinicia a mitad, borrar los *.tmp y relanzar.
- Salida por pantalla: usar nohup ... > fichero; las imágenes grandes tardan varios minutos cada una.

OJO: Crazy Taxi y Jambo! Safari (y quizá otros de 1999-2000) se cuelgan si se cambia su cabecera; usar con
ellos los .binpatch de DragonMinded/netboot (tools/binpatch_gz.py).
"""
import os, subprocess, sys

Z0, Z1 = 0x1E0, 0x260   # 8 regiones x 16 bytes


def patched(h):
    return all(h[Z0 + 16 * r] == 1 and h[Z0 + 16 * r + 1] & 2 and h[Z0 + 16 * r + 3] == 27 for r in range(8))


def zeros(h):
    return h[Z0:Z1] == bytes(Z1 - Z0)


def mk_patch(h):
    h = bytearray(h)
    for r in range(8):
        o = Z0 + 16 * r
        h[o] = 1          # la BIOS aplica estos valores por defecto
        h[o + 1] |= 2     # sonido en attract apagado
        h[o + 3] = 27     # FREE PLAY
    return bytes(h)


def mk_zero(h):
    h = bytearray(h)
    h[Z0:Z1] = bytes(Z1 - Z0)
    return bytes(h)


def run(src, need, make, ok):
    d = subprocess.Popen(['pigz', '-dc', src], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    head = d.stdout.read(0x500)
    if head[:5].upper() != b'NAOMI':
        d.kill(); d.wait(); return 'omitida (sin cabecera NAOMI)'
    if ok(head):
        d.kill(); d.wait(); return 'ya'
    if not need(head):
        d.kill(); d.wait(); return 'omitida (cabecera inesperada)'
    tmp = src + '.tmp'
    with open(tmp, 'wb') as out:
        c = subprocess.Popen(['pigz', '-c', '-6', '-p', '4'], stdin=subprocess.PIPE, stdout=out)
        c.stdin.write(make(head))
        while True:
            b = d.stdout.read(1 << 20)
            if not b:
                break
            c.stdin.write(b)
        c.stdin.close(); c.wait(); d.wait()
    if d.returncode or c.returncode or subprocess.call(['pigz', '-t', tmp], stderr=subprocess.DEVNULL):
        os.remove(tmp); return 'ERROR (se deja el original)'
    k = subprocess.Popen(['pigz', '-dc', tmp], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    h2 = k.stdout.read(0x500); k.kill(); k.wait()
    if not ok(h2):
        os.remove(tmp); return 'ERROR de comprobacion'
    os.replace(tmp, src)
    return 'ok'


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    folder = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else ''
    names = sorted(f for f in os.listdir(folder) if f.endswith('.bin.gz'))
    restore = [f for f in names if f.startswith('dc-') or f == 'h-outrunners_dcport.bin.gz']
    patch = [f for f in names if f.startswith(('aw-', 'n1-', 'n2-'))]
    if mode != '--patch-only':
        print('RESTAURAR', len(restore), flush=True)
        for f in restore:
            try:
                r = run(os.path.join(folder, f), patched, mk_zero, zeros)
            except Exception as e:
                r = 'ERROR ' + repr(e)
            print('restaurar:', r, f, flush=True)
    if mode != '--restore-only':
        print('PARCHEAR', len(patch), flush=True)
        for f in patch:
            try:
                r = run(os.path.join(folder, f), lambda h: True, mk_patch, patched)
            except Exception as e:
                r = 'ERROR ' + repr(e)
            print('parchear:', r, f, flush=True)
    print('fin', flush=True)


if __name__ == '__main__':
    main()
