#!/usr/bin/env python3
"""Read and rebuild EVENT.DAT, the story script archive.

Layout. The file is a run of blocks; the structure is plain binary and only
the message text is obfuscated (XOR 0x77, which turns a string's NUL
terminator into the 0x77 bytes you see all over the file):

    block:
        u16 script_offsets[]   self-describing: the first entry is the
                               table's own byte size; offsets are relative
                               to the table, i.e. to the block start
        ...script bytecode...
        u16 message_offsets[]  same self-describing form, relative to this
                               table
        ...messages...         XOR 0x77, NUL-terminated, stored contiguously
                               in table order; each at most 70 bytes

Blocks are not chained -- MAIN.EXE carries two zero-terminated u32 index
tables that point into the file, so rebuilding with different message
lengths means patching those too:

    MAIN.EXE 0x049f10   47 x u32   offset of each block's message table
    MAIN.EXE 0x049fd0   47 x u32   offset of each block's start

The file ends with ~420 bytes of stale duplicated text that nothing points
at; it is carried through untouched.
"""
from __future__ import annotations

import os
import struct
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jis

XOR = 0x77
BLOCK_COUNT = 47
# The engine copies a message into a fixed buffer. No original message
# exceeds 70 bytes, and a 78-byte one garbles from byte 70 onward on screen,
# so this is a hard cap -- control codes included.
MAX_MESSAGE = 70
MAIN_MSG_TABLE = 0x049F10
MAIN_START_TABLE = 0x049FD0


@dataclass
class Block:
    index: int
    script: bytes                      # script table + bytecode, verbatim
    messages: list[bytes] = field(default_factory=list)   # plain Shift-JIS


def read_index(main_exe: bytes) -> tuple[list[int], list[int]]:
    starts = list(struct.unpack_from(f'<{BLOCK_COUNT}I', main_exe, MAIN_START_TABLE))
    msg_tabs = list(struct.unpack_from(f'<{BLOCK_COUNT}I', main_exe, MAIN_MSG_TABLE))
    return starts, msg_tabs


def parse(event: bytes, starts: list[int], msg_tabs: list[int]) -> tuple[list[Block], bytes]:
    blocks = []
    end_of_last = 0
    for i, (start, mt) in enumerate(zip(starts, msg_tabs)):
        size = struct.unpack_from('<H', event, mt)[0]
        count = size // 2
        rels = struct.unpack_from(f'<{count}H', event, mt)
        messages = []
        for rel in rels:
            p = mt + rel
            end = event.index(b'\x77', p)
            messages.append(bytes(b ^ XOR for b in event[p:end]))
            end_of_last = max(end_of_last, end + 1)
        blocks.append(Block(index=i, script=event[start:mt], messages=messages))
    return blocks, event[end_of_last:]


def build(blocks: list[Block], tail: bytes) -> tuple[bytes, list[int], list[int]]:
    out = bytearray()
    starts, msg_tabs = [], []
    for b in blocks:
        starts.append(len(out))
        out += b.script
        msg_tabs.append(len(out))
        size = 2 * len(b.messages)
        rel = size
        table = bytearray()
        body = bytearray()
        for m in b.messages:
            table += struct.pack('<H', rel)
            body += bytes(c ^ XOR for c in m) + b'\x77'
            rel += len(m) + 1
        assert struct.unpack_from('<H', table, 0)[0] == size, 'table must describe its own size'
        out += table + body
    out += tail
    return bytes(out), starts, msg_tabs


def write_index(main_exe: bytes, starts: list[int], msg_tabs: list[int]) -> bytes:
    data = bytearray(main_exe)
    struct.pack_into(f'<{BLOCK_COUNT}I', data, MAIN_START_TABLE, *starts)
    struct.pack_into(f'<{BLOCK_COUNT}I', data, MAIN_MSG_TABLE, *msg_tabs)
    return bytes(data)


def load(event_path: str, main_path: str):
    event = open(event_path, 'rb').read()
    main_exe = open(main_path, 'rb').read()
    starts, msg_tabs = read_index(main_exe)
    blocks, tail = parse(event, starts, msg_tabs)
    return event, main_exe, blocks, tail, starts, msg_tabs


def markup(text: str) -> str:
    """The ASCII in a message is all markup -- control codes like G/W/N/X/U/Y
    and S, continuation jumps like C003 or C64, F-jumps, and %s specifiers.
    Real text is fullwidth throughout, so the ASCII sequence must survive a
    translation unchanged."""
    return ''.join(ch for ch in text if ord(ch) < 128)


def cmd_verify(args):
    import csv
    _, _, blocks, _, _, _ = load(args.event, args.main)
    problems = n = 0
    for row in csv.DictReader(open(args.tsv, encoding='utf-8'), delimiter='\t'):
        zh = row.get('translation_zh', '').strip()
        if not zh:
            continue
        n += 1
        bi, i = int(row['block']), int(row['index'])
        where = f'block {bi} 第 {i} 則'
        original = blocks[bi].messages[i].decode('cp932')

        bad = jis.missing(zh)
        if bad:
            print(f'  {where}: {jis.advise(bad)}')
            problems += 1
            continue
        size = len(zh.encode('cp932'))
        if size > MAX_MESSAGE:
            print(f'  {where}: {size} bytes 超過上限 {MAX_MESSAGE}')
            problems += 1
        if markup(zh) != markup(original):
            print(f'  {where}: 控制碼不符 '
                  f'原文 {markup(original)!r} -> 譯文 {markup(zh)!r}')
            problems += 1
    print(f'{args.tsv}: {n} 筆譯文, {problems} 筆有問題')
    if problems:
        raise SystemExit(1)


def cmd_check(args):
    event, _, blocks, tail, starts, msg_tabs = load(args.event, args.main)
    total = sum(len(b.messages) for b in blocks)
    print(f'{len(blocks)} blocks, {total} messages, {len(tail)} bytes of tail')
    rebuilt, s2, m2 = build(blocks, tail)
    print(f'round trip: bytes {"identical" if rebuilt == event else "DIFFER"}, '
          f'starts {"ok" if s2 == starts else "DIFFER"}, '
          f'message tables {"ok" if m2 == msg_tabs else "DIFFER"}')


def cmd_dump(args):
    import csv
    _, _, blocks, _, _, _ = load(args.event, args.main)
    with open(args.out, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t', lineterminator='\n')
        w.writerow(['block', 'index', 'original_ja', 'translation_zh'])
        n = 0
        for b in blocks:
            for i, m in enumerate(b.messages):
                w.writerow([b.index, i, m.decode('cp932'), ''])
                n += 1
    print(f'{args.out}: {n} messages', file=sys.stderr)


def cmd_apply(args):
    import csv
    _, main_exe, blocks, tail, _, _ = load(args.event, args.main)

    trans = {}
    for row in csv.DictReader(open(args.tsv, encoding='utf-8'), delimiter='\t'):
        zh = row.get('translation_zh', '').strip()
        if zh:
            trans[(int(row['block']), int(row['index']))] = zh

    applied = 0
    for b in blocks:
        for i, _ in enumerate(b.messages):
            zh = trans.get((b.index, i))
            if zh is None:
                continue
            try:
                raw = zh.encode('cp932')
            except UnicodeEncodeError:
                raise SystemExit(
                    f'block {b.index} 第 {i} 則: ' + jis.advise(jis.missing(zh)))
            if markup(zh) != markup(blocks[b.index].messages[i].decode('cp932')):
                raise SystemExit(
                    f'block {b.index} 第 {i} 則: 控制碼不符')
            if len(raw) > MAX_MESSAGE:
                raise SystemExit(
                    f'block {b.index} 第 {i} 則: {len(raw)} bytes 超過每則上限 '
                    f'{MAX_MESSAGE}: {zh}')
            b.messages[i] = raw
            applied += 1

    rebuilt, starts, msg_tabs = build(blocks, tail)
    open(args.out_event, 'wb').write(rebuilt)
    open(args.out_main, 'wb').write(write_index(main_exe, starts, msg_tabs))
    delta = len(rebuilt) - sum(1 for _ in open(args.event, 'rb').read())
    print(f'{args.out_event}: {applied} 則譯文, {len(rebuilt)} bytes '
          f'({delta:+d})')


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--event', default='game/KAMI/EVENT.DAT')
    ap.add_argument('--main', default='game/KAMI/MAIN.EXE')
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('check').set_defaults(fn=cmd_check)
    v = sub.add_parser('verify'); v.add_argument('--tsv', required=True)
    v.set_defaults(fn=cmd_verify)
    d = sub.add_parser('dump'); d.add_argument('--out', required=True)
    d.set_defaults(fn=cmd_dump)
    a = sub.add_parser('apply')
    a.add_argument('--tsv', required=True)
    a.add_argument('--out-event', required=True)
    a.add_argument('--out-main', required=True)
    a.set_defaults(fn=cmd_apply)
    args = ap.parse_args()
    args.fn(args)


if __name__ == '__main__':
    main()
