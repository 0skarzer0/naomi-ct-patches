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

## Siguientes juegos candidatos

Ver [docs/referencia-arneses.md](docs/referencia-arneses.md): lo que hace cada arnés del mueble
multijuego de arcade-projects, traducido a lo que debe hacer cada parche. Orden propuesto:
1. 18 Wheeler (Standard, 840-0036): pendiente de que el usuario pase su volcado.
2. Club Kart e Initial D (solo palanca a J2 + vista).
3. Faster Than Speed (turbo) y comprobar Maximum Speed (Atomiswave).
4. King of Route 66 (lo más complejo).

## Cómo trabajar

1. El usuario pasa su volcado (`.bin.gz`) en el chat; nunca se sube al repo (`.gitignore` lo bloquea).
2. Crear `nombre-juego/` con `build_patch.py`, `test_patch.py`, `README.md`, los `.ips` y sus `.ips.sha1`.
3. Actualizar la tabla del README de este repo, este HANDOFF y la fila del juego en naomi-wheel-games.
