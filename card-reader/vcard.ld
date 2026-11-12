/* El bloque se carga en VC_BASE (RAM que Initial D no usa: el juego se limita a 0x0C000000-0x0D000000). */
VC_BASE = DEFINED(VC_BASE) ? VC_BASE : 0x0DF00000;
SECTIONS
{
  . = VC_BASE;
  ___vc_base = .;   /* sh-elf antepone "_" a los símbolos de C: __vc_base */
  .header : { KEEP(*(.header)) }
  . = ALIGN(16);
  .text   : { *(.text .text.*) }
  .rodata : { *(.rodata .rodata.*) }
  .data   : { *(.data .data.*) }
  . = ALIGN(256);
  .card   : { KEEP(*(.card)) }
  . = ALIGN(16);
  .debug_area : { KEEP(*(.vcdebug)) }
  .bss    : { *(.bss .bss.* COMMON) }
  . = ALIGN(16);
  ___vc_end = .;
  /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
