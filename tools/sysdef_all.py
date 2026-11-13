#!/usr/bin/env python3
"""En la Raspberry (WiPi): pone FREE PLAY y attract sound OFF en la cabecera de todas las imágenes .bin.gz de
una carpeta, sin pasar las imágenes por la red. Lo mismo que system_defaults.py, pero en lote y en streaming
(pigz), y guardando los originales.

    python3 sysdef_all.py /boot/roms /boot/roms_orig            # todas
    python3 sysdef_all.py /boot/roms /boot/roms_orig A.bin.gz   # solo esas

- Omite las que no empiezan por "NAOMI" y las que ya están (aplicar = 1, attract mudo y free play en las 8
  regiones de 0x1E0).
- Comprueba cada resultado (pigz -t y cabecera) antes de cambiarlo; el original va a ORIG.
- Registro: /var/log/system_defaults.log
"""
import os, subprocess, sys, time
LOG = '/var/log/system_defaults.log'


def log(*a):
    with open(LOG, 'a') as f:
        f.write(time.strftime('%F %T ') + ' '.join(map(str, a)) + '\n')


def patch_header(h):
    h = bytearray(h)
    for r in range(8):
        o = 0x1E0 + 16 * r
        h[o] = 1          # la BIOS aplica estos valores por defecto
        h[o + 1] |= 2     # sonido en attract apagado
        h[o + 3] = 27     # FREE PLAY
    return bytes(h)


def done(h):
    return all(h[0x1E0 + 16 * r] == 1 and h[0x1E1 + 16 * r] & 2 and h[0x1E3 + 16 * r] == 27 for r in range(8))


def one(src, origdir):
    d = subprocess.Popen(['pigz', '-dc', src], stdout=subprocess.PIPE)
    head = d.stdout.read(0x500)
    if head[:5].upper() != b'NAOMI':
        d.kill(); log('omitida (no es NAOMI):', src); return
    if done(head):
        d.kill(); log('ya estaba:', src); return
    tmp = src + '.tmp'
    with open(tmp, 'wb') as out:
        c = subprocess.Popen(['pigz', '-c', '-6', '-p', '4'], stdin=subprocess.PIPE, stdout=out)
        c.stdin.write(patch_header(head))
        while True:
            b = d.stdout.read(1 << 20)
            if not b:
                break
            c.stdin.write(b)
        c.stdin.close(); c.wait(); d.wait()
    if d.returncode or c.returncode or subprocess.call(['pigz', '-t', tmp]):
        os.remove(tmp); log('ERROR, se deja el original:', src); return
    chk = subprocess.Popen(['pigz', '-dc', tmp], stdout=subprocess.PIPE)
    h2 = chk.stdout.read(0x500); chk.kill()
    if not done(h2):
        os.remove(tmp); log('ERROR de comprobación:', src); return
    os.makedirs(origdir, exist_ok=True)
    os.replace(src, os.path.join(origdir, os.path.basename(src)))
    os.replace(tmp, src)
    log('ok:', src)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    folder, origdir = sys.argv[1], sys.argv[2]
    files = sys.argv[3:] or sorted(os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.bin.gz'))
    log('inicio', len(files), 'imágenes')
    for f in files:
        try:
            one(f, origdir)
        except Exception as e:
            log('ERROR', f, repr(e))
    log('fin')


if __name__ == '__main__':
    main()
