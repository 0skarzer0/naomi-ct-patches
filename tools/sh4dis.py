import sys, struct, capstone as c
rom=sys.argv[1]; start=int(sys.argv[2],16); n=int(sys.argv[3],16)
B=0x0C020000
d=open(rom,'rb').read()
md=c.Cs(c.CS_ARCH_SH, c.CS_MODE_SH4 | c.CS_MODE_LITTLE_ENDIAN)
off=start-B
for i in range(0,n,2):
    a=start+i; w=d[off+i:off+i+2]
    ins=list(md.disasm(w,a))
    txt=f'{ins[0].mnemonic} {ins[0].op_str}' if ins else f'.word {w.hex()}'
    # resolve PC-rel literals
    op=struct.unpack('<H',w)[0]
    extra=''
    if op>>12==0xD:  # mov.l @(disp,pc),Rn
        la=((a+4)&~3)+(op&0xff)*4; v=struct.unpack_from('<I',d,la-B)[0]; extra=f'   ; [{la:08x}]={v:08x}'
    elif op>>12==0x9:
        la=a+4+(op&0xff)*2; v=struct.unpack_from('<H',d,la-B)[0]; extra=f'   ; [{la:08x}]={v:04x}'
    print(f'{a:08x}: {w.hex()}  {txt}{extra}')
