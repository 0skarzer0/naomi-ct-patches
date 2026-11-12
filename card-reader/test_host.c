/* Prueba en el PC: simula el driver serie de Initial D (buffers circulares) y la capa del lector del juego. */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "vcard.h"

static uint8_t port[0x1200] __attribute__((aligned(4)));
#define CTL(i) (((uint32_t *)(port + 0x7FC))[i])

static void game_putc(uint8_t b) {           /* como 0x0C13AF60 */
    port[0x82C] = 1;
    port[0x10 + CTL(5)] = b; CTL(5) = (CTL(5) + 1) & 0x3FF; CTL(7)++;
    port[0x82C] = 0;
}
static int game_getc(void) {                  /* como 0x0C13B100 */
    if (!CTL(8)) return -1;
    uint8_t b = port[0x410 + ((CTL(6) - CTL(8) + 0x400) & 0x3FF)]; CTL(8)--; return b;
}
static int fails = 0;
#define CHECK(c, ...) do { if (!(c)) { printf("FALLO: " __VA_ARGS__); printf("\n"); fails++; } } while (0)

static void send_packet(uint8_t cmd, const uint8_t *p, int n, int corrupt) {
    uint8_t len = 6 + n, bcc = len;
    game_putc(0x02); game_putc(len);
    uint8_t hdr[4] = { cmd, 0, 0, 0 };
    for (int i = 0; i < 4; i++) { game_putc(hdr[i]); bcc ^= hdr[i]; }
    for (int i = 0; i < n; i++) { game_putc(p[i]); bcc ^= p[i]; }
    game_putc(0x03); bcc ^= 0x03;
    game_putc(corrupt ? bcc ^ 0xFF : bcc);
}
typedef struct { uint8_t cmd, r, p, s; uint8_t data[256]; int n; } reply_t;
static int get_reply(reply_t *r) {
    uint8_t b[300]; int n = 0, c;
    while ((c = game_getc()) >= 0) b[n++] = c;
    if (n < 8 || b[0] != 0x02) return 0;
    uint8_t len = b[1], bcc = 0;
    for (int i = 1; i <= len; i++) bcc ^= b[i];
    if (b[len] != 0x03 || bcc != b[len + 1] || n != len + 2) return 0;
    r->cmd = b[2]; r->r = b[3]; r->p = b[4]; r->s = b[5]; r->n = len - 6;
    memcpy(r->data, b + 6, r->n);
    return 1;
}
/* manda una orden y pregunta con ENQ hasta que deja de estar "trabajando" (como el juego) */
static reply_t cmd(uint8_t c, const uint8_t *p, int n) {
    reply_t r = {0};
    send_packet(c, p, n, 0);
    vcard_poll(port);
    int a = game_getc();
    CHECK(a == 0x06, "orden %02X: esperaba ACK y llegó %d", c, a);
    for (int tries = 0; tries < 10; tries++) {
        game_putc(0x05);
        vcard_poll(port);
        CHECK(get_reply(&r), "orden %02X: respuesta mal formada", c);
        CHECK(r.cmd == c, "orden %02X: la respuesta es de %02X", c, r.cmd);
        if (r.s != 0x33) break;
    }
    return r;
}

int main(void) {
    reply_t r; uint8_t p[256];
    /* 1. sin tarjeta en el fichero: inicializar, estado, leer -> esperando tarjeta */
    vcard_reset();
    p[0] = 0x30; r = cmd(0x10, p, 1); CHECK(r.p == 0x30 && r.s == 0x30, "init: P=%02X S=%02X", r.p, r.s);
    r = cmd(0x20, NULL, 0); CHECK((r.r & 0x1F) == 0x00, "estado sin tarjeta: R=%02X", r.r);
    p[0] = 0x32; p[1] = 0x31; p[2] = 0x36; r = cmd(0x33, p, 3);
    CHECK(r.s == 0x34, "leer sin tarjeta: debería esperar (S=34), S=%02X", r.s);
    r = cmd(0x40, NULL, 0); CHECK(r.s == 0x32, "cancelar: S=%02X", r.s);
    /* 2. comprar tarjeta (dispensar), leer (virgen: error de lectura) y escribir las tres pistas */
    p[0] = 0x31; r = cmd(0xB0, p, 1); CHECK((r.r & 0x1F) == 0x18 && r.p == 0x30, "dispensar: R=%02X P=%02X", r.r, r.p);
    p[0] = 0x30; p[1] = 0x31; p[2] = 0x36; r = cmd(0x33, p, 3); CHECK(r.p == 0x31, "leer virgen: P=%02X", r.p);
    uint32_t seq0 = vc_card.seq;
    p[0] = 0x30; p[1] = 0x31; p[2] = 0x36; for (int i = 0; i < 207; i++) p[3 + i] = (uint8_t)(i * 7 + 1);
    r = cmd(0x53, p, 210); CHECK(r.p == 0x30, "escribir: P=%02X", r.p);
    CHECK(vc_card.flags & 1, "la tarjeta debería quedar válida");
    CHECK(vc_card.seq == seq0 + 1, "seq tras escribir: %u", vc_card.seq);
    CHECK(vc_card.data[0] == 1 && vc_card.data[206] == (uint8_t)(206 * 7 + 1), "datos escritos");
    /* 3. imprimir, expulsar; la siguiente orden retira la tarjeta */
    p[0] = 0x30; p[1] = 0x30; p[2] = 0x30; memcpy(p + 3, "HOLA", 4); r = cmd(0x7C, p, 7); CHECK(r.p == 0x30, "imprimir: P=%02X", r.p);
    r = cmd(0x80, NULL, 0); CHECK((r.r & 0x1F) == 0x01, "expulsar: R=%02X", r.r);
    CHECK(vc_card.seq == seq0 + 2, "seq tras expulsar: %u", vc_card.seq);
    r = cmd(0x20, NULL, 0); CHECK((r.r & 0x1F) == 0x00, "tras expulsar la tarjeta se retira: R=%02X", r.r);
    /* 4. partida siguiente: el juego pide tarjeta y entra sola con los mismos datos */
    p[0] = 0x32; p[1] = 0x31; p[2] = 0x36; r = cmd(0x33, p, 3); CHECK(r.s == 0x30 && (r.r & 0x1F) == 0x18, "meter tarjeta: R=%02X S=%02X", r.r, r.s);
    p[0] = 0x30; r = cmd(0x33, p, 3); CHECK(r.n == 207 && r.data[5] == (uint8_t)(5 * 7 + 1), "leer: %d bytes", r.n);
    CHECK(r.n == 207 && memcmp(r.data, vc_card.data, 207) == 0, "los datos leídos coinciden");
    p[2] = 0x31; r = cmd(0x33, p, 3); CHECK(r.n == 69 && r.data[0] == vc_card.data[69], "leer solo pista 2: %d bytes", r.n);
    /* 5. paquete con BCC mal -> NAK; basura suelta se ignora */
    game_putc(0x55); game_putc(0xAA);
    send_packet(0x20, NULL, 0, 1); vcard_poll(port); CHECK(game_getc() == 0x15, "BCC mal: esperaba NAK");
    r = cmd(0x20, NULL, 0); CHECK(r.p == 0x30, "tras el NAK sigue funcionando");
    /* 6. cerrojos: si el juego está escribiendo, no se toca su buffer */
    port[0x82C] = 1; game_putc(0x05); port[0x82C] = 1; vcard_poll(port); CHECK(CTL(7) == 1, "cerrojo de envío respetado");
    port[0x82C] = 0; vcard_poll(port); get_reply(&r);
    printf("%s (%d fallos). Paquetes %u, NAK %u, ENQ %u, bytes %u/%u\n", fails ? "MAL" : "OK", fails,
           vc_debug.packets, vc_debug.bad_packets, vc_debug.enq, vc_debug.bytes_in, vc_debug.bytes_out);
    return fails != 0;
}
