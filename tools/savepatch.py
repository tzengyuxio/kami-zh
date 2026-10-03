#!/usr/bin/env python3
"""Bring the names in a saved game in line with the current build.

    python3 tools/install.py                       # build first
    python3 tools/savepatch.py build/KAMI/SAVEDATA.DAT

SAVEDATA.DAT is a 54-byte header followed by three slots, and each slot is a
full snapshot of SDATA.CIM. Names are therefore copied in when a game starts
and never re-read: a save made before a name was translated keeps the old
text for good. This rewrites the name fields from build/KAMI/SDATA.CIM:

  header    3 x 18 bytes, hero name at +3 (what the load menu shows)
  villages  slot + 0x92,   29 records x 29 bytes, name in the first 9
  people    slot + 0x1372, 150 records x 33 bytes, name in the first 15

Nothing but name bytes changes. The hero (person 0) is named by the player,
so it is only rewritten while it still holds the original Japanese name.
The untouched file is kept as <file>.bak the first time.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tables  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
HEADER = 54
HEADER_ENTRY = 18
HEADER_NAME = 3
PEOPLE = tables.TABLES["SDATA.CIM"]


def fields():
    """(kind, index, offset within a slot, width) for every name field."""
    v = tables.VILLAGES
    for i in range(v["count"]):
        yield "village", i, v["sdata"] + i * v["stride"], v["name_field"]
    for i in range(PEOPLE["count"]):
        yield "person", i, PEOPLE["start"] + i * PEOPLE["stride"], tables.NAME_FIELD


def name(raw: bytes) -> bytes:
    return raw.split(b"\x00")[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("save", help="SAVEDATA.DAT, patched in place")
    ap.add_argument("--game", default=ROOT / "game/KAMI/SDATA.CIM", type=Path)
    ap.add_argument("--build", default=ROOT / "build/KAMI/SDATA.CIM", type=Path)
    args = ap.parse_args()

    game = args.game.read_bytes()
    build = args.build.read_bytes()
    data = bytearray(Path(args.save).read_bytes())
    slot_size = len(game)
    if len(data) != HEADER + 3 * slot_size:
        sys.exit(f"{args.save}: {len(data)} bytes, 預期 {HEADER + 3 * slot_size}")

    hero_ja = name(game[PEOPLE["start"]:PEOPLE["start"] + tables.NAME_FIELD])
    hero_zh = name(build[PEOPLE["start"]:PEOPLE["start"] + tables.NAME_FIELD])
    changed = {"header": 0, "village": 0, "person": 0}

    for k in range(3):
        base = HEADER + k * slot_size
        if not name(data[base + tables.VILLAGES["sdata"]:][:9]):
            continue            # empty slot: nothing was ever saved here
        for kind, i, off, width in fields():
            current = data[base + off:base + off + width]
            wanted = build[off:off + width]
            if kind == "person" and i == 0 and name(current) != hero_ja:
                continue        # the player's own name for the hero
            if name(current) != name(wanted):
                data[base + off:base + off + width] = wanted
                changed[kind] += 1

        h = k * HEADER_ENTRY + HEADER_NAME
        if name(data[h:h + HEADER_ENTRY - HEADER_NAME]) == hero_ja:
            data[h:h + HEADER_ENTRY - HEADER_NAME] = hero_zh.ljust(
                HEADER_ENTRY - HEADER_NAME, b"\x00")
            changed["header"] += 1

    if not any(changed.values()):
        print(f"{args.save}: 名稱已與 build 一致，未修改")
        return
    backup = Path(f"{args.save}.bak")
    if not backup.exists():
        shutil.copy2(args.save, backup)
    Path(args.save).write_bytes(bytes(data))
    print(f"{args.save}: 村名 {changed['village']} 筆、人名 {changed['person']} 筆、"
          f"讀檔選單 {changed['header']} 筆（原檔備份於 {backup.name}）")


if __name__ == "__main__":
    main()
