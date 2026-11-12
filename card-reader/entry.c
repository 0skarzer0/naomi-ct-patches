/* Cabecera del bloque: va la primera en VC_BASE (sección .header). */
#include "vcard.h"
extern vc_card_t vc_card;
extern vc_debug_t vc_debug;
extern char __vc_base[];
__attribute__((section(".header"), used))
const vc_header_t vc_header = {
    VC_MAGIC, VC_VERSION, (uint32_t)vcard_poll,
    (uint32_t)&vc_card, (uint32_t)&vc_debug, (uint32_t)__vc_base, { 0, 0 }
};
