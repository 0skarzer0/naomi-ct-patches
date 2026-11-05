# HANDOFF — estado y cómo retomar (personas o IAs)

Última actualización: 2026-11-05

## Contexto

- Mueble **Crazy Taxi upright** con NAOMI 2 multibios + NetDIMM 512 MB; netboot desde Raspberry Pi 3
  con WiPi Netbooter. Controles: ver tabla en el README.
- Objetivo: adaptar juegos de NAOMI, NAOMI 2 y Atomiswave a esos controles **sin tocar el cableado**,
  publicando solo parches.
- Índice general del proyecto: [naomi-wheel-games](https://github.com/0skarzer0/naomi-wheel-games).

## Estado por juego

### Jambo! Safari (840-0013 Rev A) — 🧪 falta probar en placa

- Volcado de referencia: `n1-jambo_safari-840-0013.bin`, MD5 `4efd869b0d688a80a8ab8c51f4897d24`.
- Parche: reescribe `0x0C0217CC` (offset ROM `0x0017CC`, 104 bytes). Detalles en
  [jambo-safari/README.md](jambo-safari/README.md).
- Verificado: equivalencia en `tools/sh4mini.py` (3000 frames, 0–3 jugadores).
- **Siguiente paso:** el usuario prueba en placa la variante `cruzado` (adelante = lazo). Si el sentido
  sale al revés, `directo`. Anotar el resultado y si aparece algún error de ROM al arrancar.
- No probado en Flycast (hace falta la BIOS NAOMI, que no está en el entorno de trabajo).

## Siguientes juegos candidatos

Pendiente de que el usuario elija. Ideas de la tabla de naomi-wheel-games: F355 Challenge (cambio),
Wave Runner GP, 18 Wheeler (palanca de 3 posiciones), Maximum Speed / Faster Than Speed (Atomiswave),
Club Kart / King of Route 66 / Wild Riders (NAOMI 2).

## Cómo trabajar

1. El usuario pasa su volcado (`.bin.gz`) en el chat; nunca se sube al repo (`.gitignore` lo bloquea).
2. Crear `nombre-juego/` con `build_patch.py`, `test_patch.py`, `README.md`, los `.ips` y sus `.ips.sha1`.
3. Actualizar la tabla del README de este repo, este HANDOFF y la fila del juego en naomi-wheel-games.
