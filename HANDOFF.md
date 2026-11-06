# HANDOFF — estado y cómo retomar (personas o IAs)

Última actualización: 2026-11-05

## Contexto

- Mueble **Crazy Taxi upright** con NAOMI 2 multibios + NetDIMM 512 MB; netboot desde Raspberry Pi 3
  con WiPi Netbooter. Controles: ver tabla en el README.
- Objetivo: adaptar juegos de NAOMI, NAOMI 2 y Atomiswave a esos controles **sin tocar el cableado**,
  publicando solo parches.
- Índice general del proyecto: [naomi-wheel-games](https://github.com/0skarzer0/naomi-wheel-games).

## Estado por juego

### Jambo! Safari (840-0013 Rev A) — ✅ funciona en placa

- Volcado de referencia: `n1-jambo_safari-840-0013.bin`, MD5 `4efd869b0d688a80a8ab8c51f4897d24`.
- Parche: reescribe `0x0C0217CC` (offset ROM `0x0017CC`, 104 bytes). Detalles en
  [jambo-safari/README.md](jambo-safari/README.md).
- Verificado: equivalencia en `tools/sh4mini.py` (3000 frames, 0–3 jugadores).
- **Probado en placa (2026-11-05):** la variante `cruzado` funciona a la primera en el mueble Crazy
  Taxi (palanca adelante = lazo), sin errores de ROM al arrancar. La `directa` queda como alternativa.
- Entrada en `romsinfo.csv` de WiPi: `jambo_safari_ct_cruzado.bin.gz`, `openjvs` = `crazy-taxi`, `game_id` = `BAU0`.
- No probado en Flycast (hace falta la BIOS NAOMI, que no está en el entorno de trabajo).

### 18 Wheeler Standard (840-0036) — 🧪 falta probar en placa

- Volcado de referencia: `n1-18_wheeler_std-[840-0036].bin`, MD5 `dc761d5f3ac44b749894a9e1227146d8`.
- Lógica acordada con el usuario: toque adelante = larga y toque atrás = corta (se quedan puestas);
  atrás mantenido con freno o largo = marcha atrás; START corto = vista; START largo = bocina.
- Parche: reescribe el bucle de estructuras de `0x0C021E30` (zonas `0x0C021F4E`–`0x0C021F81` y
  `0x0C021FB4`–`0x0C02205D`). Detalles en [18-wheeler/README.md](18-wheeler/README.md).
- **Siguiente paso:** el usuario lo prueba en placa. Ajustes posibles en `build_patch.py`: `HOLD`, `LONG`,
  `BRAKE` (umbral del freno) y `HORN`. Si la vista no responde con un pulso de 1 frame, alargarlo.
- Entrada en `romsinfo.csv`: `18wheeler_std_ct.bin.gz`, `openjvs` = `crazy-taxi`, `game_id` = `BBK0`.

### Initial D Export Rev A (GDS-0025A) — 🧪 falta probar en placa

- Volcado de referencia: `n2-initial_d_export_rev.a-[GDS-0025A].bin`, MD5 `eb7d81c2a0792267d0733beea5956066`.
  El programa se carga desde el offset 0x500 de la ROM (en `sh4dis.py` se pasa `500` como 4º argumento).
- Lógica acordada: palanca adelante/atrás = subir/bajar (J2 directa, sin enclavar), START corto = vista.
- Parche: reescribe los bucles de `0x0C1579C0` (ROM `0x137ED6`, 166 bytes). Detalles en
  [initial-d/README.md](initial-d/README.md).
- CARD R/W apagado por defecto (6 bytes en las rutinas de ajustes de fábrica, main y test), a petición del
  usuario: al cambiar de juego por netboot los ajustes se reinician.
- **Siguiente paso:** probarlo en placa (MT). Comprobar si en algún menú el pulso de vista molesta.
- Entrada en `romsinfo.csv`: `initiald_exp_reva_ct.bin.gz`, `openjvs` = `crazy-taxi`, `game_id` = `BFFA`.

### Aviso: 18 Wheeler y la BIOS multirregión

El usuario tiene BIOS multirregión. Según arcade-otaku y arcade-projects, 18 Wheeler se cuelga con ella
(en la demo o en el mapa de EE. UU.) aunque no esté parcheado. Con la BIOS Export EPR-23608B o la
Export H funciona. El parche de 18 Wheeler no se puede probar en placa hasta cambiar la BIOS.

## Siguientes juegos candidatos

Ver [docs/referencia-arneses.md](docs/referencia-arneses.md): lo que hace cada arnés del mueble
multijuego de arcade-projects, traducido a lo que debe hacer cada parche. Orden propuesto:
1. Club Kart (palanca a J2 + vista) e Initial D Ver. 2 / Ver. 3 (mismo método que la Ver. 1).
2. Faster Than Speed (turbo) y comprobar Maximum Speed (Atomiswave).
3. King of Route 66 (lo más complejo).

## Cómo trabajar

1. El usuario pasa su volcado (`.bin.gz`) en el chat; nunca se sube al repo (`.gitignore` lo bloquea).
2. Crear `nombre-juego/` con `build_patch.py`, `test_patch.py`, `README.md`, los `.ips` y sus `.ips.sha1`.
3. Actualizar la tabla del README de este repo, este HANDOFF y la fila del juego en naomi-wheel-games.
