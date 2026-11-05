# Referencia: arneses de un mueble Crazy Taxi multijuego → qué tiene que hacer cada parche

Fuente: hoja *Crazy Taxi Harness Details* del hilo de arcade-projects
[Crazy Taxi multi-harness w/ button panels](https://www.arcade-projects.com/threads/crazy-taxi-multi-harness-w-button-panels.30132/).
Su autor resuelve por **hardware** (tres arneses y paneles de botones extra) lo que aquí se hace por
**software**. Cada arnés equivale a una "reasignación" que el parche debe hacer dentro del juego.

## Lo que manda el mueble Crazy Taxi (sin tocar)

| Control | Entrada JVS |
|---|---|
| START | J1 START |
| Palanca adelante (DRIVE) | J1 ARRIBA |
| Palanca atrás (REVERSE) | J1 ABAJO |
| Volante / acelerador / freno | Analógicos 0 / 1 / 2 |

No hay más botones: lo que en el arnés sale del panel auxiliar, por software habrá que asignarlo a una
**combinación** (p. ej. START durante la carrera, toques de palanca), como ya se hizo con
START + freno = crédito.

## Arnés 1 — Jambo! Safari

| Del mueble | Va a |
|---|---|
| J1 ARRIBA | J2 ABAJO |
| J1 ABAJO | J2 ARRIBA |

Equivale al parche `jambo-safari/jambo_ct_cruzado.ips` (✅ probado en placa).

## Arnés 2 — Initial D 1/2/3, King of Route 66, 18 Wheeler, Club Kart (y OutRun 2 de Chihiro)

| Del mueble / panel | Va a | Nota |
|---|---|---|
| J1 ARRIBA (palanca adelante) | J2 ARRIBA | palanca **directa**, no cruzada |
| J1 ABAJO (palanca atrás) | J2 ABAJO | |
| Botón crucero (con enclavamiento) | J2 ARRIBA | 18 Wheeler / KoR66: mantiene la marcha larga |
| Puente | J2 ABAJO + J2 IZQUIERDA | 18 Wheeler: marcha atrás = ABAJO + IZQUIERDA a la vez |
| Botón VISTA | J1 ABAJO | |
| Botón BOCINA | J1 B1 | 18 Wheeler / KoR66 |
| Botón LIMPIAPARABRISAS | J1 B2 | KoR66 |
| Pulsador del MICRÓFONO | J1 B3 | KoR66 (además necesita el micro y la placa 839-1132) |

Consecuencia importante: **en estos juegos el cable de "palanca atrás" del Crazy Taxi (J1 ABAJO) es el
botón VISTA**. Sin parche, tirar de la palanca cambia la cámara en vez de la marcha.

Qué debe hacer el parche (patrón común):
1. Copiar J1 ARRIBA/ABAJO a J2 ARRIBA/ABAJO (variante *directa* del parche del Jambo).
2. **Quitar** J1 ABAJO del J1, para que la palanca no cambie la vista.
3. Poner VISTA (J1 ABAJO) en una combinación libre.
4. 18 Wheeler: decidir cómo sacar larga / corta / marcha atrás con una palanca de dos posiciones y
   retorno (p. ej. adelante = larga enclavada, atrás = corta, atrás mantenido o con freno = marcha atrás),
   y la bocina (J1 B1) en otra combinación.
5. KoR66: además limpiaparabrisas (J1 B2) y micrófono (J1 B3).

## Arnés 3 — Faster Than Speed, Maximum Speed (Atomiswave)

| Del mueble / panel | Va a | Nota |
|---|---|---|
| J1 ARRIBA / ABAJO | J1 ARRIBA / ABAJO | sin cambios |
| Botón TURBO | J1 B1 | solo Faster Than Speed |

- **Maximum Speed**: debería funcionar sin parche.
- **Faster Than Speed**: solo falta el turbo (J1 B1) en una combinación.

## Salidas de luces

El autor usa las salidas de lámparas libres de la I/O (pines 52–55 del conector JST de 60, +12 V en el
60) para iluminar sus botones. Por software no hacen falta.
