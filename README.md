# naomi-ct-patches — parches de controles para el mueble Crazy Taxi (NAOMI / NAOMI 2 / Atomiswave)

Muchos juegos de conducción de NAOMI esperan la palanca o los botones en pines distintos de los que
cablea un **mueble Crazy Taxi upright**. En vez de recablear, aquí se **parchea el código del juego**
para que funcione con los controles del mueble tal cual.

> **Política de ROMs:** este repositorio **no contiene ROMs** ni binarios que las incluyan. Solo hay
> parches (IPS), scripts y documentación. Cada usuario los aplica a su propio volcado.

Forma parte del proyecto [naomi-wheel-games](https://github.com/0skarzer0/naomi-wheel-games) (índice
general de juegos de volante para el mueble).

## Uso

```sh
python3 apply_patch.py TU_ROM.bin[.gz] juego/parche.ips SALIDA.bin.gz
```

El script comprueba que la zona que va a sustituir es la esperada (fichero `.ips.sha1` junto al
parche) y no modifica el original. El `.bin.gz` resultante se carga por netboot como cualquier otro
(en WiPi Netbooter: fichero + línea en `romsinfo.csv`).

## Controles del mueble Crazy Taxi (referencia)

| Control | Entrada JVS |
|---|---|
| Volante | Analógico 0 |
| Acelerador | Analógico 1 |
| Freno | Analógico 2 |
| Palanca adelante (DRIVE) | J1 ARRIBA |
| Palanca atrás (REVERSE) | J1 ABAJO |
| START | J1 START |
| Monedero, TEST, SERVICE | Sistema / monedas |

## Tabla por juego

| Juego | Placa | Entrada original | Reasignación en el mueble Crazy Taxi | Estado |
|---|---|---|---|---|
| [Jambo! Safari](jambo-safari/) (840-0013 Rev A) | NAOMI | Palanca en J2 ARRIBA/ABAJO | Palanca D/R (J1) → J2, en cruz: adelante = lazo | ✅ Probado en placa (variante cruzada, 2026-11-05) |
| [18 Wheeler Standard](18-wheeler/) (840-0036) | NAOMI | Palanca de 3 posiciones fija en J2, vista en J1 ABAJO, bocina en J1 B1 | Toques adelante/atrás = larga/corta (se quedan), atrás mantenido = marcha atrás, START corto = vista, START largo = bocina | 🧪 Probado en intérprete; falta placa (la BIOS multirregión cuelga este juego: hace falta la Export) |
| [Initial D Export Rev A](initial-d/) (GDS-0025A) | NAOMI 2 | Cambio secuencial en J2 ARRIBA/ABAJO, vista en J1 ABAJO | Palanca adelante/atrás = subir/bajar (directa), START corto = vista | 🧪 Probado en intérprete; falta placa |

Leyenda: ✅ probado en placa · 🧪 verificado en intérprete/emulador · 🔍 en análisis · ⏳ pendiente

## Juegos previstos

Según la [referencia de arneses](docs/referencia-arneses.md) (lo que otro usuario resolvió con cables):

| Juego | Qué necesita | Estado |
|---|---|---|
| Club Kart | Palanca a J2 directa, vista en combinación | ⏳ |
| Initial D Ver. 2 / Ver. 3 | Como la Ver. 1 (cada versión su parche) | ⏳ |
| Faster Than Speed | Turbo (J1 B1) en combinación | ⏳ |
| Maximum Speed | Nada (según el arnés): comprobar | ⏳ |
| King of Route 66 | Como 18 Wheeler + limpiaparabrisas; el micrófono necesita hardware | ⏳ |

## Lector de tarjetas virtual

[card-reader/](card-reader/): para los juegos que guardan en tarjeta magnética (Initial D…), se añade
a la imagen un lector **por software** que contesta al juego en lugar del lector real. La tarjeta se
guarda como archivo en la Raspberry, sin cable ni adaptador.

| Juego | Estado |
|---|---|
| Initial D Export Rev A (GDS-0025A) | 🧪 Arranca en placa y habla con el juego sin errores; falta comprobar compra y grabado (la BIOS multirregión cuelga el juego en el replay del attract, también sin parchear) |

## Procedimiento (repetible con otros juegos)

1. **Comparar mapeos**: `naomi_roms_input.h` de Flycast e `INPUT_PORTS` de `naomi.cpp` en MAME, frente a
   la tabla de controles del mueble de arriba.
2. **Encontrar la conversión JVS → variables del juego**: buscar cadenas de depuración o del test de
   entradas (`SW1:%x`, `LEVER UP`…), seguir sus referencias en los pools de literales y llegar a la
   función que copia los bytes JVS crudos a las estructuras por jugador.
3. **Parchear en un único punto** si es posible (la conversión), mejor que en cada lector. Si hace
   falta espacio, compactar la propia función en vez de usar zonas "libres" dudosas.
4. **Probar la equivalencia** con `tools/sh4mini.py`: función original + puente físico simulado frente a
   la función parcheada.
5. Probar en Flycast y en placa; anotar el resultado en la tabla.
6. Checksums: la cabecera NAOMI no lleva; comprobar en cada juego si hace autotest de ROM.

Atomiswave: las conversiones AW2NAOMI tienen otro mapa de memoria; el procedimiento es el mismo, pero
las direcciones de carga salen de la cabecera de cada conversión.

## Herramientas

| Fichero | Para qué |
|---|---|
| `apply_patch.py` | Aplica un IPS a un `.bin`/`.bin.gz` y comprueba la zona original (`.ips.sha1`) |
| `tools/sh4dis.py` | Desensamblador SH-4 con literales resueltos (`pip install "capstone>=6"`); base de carga `0x0C020000` |
| `tools/sh4mini.py` | Intérprete SH-4 mínimo para pruebas de equivalencia de funciones pequeñas |
| `tools/sh4asm.py` | Ensamblador SH-4 mínimo (etiquetas, huecos) para escribir los parches a mano |
| `tools/system_defaults.py` | Pone en la cabecera FREE PLAY y attract sound OFF por defecto (las 8 regiones) |
| `tools/sysdef_all.py` | Lo mismo en lote, en la Raspberry, para todas las imágenes de `/boot/roms` (guarda los originales) |
| `tools/sysdef_inplace.py` | Como `sysdef_all.py` pero sobrescribe las imágenes (sin originales) y **solo** en `aw-`/`n1-`/`n2-`; con modo de restauración de las `dc-*` parcheadas por error |
| `tools/sysdef_copy.py` | Copia de prueba con solo uno de los dos ajustes (attract mudo o free play), para aislar cuál cuelga un juego |
| `tools/binpatch_gz.py` | Aplica los `.binpatch` de DragonMinded/netboot (free play, attract mudo, noprotect) a una `.bin.gz` |
| `tools/region_ff.py` | Pone a `ff` la máscara de regiones (0x428) de una imagen solo para Japón: arregla el ERROR 02 |
| `tools/pi_ssh.py` | Comandos y copias en la Raspberry por SSH (contraseña solo por variable de entorno) |
| `card-reader/` | Lector de tarjetas virtual: código SH-4 en C, `make_image.py`, `vcard_pi.py` para la Pi |

Cada juego tiene en su carpeta un `build_patch.py` (genera los IPS desde ensamblador escrito a mano),
un `test_patch.py` y un `README.md` con las direcciones y notas técnicas.

## Créditos

- **[MAME](https://github.com/mamedev/mame)** y **[Flycast](https://github.com/flyinghead/flycast)**:
  mapas de entradas de cada juego y documentación de la NAOMI.
- **Autor del hilo
  [Crazy Taxi multi harness](https://www.arcade-projects.com/threads/crazy-taxi-multi-harness-w-button-panels.30132/)**
  (arcade-projects): los arneses por hardware que sirven de referencia para cada parche.
- **[Capstone](https://www.capstone-engine.org/)**: desensamblado SH-4.
- **[YACardEmu](https://github.com/GXTX/YACardEmu)** (GXTX): documentación del protocolo del lector
  de tarjetas (implementación propia, sin su código).
- **WiPi Netbooter** (Winteriscoming) y **[netboot](https://github.com/DragonMinded/netboot)**
  (DragonMinded): carga por red y peek/poke del NetDIMM, y sus parches `.binpatch` de free play, attract mudo y
  protección de cabecera (Crazy Taxi, Jambo! Safari…), que aplica `tools/binpatch_gz.py`.
- Hilos de arcade-otaku y arcade-projects sobre 18 Wheeler y la BIOS multirregión.
- **[pigz](https://zlib.net/pigz/)** (Mark Adler), que usan `sysdef_all.py` y `sysdef_inplace.py` para descomprimir y
  recomprimir las imágenes en la Raspberry, y **[paramiko](https://www.paramiko.org/)** (Jeff Forcier y colaboradores),
  con el que se accede por SSH a las Raspberry desde el PC.

## Aviso legal

No se distribuyen ROMs, BIOS ni binarios que las contengan. Las marcas pertenecen a sus propietarios
(Sega, Sammy…).
