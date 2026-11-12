#!/usr/bin/env python3
"""Tarjeta virtual de un juego de NAOMI con lector, guardada en un archivo junto a su imagen (WiPi Netbooter).

  vcard_pi.py send IP JUEGO.bin.gz      envía la imagen (como netdimm_send, --disable-crc) con la tarjeta de
                                        JUEGO.card metida dentro, y deja un vigilante que trae lo que el juego guarde
  vcard_pi.py watch IP JUEGO.card       el vigilante (lo lanza send): cuando el juego escribe o expulsa la tarjeta,
                                        la lee por peek del NetDIMM y la guarda en el archivo
  vcard_pi.py stop IP                   antes de mandar otro juego: una última mirada y fin del vigilante
  vcard_pi.py debug IP                  contadores del lector virtual y los últimos bytes intercambiados
  vcard_pi.py inject IMAGEN.bin.gz TARJETA.card SALIDA.bin.gz   mete una tarjeta en una imagen sin la Pi

La tarjeta es un archivo de 207 bytes (3 pistas de 69 bytes, el formato de YACardEmu). Si no existe, el juego
arranca sin tarjeta y ofrece una nueva; al expulsarla, el vigilante la guarda y la próxima vez se usa esa.
Registro: /var/log/vcard.log
"""
import gzip
import io
import os
import signal
import struct
import subprocess
import sys
import time

sys.path.append('/sbin/piforce/dm_netboot')

VC_MAGIC = 0x44524356        # 'VCRD'
VC_CARD_MAGIC = 0x44524143   # 'CARD'
CARD_SIZE = 207
RAM_BASE = 0x0C000000        # el NetDIMM recibe la dirección como offset en la RAM del NAOMI
POLL = 3
SLOW = 2.0
LOG = '/var/log/vcard.log'


def log(*a):
    line = time.strftime('%Y-%m-%d %H:%M:%S ') + ' '.join(str(x) for x in a)
    try:
        with open(LOG, 'a') as f:
            f.write(line + '\n')
    except OSError:
        print(line)


def find_block(raw):
    """(offset en la imagen del bloque vcard, cabecera) o (0, None)."""
    if raw[:5].upper() != b'NAOMI' or len(raw) < 0x400:
        return 0, None
    for i in range(8):
        o, d, s = struct.unpack_from('<3I', raw, 0x360 + 12 * i)
        if o == 0xFFFFFFFF:
            break
        if o + 32 <= len(raw) and struct.unpack_from('<I', raw, o)[0] == VC_MAGIC:
            return o, struct.unpack_from('<6I', raw, o)
    return 0, None


def load_card(path):
    try:
        with open(path, 'rb') as f:
            card = f.read()
    except OSError:
        return None
    return card if len(card) == CARD_SIZE else None


def save_card(path, card):
    tmp = path + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(card)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def inject(raw, card):
    """Mete la tarjeta en la imagen (bytearray). Devuelve la dirección de RAM de vc_card, o 0."""
    off, hdr = find_block(raw)
    if not off:
        return 0
    _, _, _, card_addr, _, base = hdr
    co = off + card_addr - base
    if card is not None:
        struct.pack_into('<I', raw, co + 8, 1)
        raw[co + 16:co + 16 + CARD_SIZE] = card
    return card_addr


class Gone(Exception):
    pass


class Board:
    def __init__(self, ip):
        from netdimm import NetDimm, PeekPokeTypeEnum
        self.d = NetDimm(ip)
        self.long = PeekPokeTypeEnum.TYPE_LONG

    def peek(self, addr):
        t = time.time()
        try:
            v = self.d.peek(addr - RAM_BASE, self.long)
        except Exception as e:
            raise Gone(str(e))
        if time.time() - t > SLOW:
            raise Gone('respuesta lenta')
        return v

    def read(self, addr, n):
        words = [self.peek(addr + 4 * i) for i in range((n + 3) // 4)]
        return struct.pack('<%dI' % len(words), *words)[:n]


def card_state(board, card_addr):
    magic, seq, flags, inserts = struct.unpack('<4I', board.read(card_addr, 16))
    if magic != VC_CARD_MAGIC:
        raise Gone('no está el lector virtual (otro juego, la BIOS o la máquina apagada)')
    return seq, flags, inserts


def pull(board, card_addr, path):
    data = board.read(card_addr + 16, CARD_SIZE)
    seq, flags, _ = card_state(board, card_addr)      # sigue siendo el mismo juego después de los peeks
    if flags & 1:
        save_card(path, data)
        log('guardada', path, 'seq', seq)
    return seq


def state_file(ip):
    return '/var/log/vcard_%s.state' % ip


def write_state(ip, path, card_addr, seq):
    with open(state_file(ip), 'w') as f:
        f.write('%d\n%d\n%s\n%d\n' % (os.getpid(), seq, path, card_addr))


def watch(ip, path, card_addr, wait=30):
    write_state(ip, path, card_addr, 0)
    log('vigilando', ip, path, hex(card_addr))
    time.sleep(wait)
    board = Board(ip)
    synced, misses = 0, 0
    while True:
        try:
            seq, flags, _ = card_state(board, card_addr)
            if seq != synced:
                synced = pull(board, card_addr, path)
                write_state(ip, path, card_addr, synced)
            misses = 0
        except Gone as e:
            misses += 1
            log('sin respuesta (%d): %s' % (misses, e))
            if misses >= 6:
                log('me rindo')
                break
        time.sleep(POLL)
    try:
        os.remove(state_file(ip))
    except OSError:
        pass


def stop(ip):
    try:
        with open(state_file(ip)) as f:
            pid, seq, path, card_addr = f.read().split('\n')[:4]
    except (OSError, ValueError):
        return
    try:
        os.kill(int(pid), signal.SIGKILL)
    except (OSError, ValueError):
        pass
    try:
        os.remove(state_file(ip))
    except OSError:
        pass
    try:
        board = Board(ip)
        if card_state(board, int(card_addr))[0] != int(seq):
            pull(board, int(card_addr), path)
            log('última mirada antes del siguiente juego: guardada')
    except Exception as e:
        log('última mirada:', e)


def send(ip, image):
    from arcadeutils import FileBytes
    from netdimm import NetDimm, NetDimmVersionEnum
    stop(ip)
    raw = bytearray(subprocess.run(['pigz', '-cd', '-p', '8', image], stdout=subprocess.PIPE, check=True).stdout)
    path = (image[:-len('.bin.gz')] if image.endswith('.bin.gz') else image) + '.card'
    card = load_card(path)
    if card is None and os.path.exists(path):
        os.replace(path, path + '.bad')
        log(path, 'no tiene 207 bytes: renombrada a .bad')
    card_addr = inject(raw, card)
    if card_addr:
        log('enviando', image, 'con', path if card else '(sin tarjeta)')
    with io.BytesIO(bytes(raw)) as fp:
        netdimm = NetDimm(ip, version=NetDimmVersionEnum.VERSION_4_01, log=print)
        netdimm.send(FileBytes(fp), None, disable_crc_check=True)
        netdimm.reboot()
    if card_addr:
        subprocess.Popen([sys.executable, os.path.abspath(__file__), 'watch', ip, path, hex(card_addr)],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)


def debug(ip):
    board = Board(ip)
    for base in (0x0DF00000,):
        if board.peek(base) != VC_MAGIC:
            print('no hay lector virtual en', hex(base))
            continue
        _, ver, poll, card_addr, dbg, _ = struct.unpack('<6I', board.read(base, 24))
        seq, flags, inserts = card_state(board, card_addr)
        print('versión %d  vcard_poll %08x  tarjeta %08x seq %d flags %d metida %d veces' %
              (ver, poll, card_addr, seq, flags, inserts))
        names = ['llamadas', 'bytes del juego', 'bytes al juego', 'paquetes', 'NAK', 'ENQ', 'último cmd',
                 'último estado']
        vals = struct.unpack('<8I', board.read(dbg, 32))
        for n, v in zip(names, vals):
            print('  %-16s %08x (%d)' % (n, v, v))
        cnt = struct.unpack('<16I', board.read(dbg + 32, 64))
        print('  comandos por grupo (cmd>>4):', ' '.join('%X:%d' % (i, c) for i, c in enumerate(cnt) if c))
        pos = board.peek(dbg + 96)
        log_bytes = board.read(dbg + 100, 1024)
        pos &= 1022                                   # circular: lo más antiguo empieza en pos
        ordered = log_bytes[pos:] + log_bytes[:pos]
        pairs = [ordered[i:i + 2] for i in range(0, 1024, 2)][-64:]
        print('  últimos bytes (> juego->lector, < lector->juego):')
        print('   ', ' '.join(('<' if p[0] else '>') + '%02x' % p[1] for p in pairs))


def main():
    a = sys.argv[1:]
    if len(a) == 3 and a[0] == 'send':
        send(a[1], a[2])
    elif len(a) in (4, 5) and a[0] == 'watch':
        try:
            watch(a[1], a[2], int(a[3], 16), float(a[4]) if len(a) == 5 else 30)
        except Exception as e:
            log('el vigilante murió:', repr(e))
            raise
    elif len(a) == 2 and a[0] == 'stop':
        stop(a[1])
    elif len(a) == 2 and a[0] == 'debug':
        debug(a[1])
    elif len(a) == 4 and a[0] == 'inject':
        data = open(a[1], 'rb').read()
        raw = bytearray(gzip.decompress(data) if data[:2] == b'\x1f\x8b' else data)
        card = load_card(a[2])
        if card is None:
            sys.exit('la tarjeta debe tener 207 bytes')
        if not inject(raw, card):
            sys.exit('la imagen no tiene el lector virtual (make_image.py)')
        with gzip.open(a[3], 'wb', 6) as f:
            f.write(raw)
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
