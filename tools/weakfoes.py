#!/usr/bin/env python3
"""Gameplay aid: set every monster's HP, and every boss part's HP, to 10.

    python3 tools/weakfoes.py [build/KAMI] [hp]

Patches in place:
  RPDATA.CIM  42-byte records, +17 u16 HP (ordinary monsters)
  BPDATA.CIM  36-byte records, one per boss (RPDATA +15 minus 7), +12 six
              u16 part HPs -- the centre first; the boss's own RPDATA HP is
              not what its battle uses
EXP (RPDATA +40) is untouched. Not part of the translation: tools/install.py
rewrites RPDATA.CIM from game/ (BPDATA.CIM is copied as is), so run this
again after every install.
"""
from __future__ import annotations

import os
import struct
import sys

STRIDE, COUNT, HP = 42, 60, 17   # records 60-69 are empty placeholders
BOSS_STRIDE, BOSS_COUNT, PARTS = 36, 10, 12


def main() -> None:
    folder = sys.argv[1] if len(sys.argv) > 1 else "build/KAMI"
    hp = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    path = os.path.join(folder, "RPDATA.CIM")
    data = bytearray(open(path, "rb").read())
    for i in range(COUNT):
        struct.pack_into("<H", data, i * STRIDE + HP, hp)
    open(path, "wb").write(bytes(data))
    print(f"{path}: HP of {COUNT} monsters set to {hp}")

    path = os.path.join(folder, "BPDATA.CIM")
    data = bytearray(open(path, "rb").read())
    for i in range(BOSS_COUNT):
        struct.pack_into("<6H", data, i * BOSS_STRIDE + PARTS, *[hp] * 6)
    open(path, "wb").write(bytes(data))
    print(f"{path}: HP of {BOSS_COUNT} bosses' parts set to {hp}")


if __name__ == "__main__":
    main()
