#!/usr/bin/env python3
"""Ejecuta un comando en la Raspberry del WiPi Netbooter o le copia un fichero, por SSH (paramiko).

    PIPW=... [PIHOST=192.168.68.60] [PIUSER=root] python3 tools/pi_ssh.py 'comando'
    PIPW=... python3 tools/pi_ssh.py put FICHERO_LOCAL /ruta/en/la/pi

La contraseña va solo en la variable de entorno PIPW: nunca se escribe en ficheros ni en el repositorio.
Útil cuando la IA trabaja desde una shell en el PC del usuario (misma red que la Pi): `pip install paramiko`.
Ejemplos: enviar un juego con tarjeta virtual y leer el lector:
    python3 tools/pi_ssh.py 'cd /sbin/piforce && (nohup python3 vcard_pi.py send 10.0.0.4 /boot/roms/X.bin.gz > /tmp/s.out 2>&1 &)'
    python3 tools/pi_ssh.py 'python3 /sbin/piforce/vcard_pi.py debug 10.0.0.4'
Ojo: no uses `pkill -f patrón` si el patrón aparece en el propio comando (se mata a sí mismo).
"""
import os
import sys

import paramiko


def main():
    if len(sys.argv) < 2 or 'PIPW' not in os.environ:
        sys.exit(__doc__)
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(os.environ.get('PIHOST', '192.168.68.60'), username=os.environ.get('PIUSER', 'root'),
              password=os.environ['PIPW'], timeout=10)
    if sys.argv[1] == 'put':
        s = c.open_sftp()
        s.put(sys.argv[2], sys.argv[3])
        s.close()
        print('copiado')
    else:
        _, o, e = c.exec_command(sys.argv[1], timeout=int(os.environ.get('T', '100')))
        sys.stdout.write(o.read().decode(errors='replace'))
        sys.stderr.write(e.read().decode(errors='replace'))


if __name__ == '__main__':
    main()
