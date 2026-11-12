/*
 * Lector de tarjetas virtual para NAOMI: imita un Sanwa CRP-1231BR-10 dentro del propio juego.
 *
 * El juego cree que habla con un lector por el puerto serie (SCIF). En vez de mover los bytes
 * entre los buffers del driver y el hardware, vcard_poll() los consume y deja la respuesta del
 * lector en el buffer de recepción. La tarjeta vive en memoria (vc_card) y la Raspberry la carga
 * y la guarda en un fichero .card por la NetDIMM.
 *
 * Protocolo (implementación propia; referencias: YACardEmu de GXTX y los scripts de Winteriscoming):
 *   juego -> lector:  STX LEN CMD 0 0 0 parámetros... ETX BCC     (BCC = XOR de LEN..ETX)
 *   lector -> juego:  ACK (0x06) si el paquete es correcto, NAK (0x15) si no
 *   juego -> lector:  ENQ (0x05) para pedir el resultado
 *   lector -> juego:  STX LEN CMD R P S datos... ETX BCC
 *     R = posición de la tarjeta, P = error (0x30 = ninguno), S = estado (0x33 = trabajando)
 */
#include "vcard.h"

#define STX 0x02
#define ETX 0x03
#define ENQ 0x05
#define ACK 0x06
#define NAK 0x15

/* Posición de la tarjeta (valor R del CRP-1231BR-10) */
enum { POS_NONE = 0x00, POS_EJECT = 0x01, POS_HEAD = 0x18, POS_THERMAL = 0x07, POS_DISPENSER = 0x1C };
/* Errores (P) */
enum { P_OK = 0x30, P_READ = 0x31, P_PRINT = 0x35, P_ILLEGAL = 0x38, P_SYSTEM = 0x41 };
/* Estado (S) */
enum { S_IDLE = 0x30, S_ILLEGAL = 0x32, S_RUNNING = 0x33, S_WAITING = 0x34 };

/* ---- Interfaz con el driver serie de Initial D (0x0C13AF60 putc, 0x0C13B100 getc, 0x0C13A9E0 tarea) ----
 * puerto + 0x010: buffer de envío (1024 B)   puerto + 0x410: buffer de recepción (1024 B)
 * puerto + 0x7FC: +20 índice de escritura de envío, +24 índice de escritura de recepción,
 *                 +28 bytes pendientes de envío,    +32 bytes pendientes de recepción, +44 errores
 * puerto + 0x82C: cerrojo de envío (el juego está escribiendo)   + 0x82D: cerrojo de recepción     */
#define PORT_TX      0x010
#define PORT_RX      0x410
#define PORT_CTL     0x7FC
#define PORT_TXLOCK  0x82C
#define PORT_RXLOCK  0x82D
#define RING_MASK    0x3FF
#define RING_SIZE    0x400

/* ---- Estado ---- */
#ifdef VC_HOST
#define VC_SECTION(x)
#else
#define VC_SECTION(x) __attribute__((section(x)))
#endif

vc_card_t  vc_card  VC_SECTION(".card")  = { VC_CARD_MAGIC, 0, 0, 0, {0}, {0} };
vc_debug_t vc_debug VC_SECTION(".vcdebug");

static uint8_t  in_buf[256];     /* paquete que llega del juego */
static uint32_t in_len;
static uint8_t  out_buf[256];    /* respuesta pendiente de pasar al juego */
static uint32_t out_len, out_pos;

static uint8_t  cmd;             /* orden en curso */
static uint8_t  params[256];
static uint32_t nparams;
static uint32_t step;            /* veces que el juego ha preguntado (ENQ) por esta orden */
static uint8_t  running;
static uint8_t  pos = POS_NONE;  /* dónde está la tarjeta */
static uint8_t  st_p = P_OK, st_s = S_IDLE;
static uint8_t  shutter = 1;
static uint8_t  fresh;           /* tarjeta nueva del dispensador, todavía sin datos */
static uint8_t  reply_data[VC_CARD_SIZE];
static uint32_t reply_len;

static void vc_log(uint8_t dir, uint8_t b)
{
    uint32_t p = vc_debug.log_pos & (VC_LOG_SIZE - 1);
    vc_debug.log[p] = dir;
    vc_debug.log[p + 1] = b;
    vc_debug.log_pos = (p + 2) & (VC_LOG_SIZE - 1);
}

static void out_byte(uint8_t b)
{
    if (out_len < sizeof(out_buf)) out_buf[out_len++] = b;
}

static uint8_t pos_value(void)
{
    /* bit7 persiana abierta (bit6 si cerrada), bit5 dispensador con tarjetas, bits 0-4 posición */
    return (shutter ? 0x80 : 0x40) | 0x20 | pos;
}

static void card_saved(void)
{
    vc_card.seq++;            /* la Pi baja la tarjeta cuando cambia */
}

static int has_card(void) { return pos != POS_NONE; }

/* Si el juego espera una tarjeta y hay una válida en el fichero, se "mete" sola. */
static int try_insert(void)
{
    if (has_card()) return 1;
    if (!(vc_card.flags & VC_CARD_VALID)) return 0;
    pos = POS_EJECT;          /* presentada en la ranura */
    fresh = 0;
    vc_card.inserts++;
    return 1;
}

static void copy_tracks(uint8_t sel)
{
    /* 0x30..0x32 = pista 1..3; 0x33 = 1+2; 0x34 = 1+3; 0x35 = 2+3; 0x36 = las tres */
    static const uint8_t mask[7] = { 1, 2, 4, 3, 5, 6, 7 };
    uint32_t t, i;
    reply_len = 0;
    if (sel < 0x30 || sel > 0x36) { st_p = P_ILLEGAL; return; }
    for (t = 0; t < VC_TRACKS; t++)
        if (mask[sel - 0x30] & (1u << t))
            for (i = 0; i < VC_TRACK_SIZE; i++)
                reply_data[reply_len++] = vc_card.data[t * VC_TRACK_SIZE + i];
}

static void store_tracks(uint8_t sel, const uint8_t *src, uint32_t len)
{
    static const uint8_t mask[7] = { 1, 2, 4, 3, 5, 6, 7 };
    uint32_t t, i, n = 0;
    if (sel < 0x30 || sel > 0x36) { st_p = P_ILLEGAL; return; }
    for (t = 0; t < VC_TRACKS; t++)
        if (mask[sel - 0x30] & (1u << t)) {
            if (n + VC_TRACK_SIZE > len) { st_p = P_SYSTEM; return; }
            for (i = 0; i < VC_TRACK_SIZE; i++)
                vc_card.data[t * VC_TRACK_SIZE + i] = src[n++];
        }
    vc_card.flags |= VC_CARD_VALID;
    fresh = 0;
    card_saved();
}

static void finish(void) { running = 0; if (st_s == S_RUNNING) st_s = S_IDLE; }

/* Avanza la orden en curso un paso (se llama en cada ENQ). */
static void run_command(void)
{
    reply_len = 0;
    switch (cmd) {
    case 0x10:                                   /* inicializar: la tarjeta, si la hay, sale */
        if (has_card()) { pos = POS_EJECT; card_saved(); }
        finish();
        break;
    case 0x20:                                   /* estado */
        finish();
        break;
    case 0x33:                                   /* leer: param 0 = modo, 2 = pistas */
        if (!has_card() && !try_insert()) {      /* sin tarjeta: esperar (el juego reintenta) */
            st_s = S_WAITING;
            return;
        }
        if (step == 0) return;                   /* primera respuesta: "trabajando" */
        st_s = S_RUNNING;
        pos = POS_HEAD;
        if (nparams >= 3 && params[0] != 0x32) { /* 0x32 = solo meter la tarjeta */
            if (fresh || !(vc_card.flags & VC_CARD_VALID)) st_p = P_READ;   /* tarjeta virgen */
            else copy_tracks(params[2]);
        }
        finish();
        break;
    case 0x40:                                   /* cancelar */
        st_s = S_ILLEGAL;
        running = 0;
        break;
    case 0x53:                                   /* escribir: param 0 = modo, 2 = pistas, 3.. = datos */
        if (!has_card() || nparams < 3) { st_p = P_ILLEGAL; finish(); break; }
        if (step == 0) return;
        store_tracks(params[2], params + 3, nparams - 3);
        pos = POS_HEAD;
        finish();
        break;
    case 0x7C:                                   /* imprimir una línea: se acepta y se descarta */
        if (!has_card()) { st_p = P_PRINT; finish(); break; }
        if (step == 0) { pos = POS_THERMAL; return; }
        pos = POS_HEAD;
        finish();
        break;
    case 0x80:                                   /* expulsar */
        if (step < 2) return;                    /* el lector real tarda: dos respuestas "trabajando" */
        if (has_card()) { pos = POS_EJECT; card_saved(); }
        finish();
        break;
    case 0xA0:                                   /* limpieza del cabezal */
        if (step < 2) return;
        finish();
        break;
    case 0xB0:                                   /* dispensar tarjeta nueva */
        if (has_card()) { st_s = S_ILLEGAL; running = 0; break; }
        if (step == 0) return;
        pos = POS_HEAD;
        fresh = 1;
        finish();
        break;
    case 0xD0:                                   /* persiana: param 0 = 0x31 abrir */
        shutter = (nparams >= 1 && params[0] == 0x31);
        finish();
        break;
    case 0x78: case 0x7A: case 0xC0: case 0xC1: case 0xE1: case 0xF5:
        finish();                                /* ajustes de impresora, LED, reloj...: aceptar */
        break;
    default:
        st_s = S_ILLEGAL;
        running = 0;
        break;
    }
}

static void send_reply(void)
{
    uint32_t i;
    uint8_t len, bcc;
    if (running) {
        run_command();
        step++;
    }
    len = (uint8_t)(4 + reply_len + 2);
    out_byte(STX);
    out_byte(len);
    bcc = len;
    out_byte(cmd);            bcc ^= cmd;
    out_byte(pos_value());    bcc ^= pos_value();
    out_byte(st_p);           bcc ^= st_p;
    out_byte(st_s);           bcc ^= st_s;
    for (i = 0; i < reply_len; i++) { out_byte(reply_data[i]); bcc ^= reply_data[i]; }
    reply_len = 0;
    out_byte(ETX);            bcc ^= ETX;
    out_byte(bcc);
    vc_debug.last_status = ((uint32_t)pos_value() << 16) | ((uint32_t)st_p << 8) | st_s;
}

static void packet_done(void)
{
    uint32_t i, len = in_buf[1];
    uint8_t bcc = 0;
    for (i = 1; i <= len; i++) bcc ^= in_buf[i];
    if (len < 6 || in_buf[len] != ETX || bcc != in_buf[len + 1]) {
        vc_debug.bad_packets++;
        out_byte(NAK);
        return;
    }
    vc_debug.packets++;
    /* el jugador se lleva la tarjeta expulsada antes de la orden siguiente */
    if (pos == POS_EJECT && in_buf[2] != 0x33 && in_buf[2] != 0xD0)
        pos = POS_NONE;
    cmd = in_buf[2];
    nparams = len - 6;                  /* LEN cuenta CMD, 3 bytes, parámetros y ETX */
    for (i = 0; i < nparams; i++) params[i] = in_buf[6 + i];
    vc_debug.last_cmd = cmd;
    vc_debug.cmd_count[cmd >> 4]++;
    step = 0;
    running = 1;
    st_p = P_OK;
    st_s = S_RUNNING;
    out_byte(ACK);
}

static void host_byte(uint8_t b)
{
    vc_debug.bytes_in++;
    vc_log(0, b);
    if (in_len == 0) {
        if (b == ENQ) { vc_debug.enq++; send_reply(); return; }
        if (b != STX) return;           /* basura fuera de paquete */
    }
    if (in_len < sizeof(in_buf)) in_buf[in_len++] = b;
    if (in_len >= 2 && in_len == (uint32_t)in_buf[1] + 2) {
        packet_done();
        in_len = 0;
    } else if (in_len >= sizeof(in_buf)) {
        in_len = 0;
    }
}

void vcard_reset(void)
{
    in_len = out_len = out_pos = 0;
    running = 0;
    pos = POS_NONE;
    st_p = P_OK;
    st_s = S_IDLE;
    shutter = 1;
}

/* Sustituye a la tarea periódica del driver (0x0C13A9E0): mismo argumento (el puerto). */
void vcard_poll(uint8_t *port)
{
    volatile uint32_t *ctl = (volatile uint32_t *)(port + PORT_CTL);
    vc_debug.polls++;

    /* juego -> lector: vaciar el buffer de envío */
    if (!port[PORT_TXLOCK]) {
        while (ctl[7] > 0) {                                   /* +28: pendientes */
            uint32_t idx = (ctl[5] - ctl[7] + RING_SIZE) & RING_MASK;   /* +20: escritura */
            uint8_t b = port[PORT_TX + idx];
            ctl[7] = ctl[7] - 1;
            host_byte(b);
        }
    }
    /* lector -> juego: llenar el buffer de recepción */
    if (!port[PORT_RXLOCK]) {
        while (out_pos < out_len && ctl[8] < RING_SIZE) {      /* +32: pendientes de leer */
            uint32_t w = ctl[6];                               /* +24: escritura */
            uint8_t b = out_buf[out_pos++];
            port[PORT_RX + w] = b;
            ctl[6] = (w + 1) & RING_MASK;
            ctl[8] = ctl[8] + 1;
            vc_debug.bytes_out++;
            vc_log(1, b);
        }
        if (out_pos >= out_len) out_pos = out_len = 0;
    }
}
