# 18 Wheeler Standard (NAOMI, 840-0036): marchas, vista y bocina con los controles del Crazy Taxi

## El problema

| Función en 18 Wheeler | Entrada que espera | Qué le llega desde el mueble Crazy Taxi |
|---|---|---|
| Marcha larga (H) | J2 ARRIBA | nada |
| Marcha corta (L) | J2 ABAJO | nada |
| Marcha atrás (R) | J2 IZQUIERDA (el arnés de referencia añade J2 ABAJO) | nada |
| Vista | J1 ABAJO | **la palanca hacia atrás** |
| Bocina | J1 B1 | nada |

Además, la palanca original de 18 Wheeler tiene tres posiciones **que se quedan puestas**, y la del Crazy
Taxi tiene dos y vuelve al centro. Fuentes: `INPUT_PORTS` de MAME, `naomi_roms_input.h` de Flycast y la
[referencia de arneses](../docs/referencia-arneses.md).

## Cómo queda con el parche

| Haces | Resultado |
|---|---|
| Toque de palanca **adelante** | Marcha **larga**, se queda puesta |
| Toque de palanca **atrás** | Marcha **corta**, se queda puesta |
| Palanca atrás **mantenida** ¼ s pisando el freno, o 0,75 s sin freno | **Marcha atrás** mientras la mantengas; al soltar, corta |
| **START** corto (pulsar y soltar) | **Cambio de vista** |
| **START mantenido** (más de ⅓ s) | **Bocina** mientras lo mantengas (sin cambio de vista al soltar) |
| Volante, acelerador, freno, START | Igual que siempre |

Al arrancar empieza en corta. Los tiempos y el umbral del freno están en la cabecera de `build_patch.py`
(`HOLD`, `LONG`, `BRAKE`, `HORN`).

## Qué hace el parche (técnico)

La función `0x0C021E30` copia cada frame la respuesta JVS y rellena las estructuras de jugador:

| Dirección | Contenido |
|---|---|
| `0x0C289490` | byte de sistema JVS |
| `0x0C289491 + 16·i` | bytes crudos del jugador *i* (la I/O escribe 2; el resto del hueco queda libre) |
| `0x0C2896B2` | analógicos (palabras; jugador *i* desde `+16·i`: volante, acelerador, freno) |
| `0x0C2892D0 + 20·i` | estructura: `u16` actual, anterior, pulsado, soltado + 3 analógicos `u32` |

El bucle que rellena las estructuras estaba desenrollado y ocupaba 200 bytes. Se reescribe compacto
en el mismo sitio (`0x0C021F4E`–`0x0C02205D`). Se salta el pool de literales `0x0C021F82`–`0x0C021FB3`,
que no se toca. En el espacio que queda va la lógica:

- Estado en bytes libres del hueco JVS del J1: `0x0C28949B` marcha, `0x0C28949C` frames con la palanca
  atrás, `0x0C28949D` frames con START pulsado.
- El byte 0 del J1 que ve el juego lleva START y SERVICE, pero no la palanca, más VISTA y BOCINA cuando
  toca. El byte 0 del J2 lleva la marcha.
- El búfer crudo no se modifica. Otros lectores del búfer (comprobación de SERVICE en `0x0C02CD30`…)
  siguen viendo lo real.

La rutina de arranque de `0x0C0206xx` llama a `0x0C021FDA`. Es código muerto: es la zona entre la
cabecera y la entrada `0x0C021000`, nada del programa real la referencia y todas sus llamadas apuntan
a direcciones desplazadas.

## Cómo aplicarlo

```sh
python3 ../apply_patch.py TU_18wheeler_std.bin.gz 18wheeler_ct.ips 18wheeler_std_ct.bin.gz
```

Volcado probado: `n1-18_wheeler_std-[840-0036].bin`, 176 177 152 bytes, MD5 `dc761d5f3ac44b749894a9e1227146d8`.

## Verificación

- `test_patch.py` ejecuta 6000 frames aleatorios en `../tools/sh4mini.py`. La función parcheada
  alimentada con lo que manda el mueble da las mismas estructuras **byte a byte** que la original
  alimentada con un "arnés lógico" (modelo en Python de la tabla de arriba). Además prueba los
  escenarios: toques, mantener con y sin freno, START corto y largo.
- Solo cambian 210 bytes de la ROM, todos dentro de la función.

## Estado

| Paso | Estado |
|---|---|
| Localizar entradas y estructura | ✅ |
| Parche + prueba en intérprete | ✅ |
| Prueba en placa | ⏳ |
