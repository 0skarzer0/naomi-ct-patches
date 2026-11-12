# Lector de tarjetas virtual (sin cable ni lector)

Algunos juegos de NAOMI guardan la partida en una **tarjeta magnética** que lee un lector Sanwa
CRP-1231BR-10 conectado al puerto serie de la placa (CN8). Este módulo lo **sustituye por software**:
se añade a la imagen del juego un pequeño bloque de código SH-4 que contesta al juego como si fuera el
lector, y la tarjeta queda guardada como **archivo en la Raspberry** (como la `.vmu` de
[dc2naomi](https://github.com/0skarzer0/dc2naomi)). No hace falta adaptador USB-serie, ni cable, ni
lector.

> No contiene ROMs. `make_image.py` modifica **tu** volcado.

## Juegos

| Juego | Volcado | Estado |
|---|---|---|
| Initial D Arcade Stage Export Rev A (GDS-0025A) | MD5 `eb7d81c2a0792267d0733beea5956066` (sin parchear) | 🧪 Probado en el PC y en el intérprete SH-4; falta probar en placa |

Para la tarjeta, en el menú de test el ajuste **CARD R/W** tiene que estar en **ON** (el valor de
fábrica). La imagen se hace desde el volcado original, no desde el que arranca con el lector apagado.

## Cómo funciona

```
juego ── putc/getc ──> buffers del driver serie de Sega ──X── SCIF (CN8) ── lector real
                                │
                    tarea periódica 0x0C13A9E0 (enganchada)
                                │
                                v
                  vcard_poll(): lee lo que el juego "envía", contesta como el lector
                                │
                    vc_card (RAM 0x0DF00D00) <── peek ── Raspberry: JUEGO.card
```

1. **Bloque en RAM libre.** `make_image.py` añade `vcard.bin` al final de la imagen y una entrada en la
   tabla de carga de la cabecera NAOMI (`0x360`), así que la BIOS lo copia a `0x0DF00000`. Según el crt0
   del juego, la memoria que usa termina en `0x0D000000` (falta confirmarlo en placa).
2. **Gancho.** El juego usa la librería de Sega del puerto serie, con buffers circulares de 1 KB. La
   tarea periódica `0x0C13A9E0(port)` es la que mueve bytes entre esos buffers y el SCIF. Se
   sustituyen sus primeras instrucciones por un salto a `vcard_poll(port)`, que vacía el buffer de envío
   (lo que el juego manda al lector) y llena el de recepción (lo que el lector contesta). El SCIF ya no
   se usa, y el resto del juego (capa de tarjeta, tiempos de espera, menús) no cambia.
3. **Protocolo** (implementación propia; protocolo documentado por YACardEmu):
   - El juego envía `STX LEN CMD 0 0 0 parámetros ETX BCC`. El lector contesta `ACK` (o `NAK` si está mal).
   - El juego envía `ENQ`. El lector contesta `STX LEN CMD R P S datos ETX BCC`.
   - R es la posición de la tarjeta, P el resultado y S el estado.
   - Comandos soportados:

     | Código | Comando |
     |---|---|
     | 10 | Inicializar |
     | 20 | Estado |
     | 33 | Leer |
     | 40 | Cancelar |
     | 53 | Escribir |
     | 7C | Imprimir |
     | 80 | Expulsar |
     | A0 | Limpiar |
     | B0 | Dispensar tarjeta nueva |
     | D0 | Persiana |
     | 78, 7A, C0, C1, E1, F5 | Se aceptan |

4. **La tarjeta.**
   - Ocupa 207 bytes: 3 pistas de 69, en el formato `.card` de YACardEmu, así que sirven tarjetas de
     ese emulador.
   - Si hay tarjeta válida, se mete sola cuando el juego la pide.
   - Al escribirla o expulsarla sube el contador `seq`.
   - La Raspberry lo vigila por *peek* del NetDIMM y guarda el archivo.

## Estructura en RAM (offset para peek = dirección − 0x0C000000)

| Dirección | Contenido |
|---|---|
| `0x0DF00000` | Cabecera: `VCRD`, versión, dirección de `vcard_poll`, de la tarjeta, del registro y base |
| `0x0DF00D00` | `vc_card_t`: `CARD`, `seq`, `flags` (bit 0 = válida), veces metida, 207 bytes de pistas |
| `0x0DF00E00` | `vc_debug_t` (ver la tabla siguiente) |

Contenido de `vc_debug_t`:
- llamadas, bytes en un sentido y en otro, paquetes, NAK, ENQ;
- último comando y último estado;
- comandos por grupo;
- registro circular de 512 bytes intercambiados, en pares (dirección, byte), donde 0 = juego→lector.

Las direcciones exactas salen en `vcard.sym` después de compilar.

## Uso

### 1. Crear la imagen (en el PC)

```sh
./build.sh          # opcional: vcard.bin ya va compilado en el repo
python3 make_image.py "n2-initial_d_export_rev.a-[GDS-0025A].bin.gz" initiald_exp_reva_vcard.bin.gz
# con una tarjeta ya hecha dentro:
python3 make_image.py ROM.bin.gz SALIDA.bin.gz --card mi_tarjeta.card
```

### 2. En la Raspberry (WiPi Netbooter)

Copiar `vcard_pi.py` a `/sbin/piforce/`. Usa la librería netdimm de DragonMinded que ya trae el WiPi.

```sh
vcard_pi.py send 10.0.0.4 /boot/roms/initiald_exp_reva_vcard.bin.gz
#   mete initiald_exp_reva_vcard.card (si existe) y deja vigilando el guardado
vcard_pi.py debug 10.0.0.4      # contadores y últimos bytes, para ver qué pide el juego
vcard_pi.py stop 10.0.0.4       # antes de cargar otro juego (última mirada)
vcard_pi.py inject IMAGEN.bin.gz TARJETA.card SALIDA.bin.gz   # sin Pi
```

Sin integrarlo en `wipiloader.py` (como se hizo con dc2naomi), la imagen funciona igual si se carga
desde la web del WiPi:
- el juego arranca sin tarjeta, o con la que se haya metido con `--card` o `inject`;
- ofrece comprar una nueva, y se puede jugar y guardar durante la sesión;
- pero la tarjeta no se copia a la Pi: se pierde al apagar.

Para conservarla, hay que enviar con `vcard_pi.py send`.

## Pruebas

| Prueba | Qué hace |
|---|---|
| `build.sh` → `test_host` | El código C compilado para el PC, con un juego simulado: inicializar, dispensar, escribir, expulsar, meter, leer. Comprueba ACK, BCC y estados |
| `test_sh4.py IMAGEN.bin.gz` | Carga la imagen como la BIOS en `tools/sh4mini.py` y llama al gancho del juego (`0x0C13A9E0`) con el mismo escenario: ejecuta el binario SH-4 real que va a la placa |

Pendiente en placa:
- confirmar que `0x0DF00000` está libre;
- que el juego compra, graba y lee la tarjeta;
- que `vcard_pi.py debug` responde.

Si algo falla, el registro de `debug` dice qué comando se quedó sin la respuesta esperada.

## Ficheros

| Fichero | Para qué |
|---|---|
| `vcard.h`, `vcard.c`, `entry.c`, `vcard.ld` | El lector virtual (C, compilado con `sh-elf-gcc`) |
| `build.sh` | Compila `vcard.bin` y la prueba en PC. Dependencias Ubuntu: `gcc-sh-elf binutils-sh-elf libnewlib-sh-elf-dev` |
| `vcard.bin`, `vcard.sym` | Binario compilado y sus símbolos (código propio, no contiene nada del juego) |
| `make_image.py` | Añade el lector a un volcado soportado (tabla `GAMES`: tamaño, gancho y bytes originales) |
| `vcard_pi.py` | Raspberry: enviar con tarjeta, vigilar, depurar |
| `test_host.c`, `test_sh4.py` | Pruebas |

## Añadir otro juego

Initial D Ver. 2 y Ver. 3 y otros juegos de Sega con lector usan la misma librería serie (buscar la
tarea periódica que comprueba los bytes de cerrojo `port+0x82C` / `port+0x82D` y llama a las bombas de
recepción y envío). Si el formato de los buffers coincide, basta con añadir una entrada en `GAMES` de
`make_image.py`. Si no, hay que adaptar `vcard_poll`. Comprobar también:
- la tabla de comandos del juego (Initial D Ver. 1: `0x0C1EAB38`);
- que haya RAM libre para el bloque.

## Créditos

- **[YACardEmu](https://github.com/GXTX/YACardEmu)** (GXTX y colaboradores): documentación del
  protocolo del CRP-1231BR-10 y del formato `.card`. No se ha copiado su código (es GPL-2); aquí hay una
  implementación propia.
- **WiPi Netbooter** (Winteriscoming y colaboradores): el sistema de carga por red en la Raspberry.
- **[netdimm / netboot](https://github.com/DragonMinded/netboot)** (DragonMinded): envío y peek/poke
  del NetDIMM.
- **[dc2naomi](https://github.com/0skarzer0/dc2naomi)**: la idea de guardar la memoria del juego como
  archivo en la Pi y vigilarla por peek.
- **MAME** y **Flycast**: documentación de la placa NAOMI y del formato de cabecera.
