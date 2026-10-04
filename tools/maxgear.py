#!/usr/bin/env python3
"""Gameplay aid: set every weapon's attack and every armour's defence to 255.

    python3 tools/maxgear.py [build/KAMI/MAIN.EXE]

Patches the item table in the built MAIN.EXE in place (25-byte records from
0x436c0; +17 is the u8 attack/defence, low nibble of +23 the category). Not
part of the translation: tools/install.py rebuilds MAIN.EXE from game/ and so
undoes this -- run it again after every install. Close the game first; it
reads MAIN.EXE only at start.
"""
from __future__ import annotations

import sys

ITEMS, STRIDE, COUNT = 0x436C0, 25, 126
VALUE, CATEGORY = 17, 23
GEAR = {0: "weapon", 1: "bow", 2: "armour"}


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "build/KAMI/MAIN.EXE"
    data = bytearray(open(path, "rb").read())
    changed = 0
    for i in range(COUNT):
        rec = ITEMS + i * STRIDE
        if data[rec + CATEGORY] & 0x0F in GEAR and data[rec + VALUE] != 255:
            data[rec + VALUE] = 255
            changed += 1
    open(path, "wb").write(bytes(data))
    print(f"{path}: {changed} items set to 255")


if __name__ == "__main__":
    main()
