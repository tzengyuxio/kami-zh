#!/usr/bin/env python3
"""Build a DOS TSR that tops up EXP on a hotkey.

    python3 tools/exptsr.py build/EXPKEY.COM 0 40 48
    tools/dosbox/run.sh            # loads build/EXPKEY.COM before the game

In game, Ctrl+E sets "EXP still needed for the next level" to 1 for the
listed people (person indices, as in SDATA.CIM), so their next EXP gain
levels them up. A high beep means it worked, a low beep means the table
was not found. The key itself is swallowed.

The game keeps SDATA.CIM in memory exactly as it is laid out on disk (a
save slot is a byte-for-byte snapshot of it), so the TSR finds the table
the same way a person would: by content. The 8-byte-per-person table at
SDATA.CIM 0x26c8 (EXP-to-next is the u16 at +4) has no field that is both
fixed and varied -- byte +2 looked fixed until a war changed it -- so the
signature comes from ANCHOR, 252 bytes that stayed the same in every save
slot seen (63 images, through year 2). 32 of them, every 6th, are compared
and up to TOLERANCE may differ; the region holds no 0x00 or 0xFF there, so
blank memory cannot match. ANCHOR - TABLE is a whole number of paragraphs,
so the table is reached by stepping the segment back. The signature is
stored XOR'd so the scan never matches the TSR.

The game reads the keyboard through BIOS INT 16h and never hooks INT 09h,
so a plain INT 09h hook sees every key first.
"""
from __future__ import annotations

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mousetsr import ORG, Asm  # noqa: E402

GAME_SDATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'game', 'KAMI', 'SDATA.CIM')
TABLE = 0x26C8          # 8-byte-per-person table inside SDATA.CIM
PEOPLE = 150
ANCHOR = 0x3528         # static region the signature is taken from
SIG_BYTES, SIG_STEP = 32, 6
TOLERANCE = 4           # signature bytes allowed to differ
KEY = 0x5A              # XOR applied to the stored signature
SCAN_E = 0x12           # make code of the E key
HIGH, LOW = 1193182 // 1500, 1193182 // 300   # PIT divisors for the beeps


def signature(sdata: bytes) -> list[tuple[int, int]]:
    """(offset from ANCHOR, byte) pairs."""
    return [(k * SIG_STEP, sdata[ANCHOR + k * SIG_STEP]) for k in range(SIG_BYTES)]


def _emit(people: list[int], sig, paragraphs: int) -> bytes:
    a = Asm()
    a.rel16(b'\xe9', 'install')                 # jmp install

    a.label('old09');     a.raw(b'\x00\x00')
    a.label('old09_seg'); a.raw(b'\x00\x00')
    a.label('busy');      a.raw(b'\x00')
    a.label('found');     a.raw(b'\x00')
    a.label('people')
    a.raw(b''.join(struct.pack('<H', i * 8 + 4) for i in people))
    a.label('pairs')
    a.raw(bytes(x for off, val in sig for x in (off, val ^ KEY)))

    # INT 09h: Ctrl+E -> scan and patch, anything else -> BIOS
    a.label('h09')
    a.raw(b'\x50')                              # push ax
    a.raw(b'\xe4\x60')                          # in al,60h
    a.raw(b'\x3c' + bytes([SCAN_E]))            # cmp al,E
    a.rel8(b'\x75', 'chain')
    a.raw(b'\x1e\x31\xc0\x8e\xd8')              # push ds / xor ax,ax / mov ds,ax
    a.raw(b'\xa0\x17\x04')                      # mov al,[0417h]  (BIOS shift flags)
    a.raw(b'\x1f')                              # pop ds
    a.raw(b'\xa8\x04')                          # test al,4  (Ctrl)
    a.rel8(b'\x74', 'chain')
    a.at(b'\x2e\x80\x3e', 'busy', b'\x00')      # cmp byte cs:[busy],0
    a.rel8(b'\x75', 'chain')
    a.raw(b'\xb0\x20\xe6\x20')                  # EOI: the key never reaches BIOS
    a.at(b'\x2e\xc6\x06', 'busy', b'\x01')
    a.raw(b'\xfb')                              # sti: let the timer run (beep waits on it)
    a.raw(b'\x53\x51\x52\x56\x57\x1e\x06')      # push bx cx dx si di ds es
    a.rel16(b'\xe8', 'scan')
    a.raw(b'\x07\x1f\x5f\x5e\x5a\x59\x5b')      # pop es ds di si dx cx bx
    a.at(b'\x2e\xc6\x06', 'busy', b'\x00')
    a.raw(b'\x58\xcf')                          # pop ax / iret
    a.label('chain')
    a.raw(b'\x58')                              # pop ax
    a.at(b'\x2e\xff\x2e', 'old09')              # jmp far cs:[old09]

    # scan conventional memory (every seg:0..15 up to A000:0) for the table
    a.label('scan')
    a.raw(b'\x0e\x1f')                          # push cs / pop ds
    a.at(b'\xc6\x06', 'found', b'\x00')
    a.raw(b'\x31\xd2')                          # xor dx,dx
    a.label('seg_loop')
    a.raw(b'\x8e\xc2\x31\xff')                  # mov es,dx / xor di,di
    a.label('off_loop')
    a.at(b'\xbe', 'pairs')                      # mov si,pairs
    a.raw(b'\xb9' + struct.pack('<H', len(sig)))
    a.raw(b'\x30\xe4')                          # xor ah,ah  (mismatches)
    a.label('cmp_loop')
    a.raw(b'\x8a\x1c\x30\xff')                  # mov bl,[si] / xor bh,bh
    a.raw(b'\x26\x8a\x01')                      # mov al,es:[bx+di]
    a.raw(b'\x34' + bytes([KEY]))               # xor al,KEY
    a.raw(b'\x3a\x44\x01')                      # cmp al,[si+1]
    a.rel8(b'\x74', 'same')
    a.raw(b'\xfe\xc4')                          # inc ah
    a.raw(b'\x80\xfc' + bytes([TOLERANCE]))     # cmp ah,TOLERANCE
    a.rel8(b'\x77', 'no_match')                 # ja
    a.label('same')
    a.raw(b'\x83\xc6\x02')                      # add si,2
    a.rel8(b'\xe2', 'cmp_loop')                 # loop
    a.rel16(b'\xe8', 'patch')
    a.label('no_match')
    a.raw(b'\x47\x83\xff\x10')                  # inc di / cmp di,16
    a.rel8(b'\x72', 'off_loop')
    a.raw(b'\x42\x81\xfa\x00\xa0')              # inc dx / cmp dx,0A000h
    a.rel8(b'\x72', 'seg_loop')
    a.raw(b'\xbb' + struct.pack('<H', LOW))     # mov bx,LOW
    a.at(b'\x80\x3e', 'found', b'\x00')         # cmp byte [found],0
    a.rel8(b'\x74', 'beep')
    a.raw(b'\xbb' + struct.pack('<H', HIGH))    # mov bx,HIGH
    a.rel8(b'\xeb', 'beep')

    # patch: es:di is ANCHOR; step es back to the table, EXP-to-next := 1
    a.label('patch')
    a.at(b'\xc6\x06', 'found', b'\x01')
    a.raw(b'\x56\x51\x06')                      # push si / push cx / push es
    a.raw(b'\x8c\xc0\x2d' + struct.pack('<H', (ANCHOR - TABLE) >> 4))  # mov ax,es / sub ax,n
    a.raw(b'\x8e\xc0')                          # mov es,ax
    a.at(b'\xbe', 'people')
    a.raw(b'\xb9' + struct.pack('<H', len(people)))
    a.label('p_loop')
    a.raw(b'\x8b\x1c')                          # mov bx,[si]
    a.raw(b'\x26\xc7\x01\x01\x00')              # mov word es:[bx+di],1
    a.raw(b'\x83\xc6\x02')                      # add si,2
    a.rel8(b'\xe2', 'p_loop')
    a.raw(b'\x07\x59\x5e\xc3')                  # pop es / pop cx / pop si / ret

    # beep: bx = PIT divisor, held for 3 timer ticks
    a.label('beep')
    a.raw(b'\xb0\xb6\xe6\x43')                  # mov al,0B6h / out 43h,al
    a.raw(b'\x88\xd8\xe6\x42\x88\xf8\xe6\x42')  # divisor lo, hi -> port 42h
    a.raw(b'\xe4\x61\x50\x0c\x03\xe6\x61')      # in al,61h / push ax / or al,3 / out 61h,al
    a.raw(b'\x1e\xb8\x40\x00\x8e\xd8')          # push ds / mov ax,40h / mov ds,ax
    a.raw(b'\x8b\x0e\x6c\x00\x83\xc1\x03')      # mov cx,[6Ch] / add cx,3
    a.label('wait')
    a.raw(b'\xa1\x6c\x00\x39\xc8')              # mov ax,[6Ch] / cmp ax,cx
    a.rel8(b'\x75', 'wait')
    a.raw(b'\x1f\x58\xe6\x61\xc3')              # pop ds / pop ax / out 61h,al / ret

    a.label('install')
    a.raw(b'\xb8\x09\x35\xcd\x21')              # mov ax,3509h / int 21h
    a.at(b'\x89\x1e', 'old09'); a.at(b'\x8c\x06', 'old09_seg')
    a.at(b'\xba', 'h09'); a.raw(b'\xb8\x09\x25\xcd\x21')
    a.raw(b'\xba' + struct.pack('<H', paragraphs))
    a.raw(b'\xb8\x00\x31\xcd\x21')              # TSR
    return a.assemble()


def build(people: list[int], sdata: bytes) -> bytes:
    assert (ANCHOR - TABLE) % 16 == 0
    if not people or any(not 0 <= i < PEOPLE for i in people):
        raise ValueError(f'person indices must be 0..{PEOPLE - 1}')
    sig = signature(sdata)
    paragraphs = (ORG + len(_emit(people, sig, 0)) + 15) >> 4
    return _emit(people, sig, paragraphs)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print('usage: exptsr.py <out.com> <person index> [...]')
        raise SystemExit(2)
    com = build([int(x) for x in sys.argv[2:]], open(GAME_SDATA, 'rb').read())
    open(sys.argv[1], 'wb').write(com)
    print(f'{sys.argv[1]}: {len(com)} bytes, Ctrl+E -> people {sys.argv[2:]}')


if __name__ == '__main__':
    main()
