# Jambo! Safari (NAOMI, 840-0013, Rev A): palanca del Crazy Taxi sin tocar cableado

## El problema

| Juego | Dónde lee la palanca | Bit "arriba" | Bit "abajo" |
|---|---|---|---|
| **Crazy Taxi** | Jugador 1, ARRIBA / ABAJO | ARRIBA = DRIVE | ABAJO = REVERSE |
| **Jambo! Safari** | Jugador 2, ARRIBA / ABAJO | ABAJO = *LEVER UP* (lanzar el lazo) | ARRIBA = *LEVER DOWN* |

Fuentes: definiciones de entrada de MAME (`naomi.cpp`) y Flycast (`naomi_roms_input.h`), y los textos
del propio juego (*"Turn the lever up to throw the..."*). En la máquina física se arregla con dos
puentes **en cruz** desde los cables de la palanca hasta las entradas del jugador 2.

## Qué hace el parche

Cada frame, la función `0x0C0217CC` llama a `0x0C021334` (copia la respuesta JVS al búfer crudo) y
convierte esos bytes en una estructura de 8 bytes por jugador:

| Dirección | Contenido |
|---|---|
| `0x0C2892F4` | byte de sistema JVS (bit 7 = TEST) |
| `0x0C2892F5 + 16·i` | bytes crudos del jugador *i* (byte0 = START SERV UP DOWN LEFT RIGHT B1 B2) |
| `0x0C289738` | número de jugadores que informa la I/O |
| `0x0C2AB3B0 + 8·i` | `u16` actual, anterior, pulsado, soltado (palabra = byte1<<8 \| byte0) |
| `0x0C289536` → `0x0C2AB3D0` | 8 canales analógicos (byte alto actual y anterior, paso 4) |

El parche **reescribe esa función en su mismo espacio** (104 bytes, offset de ROM `0x0017CC`):

- Bucles compactados: contador con `dt`, "soltado = pulsado XOR cambiado".
- Con el espacio ganado, lee ARRIBA/ABAJO del J1 y los **suma (OR)** al byte0 del J2 y siguientes.
- El J1 y los analógicos quedan exactamente igual. Las entradas reales del J2 se siguen leyendo, así que
  el parche no estropea un mueble Jambo original.

Variantes:

| Fichero | Palanca del Crazy Taxi | Resultado en Jambo |
|---|---|---|
| `jambo_ct_cruzado.ips` (**recomendado**) | adelante (DRIVE) | *lever up* = **lanzar el lazo** |
| | atrás (REVERSE) | *lever down* |
| `jambo_ct_directo.ips` | adelante | *lever down* |
| | atrás | *lever up* = lazo |

## Cómo aplicarlo

```sh
python3 ../apply_patch.py TU_jambo_safari.bin.gz jambo_ct_cruzado.ips jambo_safari_ct.bin.gz
```

El script comprueba antes la zona que va a sustituir (`.ips.sha1`). Volcado probado:
`n1-jambo_safari-840-0013.bin`, 75 497 472 bytes, MD5 `4efd869b0d688a80a8ab8c51f4897d24`.
En WiPi se añade como un juego más (fichero `.bin.gz` + línea en `romsinfo.csv`).

## Verificación hecha

- `test_patch.py` ejecuta en un intérprete SH-4 mínimo (`../tools/sh4mini.py`) la función original y la
  parcheada durante 3000 frames aleatorios (0–3 jugadores). El parche da **byte a byte** lo mismo que el
  original con el puente físico simulado, en las dos variantes.
- A la función solo se entra por su inicio (desde `0x0C021C42` y `0x0C021C8E`). El aparente salto desde
  `0x0C021BAC` es un pool de literales.
- La cabecera NAOMI no lleva checksum. El juego no comprueba esta zona: **pendiente de confirmar en placa**.

## Estado

| Paso | Estado |
|---|---|
| Localizar lectura JVS y bits | ✅ |
| Parche (dos variantes) + script | ✅ |
| Prueba de equivalencia en intérprete | ✅ |
| Prueba en Flycast | ⏳ (necesita BIOS NAOMI) |
| Prueba en placa (mueble Crazy Taxi) | ⏳ |

## Para regenerar o modificar

```sh
python3 build_patch.py                                     # reescribe los .ips
python3 test_patch.py TU_jambo.bin ../tools build_patch.py # prueba de equivalencia
python3 ../tools/sh4dis.py TU_jambo.bin 0c0217cc 68        # desensamblar (capstone >= 6)
```
