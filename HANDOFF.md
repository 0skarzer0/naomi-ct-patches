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

### Lector de tarjetas virtual — Initial D Export Rev A — 🧪 falta probar en placa

- Petición del usuario: que Initial D use una tarjeta guardada como archivo en la Pi, sin cable, igual
  que la `.vmu` de dc2naomi. Se parte del volcado **original** (CARD R/W en ON), no del de lector apagado.
- Todo en [card-reader/](card-reader/README.md). Resumen:
  - bloque C compilado en `0x0DF00000` (entrada extra en la tabla de carga `0x360`);
  - gancho en la tarea periódica del driver serie `0x0C13A9E0` → `vcard_poll(port)`, que habla con los
    buffers circulares del juego;
  - tarjeta en `0x0DF00D00` con contador `seq`; `vcard_pi.py` la mete al enviar y la trae por peek.
- Análisis del juego (RAM = ROM − 0x500 + 0x0C020000):
  - driver serie: `0x0C13A9E0`; bombas de recepción y envío `0x0C13AD40` / `0x0C13AE60`;
  - putc `0x0C13AF60`, getc `0x0C13B100`;
  - capa de tarjeta `0x0C138900`–`0x0C139A00`;
  - tabla de comandos `0x0C1EAB38` ({cmd, nº parámetros, timeout ms}).
- Probado: `test_host` (C en PC) y `test_sh4.py` (binario SH-4 real a través del gancho en
  `tools/sh4mini.py`): 6 paquetes, 0 NAK, tarjeta escrita y releída.
- **Siguiente paso (placa):**
  1. Cargar la imagen en la Pi .60 (NetDIMM 10.0.0.4) y ejecutar `vcard_pi.py debug 10.0.0.4`. Comprobar
     que la cabecera `VCRD` está, que `llamadas` sube (el gancho se ejecuta) y qué comandos llegan.
  2. Si el juego se cuelga al arrancar, sospechar de `0x0DF00000`: mover `VC_BASE` (build.sh/vcard.ld).
  3. Comprar tarjeta, jugar y expulsar; comprobar que aparece `JUEGO.card` en la Pi.
- **2026-11-12, primera prueba en placa (Pi .60 → NetDIMM 10.0.0.4):** el juego arranca con el bloque
  en `0x0DF00000` (RAM libre confirmada) y el gancho funciona. `vcard_pi.py debug`: 12805 llamadas,
  40 paquetes, 0 NAK, comandos 10 (×1), 20 (×4), 40 (×19), 7x (×16); sin tarjeta todavía (seq 0).
  Falta: comprar tarjeta en partida, expulsarla y comprobar que llega `initiald_exp_reva_vcard.card` a la Pi.
- Imagen actual en la Pi (`/boot/roms/initiald_exp_reva_vcard.bin.gz`): controles CT
  (`initial-d/initiald_ct_controles.ips`, sin apagar el lector) + lector virtual + free play y attract
  sound off (`tools/system_defaults.py`). Para que la BIOS aplicara los ajustes se cargó antes Jambo.
  Arranca y habla con el lector igual (36 paquetes, 0 NAK).
- Acceso a la Pi desde la nube: shell del PC del usuario (carpeta conectada en C:; `E:\roms` no se
  monta) + SSH con `tools/pi_ssh.py` (paramiko, usuario root; la contraseña la da el usuario en el chat,
  nunca en ficheros). La web del WiPi es http://192.168.68.60/; la NetDIMM, 10.0.0.4. Las imágenes se suben
  a `/boot/roms/` y `vcard_pi.py` está en `/sbin/piforce/`.
- **2026-11-12, primera partida (sin tarjeta, free play):** el juego mandó 33 (leer, esperando tarjeta);
  el lector virtual contestó S=0x34 (esperando) ~40 veces; después 40 (cancelar), D0 30/31 (persiana) y
  vuelta al sondeo 20/40. No hubo B0 (dispensar) ni 53 (escribir): no se ofreció comprar tarjeta o no se
  eligió. 0 NAK. El byte R coincide con YACardEmu: bit7 persiana abierta (si no, bit6), bit5 = dispensador
  con tarjetas. Falta saber qué mostró la pantalla (¿opción de comprar tarjeta?, ¿depende de créditos?).
- **2026-11-12, cuelgue en attract** justo después de la partida, a la vez que se hacían lecturas masivas por
  peek (`vcard_pi.py debug` + un volcado del registro: ~550 peeks seguidos) con el juego cargando datos del
  DIMM en attract. Con el juego colgado, los peeks tardan 30 s y devuelven 0: los atiende el propio
  software de la NAOMI, así que no se puede ver a posteriori dónde se colgó. El vigilante (4 peeks cada 3 s)
  aguantó 18 min con partida incluida. **Hipótesis:** los peeks seguidos interfieren con las lecturas del
  juego al DIMM. Prueba en curso: juego recargado SIN vigilante, en attract, sin peeks.
  Si no se cuelga: vigilante con 1 peek (seq) por vuelta y la tarjeta leída despacio (pausa entre peeks);
  `debug` solo con el juego parado o en test.
- **2026-11-12, segunda partida (eligiendo comprar tarjeta):** sin cuelgue (vigilante apagado). Contadores:
  10×1, 20×14, 33×3, 40×44, 7x×16, D0×6; **ningún B0 ni 53**, 0 NAK. Pantallas del juego: "DO YOU HAVE AN
  INITIAL D CARD?" (sí = meter tarjeta, no = START) y "WOULD YOU LIKE TO PURCHASE AN INITIAL D CARD?"
  (sí = botón de VISTA, no = START). Con el parche CT, vista = toque corto de START, START = mantenerlo.
  El juego interpreta el byte R así (0x0C138CC0): bits 7-6 → +48 (persiana), bit 5 → +52 STOCKER (1 = OK,
  0 = "NO CARD IN BOX"); el lector virtual manda bit 5 = 1. Sin ajustes de precio de tarjeta en el juego.
  Por confirmar: si el "sí" de compra se registró (¿el pulso de vista vale en ese menú?).
- **2026-11-12, el cuelgue NO es del lector ni del parche:** tras una partida, en attract, se cuelga
  igual con (a) la imagen del lector virtual sin hacer ningún peek, (b) `initiald_exp_reva_ct` (sin lector
  virtual, CARD R/W OFF) y (c) el **volcado original sin parchear**. Coincide con lo publicado sobre la BIOS
  multirregión antigua: Initial D (ID3 documentado) se cuelga en el modo REPLAY del attract después de jugar
  una partida; una BIOS multirregión más nueva (rev C/H, v2.01) lo arregla, según arcade-projects. Mismo
  problema de fondo que 18 Wheeler. Opciones: actualizar la BIOS, o (por estudiar) un parche que
  quite el replay del attract.
- **Pendiente ahora:** el usuario juega comprando tarjeta nueva; después, `vcard_pi.py debug` y comprobar
  `/boot/roms/initiald_exp_reva_vcard.card`; luego recargar el juego y ver que la lee. Después: integrar
  `vcard_pi.py send` en `wipiloader.py` (como dc2naomi) para que funcione cargando desde la web/menú.

### Aviso: 18 Wheeler y la BIOS multirregión

El usuario tiene BIOS multirregión. Según arcade-otaku y arcade-projects, 18 Wheeler se cuelga con ella
(en la demo o en el mapa de EE. UU.) aunque no esté parcheado. Con la BIOS Export EPR-23608B o la
Export H funciona. El parche de 18 Wheeler no se puede probar en placa hasta cambiar la BIOS.

## Free play y attract mudo en todas las imágenes

2026-11-13: a petición del usuario, `tools/sysdef_all.py` se pasó en la Pi .60 a las 50 imágenes de
`/boot/roms` (NAOMI, NAOMI 2, conversiones Atomiswave, dc2naomi y homebrew). Los originales están en
`/boot/roms_orig/`. Registro en `/var/log/system_defaults.log`. Recordar: la BIOS solo aplica los valores al
cambiar de juego, y algunos juegos tienen además su propio ajuste de sonido en attract. Las imágenes que se
generen a partir de ahora habrá que pasarlas también (o usar `tools/system_defaults.py` al crearlas).

Resultado: 49 de 50 imágenes con free play y attract mudo (comprobado leyendo la cabecera de cada una).
Originales en `/boot/roms_orig/` (y `/boot/roms_orig_2/` para dc-mk64, que se había vuelto a generar mientras
corría el lote). **`n2-the_king_of_route66-[840-0087].bin.gz` está corrupto en origen** (pigz: "incomplete
deflate data"; fecha 10 feb): no se tocó, hay que volver a copiarlo desde un volcado bueno y pasarle el script.

### Pi del mueble estándar (192.168.68.250), 2026-11-13 a 18

A petición del usuario se hizo lo mismo en la segunda Raspberry (mueble NAOMI estándar, NetDIMM en `10.0.0.3`),
**sobrescribiendo las imágenes y sin guardar originales** (así no hay que tocar `romsinfo.csv`), con
`tools/sysdef_inplace.py`, y **solo en NAOMI, NAOMI 2 y Atomiswave** (prefijos `aw-`, `n1-`, `n2-`): las
conversiones de Dreamcast (`dc-*`, dc2naomi) y el homebrew (`h-*`) **no se parchean** en esa Pi.

Resultado (comprobado leyendo la cabecera de las 190 imágenes): 159 `aw-`/`n1-`/`n2-` con free play y attract mudo;
29 (`dc-*` y `h-outrunners_dcport`) con la zona 0x1E0-0x25F a ceros, como las de origen; 2 sin tocar porque no
tienen cabecera NAOMI (`n1-ninja_assault-[25469801_NJA3_Ver.A]`, que empieza por `ff ff ff ff…`, y
`n1-the_house_of_the_dead_2-[834-13636]`, que empieza por código SH-4): hay que mirarlos aparte.

Lecciones del incidente:
- **Filtrar siempre por prefijo.** La primera pasada usó una variante de `sysdef_all.py` sin filtro, recorrió toda
  `/boot/roms` y parcheó por error 28 imágenes dc2naomi y `h-outrunners_dcport` antes de pararla. Como no se
  guardaban originales, se **reconstruyeron**: el parche solo cambia 0x1E0-0x25F (bytes 0, 1 y 3 de cada bloque de
  16) y todas las imágenes dc2naomi y homebrew sin parchear de la carpeta del PC tienen esa zona entera a ceros.
  `sysdef_inplace.py` hace esa restauración (`--restore-only`) y solo toca las que tienen exactamente el patrón.
- **Sin originales no hay vuelta atrás exacta:** antes de sobrescribir en lote, comprobar qué ficheros se van a
  tocar (lista de prefijos o una pasada en seco).
- **La Pi se reinició a mitad** (sin RTC: la hora se reinicia; `/var/log` está en tmpfs y se pierde el registro) y
  dejó un `*.tmp` a medias. El original seguía intacto porque se reemplaza solo al terminar. Borrar los `*.tmp` y
  relanzar: salta lo ya hecho. Redirigir la salida a un fichero en `/root`, no a `/var/log`.
- Ritmo en una Pi 3: unos 6 ficheros pequeños cada 3 minutos; las imágenes de 200-450 MB tardan varios minutos
  cada una. Las 190 imágenes (unos 21 GB) llevaron varias horas; el disco necesita espacio libre para una imagen.
- Acceso: SSH desde el PC del usuario con paramiko (`tools/pi_ssh.py`), contraseña por variable de entorno, nunca en
  ficheros ni en el repositorio.

### ERROR 02 en la Pi .250: imágenes solo para Japón (2026-11-19)

`n1-capcom_vs_snk_millenium_fight_2000_pro-unlocked-[GDL-0004]` (y la versión normal, que ya no está en la Pi) daba
**ERROR 02 "THIS GAME IS NOT ACCEPTABLE BY MAIN BOARD"**: su máscara de regiones (0x428 de la cabecera, ver
[docs/naomi.md de DragonMinded/netboot](https://github.com/DragonMinded/netboot/blob/trunk/docs/naomi.md)) vale `01`
(solo Japón); las que cargan tienen `ff`. Con `tools/region_ff.py` se puso a `ff` (cambia solo ese byte, comprobado
con `cmp` sobre la imagen descomprimida). Copia del original en `/boot/roms_backup/` de la Pi. **Falta probarlo en la
placa.** `n1-guilty_gear_xx_reload-[GDL-0019]` también tiene `01` (sin tocar). No tiene que ver con el parche de free
play (0x1E0).

### Pi .250: más regiones, Virtua Fighter 4 y limpieza del CSV (2026-11-19)

- `tools/region_ff.py` (0x428 de `01` a `ff`, copia en `/boot/roms_backup/`) también en
  `n1-guilty_gear_xx_reload-[GDL-0019]` y `n2-virtua_fighter_4_evolution_ver.b-[GDS-0024B]`. Capcom vs SNK Pro ya
  **funciona en placa** con este arreglo (confirmado por el usuario).
- Borrados, con el visto bueno del usuario, los VF4 que no aportan: `[GDS-0012]`, `ver.a-[GDS-0012B]`,
  `final_tuned-[GDS-0036A]`, `final_tuned_ver.a-[GDS-0036D]` y `evolution-[GDS-0024B]` (mismo número que el `ver.b`
  y misma cabecera, pero contenido distinto). Quedan VF4 Ver.B (0012C), Evolution Ver.B y Final Tuned Ver.B (0036F).
- `romsinfo.csv`: quitadas las 16 filas sin fichero (las 5 de VF4 y 11 de juegos que el usuario ya había borrado),
  descripción corta de VF4 Ver.B corregida e importado a la web. 174 filas = 174 ficheros. Copia previa:
  `/boot/config/romsinfo.csv.bak_antes_limpieza`.
- Después, también a petición del usuario, `region_ff.py` en lote (`/root/region_batch.sh` con la lista en
  `/root/region_list.txt`, copia de cada original en `/boot/roms_backup/`) a las 12 que no tenían `ff`: solo Japón
  (`01`) Crackin' DJ 2, Dynamite Baseball, Giant Gram 4, Jingi Storm, Melty Blood Act Cadenza Rev A, Mushi King 2004 y
  2005, Noukone Puzzle Takoron, Rhythm Tengoku y Street Fighter Zero 3 Upper; `02` Derby Owners Club; `03` Gundam
  Federation vs Zeon DX. Sin tocar Dead or Alive 2 (`17`) y Power Stone 2 (`0f`), que ya incluyen USA y Export, y
  `n1-the_house_of_the_dead_2`, sin cabecera NAOMI. Para buscarlas: leer el byte 1065 (0x428) de cada imagen
  descomprimida.

### Crazy Taxi (.60) se cuelga con el parche de free play (2026-11-19)

`n1-crazy_taxi-[840-0002]` parcheado se colgaba a los pocos segundos de partida; el usuario lo restauró. Su cabecera
original ya trae `aplicar = 1` (01 00 00 01: moneda normal, código 1, attract con sonido), así que el parche solo le
cambiaba el bit de attract mudo y el código de monedas (27). Para saber cuál de los dos es, con
`tools/sysdef_copy.py` se hicieron dos copias en `/boot/roms` de la .60, con fila en el menú:
`n1-crazy_taxi_test_sonido` (solo attract mudo) y `n1-crazy_taxi_test_freeplay` (solo free play). Mismo serial
(BAC0) que el original: **cargar otro juego entre prueba y prueba** para que la BIOS aplique los ajustes. Otra causa
posible sin relación con el parche: es un juego de cartucho que lee la NetDIMM durante la partida, y los peeks desde
la Pi ya colgaron Initial D (al hacer las copias solo corría `timehack.py`). **Resultado (2026-11-19):** se cuelgan las dos; la copia de control (mismo contenido, solo recomprimida) no. Causa:
**Crazy Taxi y Jambo! Safari tienen protección contra cambios en la cabecera** (DragonMinded/netboot trae para ambos
un `*_noprotect.binpatch`, «disable header modification protection»). **No pasarles `sysdef_*.py`.** Para free play y
attract mudo se usan los parches de código del propio netboot (`/sbin/piforce/dm_netboot/patches/`) con
`tools/binpatch_gz.py`: `n1-crazy_taxi_test_dm` (original + `CrazyTaxi_freeplay` + `CrazyTaxi_no_attract`, cabecera
intacta) y `n1-jambo_safari_ct_test_dm` (la imagen CT, con la cabecera ya cambiada, + `Jambo_Safari_noprotect`,
`_freeplay` y `_no_attract`). Pendiente de probar en placa.

## Siguientes juegos candidatos

Ver [docs/referencia-arneses.md](docs/referencia-arneses.md): lo que hace cada arnés del mueble
multijuego de arcade-projects, traducido a lo que debe hacer cada parche. Orden propuesto:
1. Club Kart (palanca a J2 + vista) e Initial D Ver. 2 / Ver. 3 (mismo método que la Ver. 1; la
   Ver. 3 exige tarjeta: usar `card-reader/` con su entrada en `GAMES`).
2. Faster Than Speed (turbo) y comprobar Maximum Speed (Atomiswave).
3. King of Route 66 (lo más complejo).

## Cómo trabajar

1. El usuario pasa su volcado (`.bin.gz`) en el chat; nunca se sube al repo (`.gitignore` lo bloquea).
2. Crear `nombre-juego/` con `build_patch.py`, `test_patch.py`, `README.md`, los `.ips` y sus `.ips.sha1`.
3. Actualizar la tabla del README de este repo, este HANDOFF y la fila del juego en naomi-wheel-games.
