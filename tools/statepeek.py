#!/usr/bin/env python3
"""Read levels, EXP and stats out of a DOSBox-X save state.

    python3 tools/statepeek.py save/1.sav            # the party: 0 40 48
    python3 tools/statepeek.py save/1.sav 0 12 40    # chosen people

The game cannot save inside dungeons, where all the fighting happens, but a
DOSBox-X save state can be taken anywhere. A state is a zip whose "Memory"
entry is raw guest RAM, and the game keeps SDATA.CIM in RAM laid out as on
disk, so the same signature the EXP hotkey uses (tools/exptsr.py) finds it.
Field layout: docs/formats.md, SDATA.CIM.
"""
from __future__ import annotations

import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exptsr  # noqa: E402

PEOPLE = 0x1372


def find(mem: bytes, sdata: bytes) -> list[int]:
    """Start offsets of every SDATA.CIM image in `mem`.

    Same test as the TSR: up to exptsr.TOLERANCE signature bytes may differ.
    Exact matches of any 8 consecutive signature bytes give the candidates.
    """
    sig = exptsr.signature(sdata)
    found = set()
    for g in range(0, len(sig), 8):
        group = dict(sig[g:g + 8])
        lo, hi = min(group), max(group)
        rx = b''.join(re.escape(bytes([group[k]])) if k in group else b'.'
                      for k in range(lo, hi + 1))
        for m in re.finditer(rx, mem, re.DOTALL):
            t = m.start() - lo
            if t >= 0 and sum(mem[t + k] != v for k, v in sig) <= exptsr.TOLERANCE:
                found.add(t)
    return sorted(t - exptsr.ANCHOR for t in found)


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        raise SystemExit(2)
    state, people = args[0], [int(x) for x in args[1:]] or [0, 40, 48]
    sdata = open(exptsr.GAME_SDATA, 'rb').read()
    z = zipfile.ZipFile(state)
    mem = z.read('Memory')
    print(f"{state}: {z.read('Time_Stamp').decode()}  {z.read('Save_Remark').decode(errors='replace')}")
    bases = find(mem, sdata)
    if not bases:
        raise SystemExit('找不到遊戲資料（快照不是在遊戲中存的？）')
    for base in bases:
        buf = mem[base:base + len(sdata)]
        for i in people:
            r = buf[PEOPLE + i * 33:][:33]
            t = buf[exptsr.TABLE + i * 8:][:8]
            name = r[:15].split(b'\0')[0].decode('cp932', errors='replace')
            print(f'  {i:3d} {name:<8} L{t[3]:<3d} 距下一級 {t[4] | t[5] << 8:4d}  '
                  f'體力 {r[15] | r[16] << 8:3d}  氣力 {r[17] | r[18] << 8:3d}  力 {r[19]:3d}  '
                  f'知力 {r[20]:3d}  敏捷 {r[21]:3d}  運 {r[22]:3d}  靈巧 {r[23]:3d}')


if __name__ == '__main__':
    main()
