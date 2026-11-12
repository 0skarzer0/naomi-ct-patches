#!/usr/bin/env python3
"""Añade el lector de tarjetas virtual a una ROM de NAOMI ya soportada.

Uso:
    python3 make_image.py ROM.bin[.gz] SALIDA.bin.gz [--card TARJETA.card]

- Añade al final de la imagen el bloque vcard.bin (compilado con build.sh) y una entrada en la tabla de carga de
  la cabecera para que la BIOS lo copie a la RAM libre (VC_BASE).
- Engancha la tarea periódica del driver serie del juego para que salte al lector virtual.
- Con --card, mete esa tarjeta (207 bytes, formato de YACardEmu) en la imagen. Si no, la tarjeta va vacía y la
  Raspberry la rellena al enviar el juego (vcard_pi.py send), o el juego compra una nueva.
"""
import gzip, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_RAM = 0x0C020000

# Juegos soportados: md5 del volcado -> dónde enganchar
GAMES = {
    'initial-d-export-reva': {
        'name': 'Initial D Arcade Stage (Export) Rev A, GDS-0025A',
        'size': 0xBFD0000,
        'romoff': 0x500,              # la ROM 0x500 se carga en 0x0C020000
        'hook': 0x0C13A9E0,           # tarea periódica del puerto serie: bombea recepción y envío
        'hook_orig': bytes.fromhex('862f1590e62f4368224f8c01'),
    },
}


def read_rom(path):
    data = open(path, 'rb').read()
    return bytearray(gzip.decompress(data) if data[:2] == b'\x1f\x8b' else data)


def find_game(rom):
    for key, g in GAMES.items():
        off = g['hook'] - BASE_RAM + g['romoff']
        if len(rom) == g['size'] and rom[off:off + len(g['hook_orig'])] == g['hook_orig']:
            return key, g
    return None, None


def main():
    args = sys.argv[1:]
    card = None
    if '--card' in args:
        i = args.index('--card')
        card = open(args[i + 1], 'rb').read()
        del args[i:i + 2]
        if len(card) != 207:
            sys.exit('la tarjeta debe tener 207 bytes (3 pistas de 69)')
    if len(args) != 2:
        sys.exit(__doc__)
    rom = read_rom(args[0])
    key, g = find_game(rom)
    if not g:
        sys.exit('ROM no reconocida (o ya parcheada). Juegos soportados: ' + ', '.join(GAMES))
    blob = bytearray(open(os.path.join(HERE, 'vcard.bin'), 'rb').read())
    magic, ver, poll, card_addr, debug_addr, base = struct.unpack_from('<6I', blob, 0)
    assert magic == 0x44524356, 'vcard.bin no válido: compila con build.sh'
    if card:
        co = card_addr - base
        struct.pack_into('<I', blob, co + 8, 1)          # flags: válida
        blob[co + 16:co + 16 + 207] = card

    # 1. el bloque al final de la imagen, alineado
    off = (len(rom) + 0xFFFF) & ~0xFFFF
    rom.extend(b'\0' * (off - len(rom)))
    rom.extend(blob)
    # 2. entrada en la tabla de carga del programa principal (0x360: hasta 8 x [offset, destino, tamaño])
    for i in range(8):
        o, d, s = struct.unpack_from('<3I', rom, 0x360 + 12 * i)
        if o == 0xFFFFFFFF:
            assert i < 7, 'la tabla de carga está llena'
            struct.pack_into('<3I', rom, 0x360 + 12 * i, off, base, len(blob))
            struct.pack_into('<3I', rom, 0x360 + 12 * (i + 1), 0xFFFFFFFF, 0, 0)
            break
    else:
        sys.exit('tabla de carga sin terminador')
    # 3. gancho: mov.l @(lit),r0 ; jmp @r0 ; nop ; nop ; .long vcard_poll   (r4 = puerto, como el original)
    h = g['hook'] - BASE_RAM + g['romoff']
    rom[h:h + 12] = struct.pack('<4HI', 0xD001, 0x402B, 0x0009, 0x0009, poll)
    with gzip.open(args[1], 'wb', compresslevel=9) as f:
        f.write(rom)
    print('OK: %s\n  bloque en ROM 0x%X -> RAM 0x%08X (%d bytes), vcard_poll 0x%08X, tarjeta 0x%08X%s\n  -> %s'
          % (g['name'], off, base, len(blob), poll, card_addr, ' (con tarjeta)' if card else '', args[1]))


if __name__ == '__main__':
    main()
