# Initial D Arcade Stage (Export) Rev A (NAOMI 2, GDS-0025A): cambio secuencial y vista con el Crazy Taxi

## El problema

| Función en Initial D | Entrada que espera | Qué le llega desde el mueble Crazy Taxi |
|---|---|---|
| Subir marcha | J2 ARRIBA | nada |
| Bajar marcha | J2 ABAJO | nada |
| Cambio de vista | J1 ABAJO | **la palanca hacia atrás** |
| Volante / acelerador / freno / START | analógicos 0/1/2, J1 START | igual |

La palanca original de Initial D es secuencial y de retorno (MAME: *two state shift lever*), como la del
Crazy Taxi. Basta con llevarla al J2 sin cruzar, como hace el arnés 2 de la
[referencia de arneses](../docs/referencia-arneses.md), y quitarla del J1.

## Cómo queda con el parche

| Haces | Resultado |
|---|---|
| Palanca **adelante** | **Subir marcha** (una por toque) |
| Palanca **atrás** | **Bajar marcha** (una por toque) |
| **START** corto (soltado antes de medio segundo) | **Cambio de vista** al soltar |
| START mantenido | Solo START, sin cambio de vista |
| Volante, acelerador, freno | Igual que siempre |

Para usar la palanca, elige **MT** (cambio manual) al empezar. Con **AT** no hace falta.

## Qué hace el parche (técnico)

En este juego el programa se carga desde el offset `0x500` de la ROM en `0x0C020000`.

| Dirección | Contenido |
|---|---|
| `0x0C157840` | copia la respuesta JVS: sistema `0x0C8D860C`, jugadores `0x0C8D860D + 16·p`, monedas `0x0C8D870E`, analógicos `0x0C8D872E` |
| `0x0C8D85FC` | jugadores, bytes por jugador y analógicos que informa la I/O |
| `0x0C1579C0` | rellena las estructuras **por bytes**: sistema `0x0C7DDFF0`, jugadores `0x0C7DE030 + 64·p` (actual `+0`, anterior `+16`, pulsado `+32`, soltado `+48`) |

Los dos bucles de `0x0C1579C0`, el del byte de sistema y el de jugadores (`0x0C1579D6`–`0x0C157A7B`),
se reescriben con una subrutina común. En el espacio ganado va la lógica:

- El byte 0 del J1 pierde ARRIBA/ABAJO (la palanca) y gana ABAJO (vista) un frame al soltar un START corto.
- El byte 0 del J2 recibe ARRIBA/ABAJO de la palanca.
- Estado: 1 byte libre del hueco JVS del J1 (`0x0C8D8615`), con los frames que lleva START pulsado.
  Válido mientras la I/O mande menos de 9 bytes por jugador (la de Sega manda 2).
- El prólogo, el epílogo y el resto de la función no cambian. El búfer crudo no se modifica.

## Cómo aplicarlo

```sh
python3 ../apply_patch.py TU_initial_d_export_rev.a.bin.gz initiald_ct.ips initiald_exp_reva_ct.bin.gz
```

Volcado probado: `n2-initial_d_export_rev.a-[GDS-0025A].bin`, 201 129 984 bytes, MD5 `eb7d81c2a0792267d0733beea5956066`.

## Verificación

- `test_patch.py`: 8000 frames aleatorios (0–3 jugadores, 0–8 bytes por jugador). Los bucles parcheados
  dan **byte a byte** las mismas estructuras que los originales alimentados con un "arnés lógico".
  Además prueba los escenarios: palanca adelante y atrás, START corto y largo.
- Solo cambian 163 bytes de la ROM. Nadie salta al interior de la zona reescrita.

## Estado

| Paso | Estado |
|---|---|
| Localizar entradas y estructuras | ✅ |
| Parche + prueba en intérprete | ✅ |
| Prueba en placa | ⏳ |
| Ver. 2 y Ver. 3 | ⏳ (mismo método; necesitan su propio parche) |
