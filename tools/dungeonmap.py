#!/usr/bin/env python3
"""Render every floor of the 13 dungeons in VDMAP.DAT (entries 40-52).

    .venv/bin/python tools/dungeonmap.py build/maps/dungeons

Writes NN_<name>-F.png per floor and NN_<name>.png per dungeon (floors side
by side).
Format: docs/formats.md, "Dungeon maps".
"""
from __future__ import annotations

import argparse
import os
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import villagemap as vm  # noqa: E402
import worldmap  # noqa: E402

FIRST, LAST = 40, 52
# MAIN.EXE: the dungeon names, one per entry 40-52 in this order. The order
# fits every check made: 41 is the opening cave (黄泉比良坂), the save state
# taken before the Susa boss is in 49 (スサの沼), 50 is the forest set.
NAMES = [0x519ce, 0x519d9, 0x519e4, 0x519ef, 0x519f6, 0x519fd, 0x51a06,
         0x51a0b, 0x51a14, 0x51a21, 0x51a2a, 0x51a35, 0x51a40]
PALETTE_BYTE = 24          # floor header: palette number (MAIN.EXE table)
# Tile set by palette number. Not stored anywhere found; deduced from the
# tile cache in save-state RAM (5, 10, 11) and the set sizes (see formats.md).
# (file, first tile, tile count)
TILESET = {3: ("A", 433, 195), 4: ("A", 433, 195), 5: ("A", 433, 195), 6: ("A", 433, 195),
           7: ("A", 628, 205), 8: ("A", 628, 205), 9: ("A", 628, 205), 10: ("A", 628, 205),
           11: ("A", 833, 199), 12: ("A", 1032, 221), 13: ("A", 1032, 221),
           14: ("C", 413, 226)}
# Floors where the ranking in tile_layer picks the wrong start, checked
# against screenshots: (entry, floor number) -> layer start.
LAYER_START = {(44, 2): 47, (48, 2): 48, (50, 8): 48, (52, 6): 63, (52, 9): 147}


def name(exe: bytes, e: int) -> str:
    off = NAMES[e - FIRST]
    return exe[off:exe.index(b"\0", off)].decode("cp932")


def floors(entry: bytes) -> list[bytes]:
    """The u32 BE offsets after the 2-byte header, up to 0xffffffff."""
    offs, p = [], 2
    while p + 4 <= len(entry):
        v = struct.unpack_from(">I", entry, p)[0]
        if v == 0xFFFFFFFF or v == 0 or v >= len(entry):
            break
        offs.append(v)
        p += 4
    offs.append(len(entry))
    return [entry[offs[i]:offs[i + 1]] for i in range(len(offs) - 1)]


def tile_layer(floor: bytes, count: int) -> bytes:
    """Find where the two compressed layers start and return the tile layer.

    The header before them holds variable-length event records that are not
    decoded yet, so try every start: the right one makes both layers come out
    at width x height and end exactly at the end of the floor. When several
    starts pass, prefer the one with fewest values outside the tile set, then
    the smoothest.
    """
    w, h = floor[0], floor[1]
    best = None
    for p in range(27, len(floor) - 32):
        try:
            tiles, pos = vm.decode(floor, p + 16, floor[p:p + 16], w * h)
            attrs, end = vm.decode(floor, pos + 16, floor[pos:pos + 16], w * h)
        except IndexError:
            continue
        if len(tiles) != w * h or len(attrs) != w * h or end != len(floor):
            continue
        outside = sum(v >= count for v in tiles)
        same = sum(tiles[i] == tiles[i + 1] for i in range(len(tiles) - 1))
        if best is None or (-outside, same) > best[0]:
            best = ((-outside, same), tiles)
    if best is None:
        raise ValueError("no layer start found")
    return best[1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("out", help="output directory")
    ap.add_argument("--game", default="game/KAMI")
    ap.add_argument("--build", default="build/KAMI", help="for the translated names")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    maps = vm.entries(worldmap.read(os.path.join(args.game, "VDMAP.DAT")))
    exe = worldmap.read(os.path.join(args.game, "MAIN.EXE"))
    zh = worldmap.read(os.path.join(args.build, "MAIN.EXE"))
    sets = {"A": vm.Tiles(os.path.join(args.game, "VDMAPG_A.DAT")),
            "C": vm.Tiles(os.path.join(args.game, "VDMAPG_C.DAT"))}
    font = ImageFont.truetype(worldmap.FONTS["zh"], 40)

    for e in range(FIRST, LAST + 1):
        title = name(zh, e)
        images = []
        for f, floor in enumerate(floors(maps[e])):
            w, h, pal_no = floor[0], floor[1], floor[PALETTE_BYTE]
            file_id, first, count = TILESET[pal_no]
            start = LAYER_START.get((e, f + 1))
            if start is None:
                layer = tile_layer(floor, count)
            else:
                layer, _ = vm.decode(floor, start + 16, floor[start:start + 16], w * h)
            im = Image.new("P", (w * 16, h * 16))
            im.putpalette(vm.palette_bytes(exe, pal_no))
            tiles = sets[file_id]
            for i, v in enumerate(layer):
                im.paste(tiles.get(first + v), ((i % w) * 16, (i // w) * 16))
            im = im.convert("RGB")
            ImageDraw.Draw(im).text((12, 8), f"{e} {title} 第{f + 1}層", font=font, fill=(255, 255, 255),
                                    stroke_width=4, stroke_fill=(0, 0, 0))
            im.save(os.path.join(args.out, f"{e}_{title}-{f + 1}.png"))
            images.append(im)
        gap = 16
        sheet = Image.new("RGB", (sum(i.width for i in images) + gap * (len(images) + 1),
                                  max(i.height for i in images) + 2 * gap), (40, 40, 40))
        x = gap
        for im in images:
            sheet.paste(im, (x, gap))
            x += im.width + gap
        sheet.save(os.path.join(args.out, f"{e}_{title}.png"))
        print(f"{e} {title}（{name(exe, e)}）: {len(images)} floors")


if __name__ == "__main__":
    main()
