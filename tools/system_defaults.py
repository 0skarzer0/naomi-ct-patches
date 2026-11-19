#!/usr/bin/env python3
"""Ajustes de sistema por defecto de una imagen NAOMI: free play y sonido de attract apagado.

Uso:
    python3 tools/system_defaults.py ENTRADA.bin[.gz] SALIDA.bin[.gz] [--coins] [--sound]

La cabecera NAOMI tiene en 0x1E0-0x25F los valores por defecto del menú SYSTEM ASSIGNMENTS, 16 bytes por
región (Japón, EE. UU., Export, Corea, Australia y 3 más):
    +0  1 = la BIOS aplica estos valores al inicializar los ajustes del juego
    +1  bit 1 = sonido en attract APAGADO (bit 0: orientación del monitor, no se toca)
    +2  tipo de monedero
    +3  ajuste de monedas 1-28; 27 = FREE PLAY
    +4..+7 monedas/créditos
Por defecto pone en todas las regiones: aplicar = 1, attract silenciado y free play.
--coins: solo free play; --sound: solo attract silenciado.

La BIOS solo usa estos valores cuando inicializa los ajustes del juego (al cargar un juego distinto del
último que guardó en su EEPROM). Si se vuelve a cargar el mismo juego, se conservan los de antes.

OJO: Crazy Taxi y Jambo! Safari (y quizá otros de 1999-2000) se cuelgan si se cambia su cabecera; usar con
ellos los .binpatch de DragonMinded/netboot (tools/binpatch_gz.py).
"""
import gzip
import sys

FREE_PLAY = 27


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags = [a for a in sys.argv[1:] if a.startswith('--')]
    if len(args) != 2:
        sys.exit(__doc__)
    coins = '--sound' not in flags or '--coins' in flags
    sound = '--coins' not in flags or '--sound' in flags
    data = open(args[0], 'rb').read()
    gz = data[:2] == b'\x1f\x8b'
    rom = bytearray(gzip.decompress(data) if gz else data)
    if rom[:5].upper() != b'NAOMI':
        sys.exit('no es una imagen NAOMI')
    for r in range(8):
        o = 0x1E0 + 16 * r
        before = rom[o:o + 8].hex(' ')
        rom[o] = 1
        if sound:
            rom[o + 1] |= 0x02
        if coins:
            rom[o + 3] = FREE_PLAY
        print('región %d: %s -> %s' % (r, before, rom[o:o + 8].hex(' ')))
    if args[1].endswith('.gz'):
        with gzip.open(args[1], 'wb', 6) as f:
            f.write(rom)
    else:
        open(args[1], 'wb').write(rom)


if __name__ == '__main__':
    main()
