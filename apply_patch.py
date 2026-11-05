#!/usr/bin/env python3
"""Aplica un parche IPS de este repositorio a TU volcado de ROM y genera el .bin (o .bin.gz) para netboot.

Uso:
    python3 apply_patch.py ROM_ORIGINAL PARCHE.ips SALIDA[.bin|.bin.gz]

- ROM_ORIGINAL puede ser .bin o .bin.gz.
- Antes de parchear comprueba que los bytes que se van a sustituir son los esperados
  (fichero PARCHE.ips.sha1 al lado del parche), para no estropear un volcado de otra revisión.
- No modifica el original.
"""
import gzip, hashlib, os, struct, sys

def read_rom(path):
    with open(path, 'rb') as f:
        data = f.read()
    return gzip.decompress(data) if data[:2] == b'\x1f\x8b' else data

def parse_ips(blob):
    assert blob[:5] == b'PATCH', 'no es un fichero IPS'
    i, recs = 5, []
    while blob[i:i+3] != b'EOF':
        off = int.from_bytes(blob[i:i+3], 'big'); size = struct.unpack('>H', blob[i+3:i+5])[0]; i += 5
        if size == 0:  # registro RLE
            n = struct.unpack('>H', blob[i:i+2])[0]; recs.append((off, blob[i+2:i+3] * n)); i += 3
        else:
            recs.append((off, blob[i:i+size])); i += size
    return recs

def main():
    if len(sys.argv) != 4:
        print(__doc__); sys.exit(1)
    src, ips_path, out = sys.argv[1:]
    rom = bytearray(read_rom(src))
    recs = parse_ips(open(ips_path, 'rb').read())
    check = ips_path + '.sha1'
    if os.path.exists(check):
        want = open(check).read().split()[0]
        got = hashlib.sha1(b''.join(bytes(rom[o:o+len(d)]) for o, d in recs)).hexdigest()
        if got != want:
            sys.exit(f'ERROR: tu ROM no coincide con la esperada (sha1 de la zona {got} != {want}).\n'
                     'Puede ser otra revisión del juego o un volcado ya parcheado.')
    for off, data in recs:
        rom[off:off+len(data)] = data
    if out.endswith('.gz'):
        with gzip.open(out, 'wb', compresslevel=9) as f:
            f.write(rom)
    else:
        open(out, 'wb').write(rom)
    print(f'OK: {len(recs)} bloque(s) aplicados -> {out} (md5 {hashlib.md5(rom).hexdigest()})')

if __name__ == '__main__':
    main()
