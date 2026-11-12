/*
 * Lector de tarjetas virtual para NAOMI (Sanwa CRP-1231BR-10 y compatibles).
 * Implementación propia del protocolo; referencias: YACardEmu (GXTX, GPL-2.0) y los scripts de
 * Winteriscoming (arcade-projects.com), solo como documentación del protocolo.
 *
 * Memoria: todo el bloque se carga en VC_BASE (RAM que el juego no usa). La Pi lee y escribe la
 * tarjeta por la NetDIMM (peek/poke) en VC_BASE + VC_CARD_OFS.
 */
#ifndef VCARD_H
#define VCARD_H
#include <stdint.h>

#define VC_MAGIC        0x44524356u     /* "VCRD" */
#define VC_CARD_MAGIC   0x44524143u     /* "CARD" */
#define VC_VERSION      1

#define VC_TRACKS       3
#define VC_TRACK_SIZE   69
#define VC_CARD_SIZE    (VC_TRACKS * VC_TRACK_SIZE)   /* 207 bytes = formato .card de YACardEmu */

/* Tarjeta compartida con la Pi (offset fijo dentro del bloque) */
typedef struct {
    uint32_t magic;          /* VC_CARD_MAGIC */
    uint32_t seq;            /* +1 en cada escritura o expulsión: la Pi baja la tarjeta cuando cambia */
    uint32_t flags;          /* bit0: la tarjeta tiene datos válidos */
    uint32_t inserts;        /* veces que se ha metido en la máquina */
    uint8_t  data[VC_CARD_SIZE];
    uint8_t  pad[256 - 16 - VC_CARD_SIZE];
} vc_card_t;

#define VC_CARD_VALID   1

/* Registro de depuración (se lee con peek) */
#define VC_LOG_SIZE     1024
typedef struct {
    uint32_t polls;          /* llamadas a vcard_poll */
    uint32_t bytes_in;       /* bytes recibidos del juego */
    uint32_t bytes_out;      /* bytes enviados al juego */
    uint32_t packets;        /* paquetes válidos */
    uint32_t bad_packets;    /* NAK enviados */
    uint32_t enq;            /* ENQ recibidos */
    uint32_t last_cmd;
    uint32_t last_status;    /* R<<16 | P<<8 | S */
    uint32_t cmd_count[16];  /* por orden: índice = (cmd >> 4) */
    uint32_t log_pos;        /* posición en log[] */
    uint8_t  log[VC_LOG_SIZE];  /* bytes: los del juego con bit7 del índice par... ver README */
} vc_debug_t;

/* Cabecera del bloque, en VC_BASE */
typedef struct {
    uint32_t magic;          /* VC_MAGIC */
    uint32_t version;
    uint32_t poll;           /* dirección de vcard_poll(port) */
    uint32_t card;           /* dirección de vc_card_t */
    uint32_t debug;          /* dirección de vc_debug_t */
    uint32_t base;           /* VC_BASE */
    uint32_t reserved[2];
} vc_header_t;

/* Interfaz del driver serie del juego (librería de Sega usada por Initial D):
 * buffers circulares de 1024 bytes y contadores en puerto + VC_PORT_CTL. */
typedef struct {
    uint32_t tx_buf;         /* offset del buffer de envío (bytes que el juego manda al lector) */
    uint32_t rx_buf;         /* offset del buffer de recepción (bytes que el lector manda al juego) */
    uint32_t ctl;            /* offset de los contadores */
    uint32_t tx_lock;        /* offset del byte de cerrojo de envío */
    uint32_t rx_lock;        /* offset del byte de cerrojo de recepción */
} vc_port_layout_t;

void vcard_poll(uint8_t *port);
void vcard_reset(void);

/* Para la prueba en el PC */
#ifdef VC_HOST
extern vc_card_t  vc_card;
extern vc_debug_t vc_debug;
#endif

#endif
