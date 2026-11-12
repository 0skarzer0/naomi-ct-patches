#!/bin/sh
# Compila el lector virtual para SH-4 (Ubuntu: apt install gcc-sh-elf binutils-sh-elf) y la prueba del PC.
set -e
cd "$(dirname "$0")"
CFLAGS="-m4-single-only -ml -O2 -ffreestanding -fno-builtin -nostdlib -fno-pic -fno-common -Wall"
sh-elf-gcc $CFLAGS -c vcard.c -o vcard.o
sh-elf-gcc $CFLAGS -c entry.c -o entry.o
sh-elf-ld -EL -m shlelf -T vcard.ld vcard.o entry.o -o vcard.elf -Map vcard.map
sh-elf-objcopy -O binary --set-section-flags .bss=alloc,load,contents vcard.elf vcard.bin
sh-elf-nm -n vcard.elf > vcard.sym
gcc -DVC_HOST -Wall -O1 -o test_host test_host.c vcard.c && ./test_host
ls -l vcard.bin
