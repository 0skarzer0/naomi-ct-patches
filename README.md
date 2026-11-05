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

Leyenda: ✅ probado en placa · 🧪 verificado en intérprete/emulador · 🔍 en análisis · ⏳ pendiente

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

Cada juego tiene en su carpeta un `build_patch.py` (genera los IPS desde ensamblador escrito a mano),
un `test_patch.py` y un `README.md` con las direcciones y notas técnicas.

## Aviso legal

No se distribuyen ROMs, BIOS ni binarios que las contengan. Las marcas pertenecen a sus propietarios
(Sega, Sammy…).
