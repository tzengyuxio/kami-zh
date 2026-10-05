#!/usr/bin/env python3
"""Render every map of the 13 dungeons in VDMAP.DAT (entries 40-52).

    .venv/bin/python tools/dungeonmap.py build/maps/dungeons
    .venv/bin/python tools/dungeonmap.py --list > list.md

Writes NN_<name>-A.png, -B.png... per map and NN_<name>.png per dungeon (all
maps, wrapped into rows). --guide DIR writes the same set again with the
chests, stairs, doors, teleport pads and switches marked, and the chest
contents listed under each map. --list prints those records as Markdown.
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
# (file, first tile, tile count, colour bits ORed in). The two cave sets are
# drawn with colour bit 3 forced on: on screen every pixel of them is the
# stored value | 8 (checked tile by tile against save-state VGA memory).
TILESET = {3: ("A", 433, 195, 8), 4: ("A", 433, 195, 8), 5: ("A", 433, 195, 8),
           6: ("A", 433, 195, 8), 7: ("A", 628, 205, 8), 8: ("A", 628, 205, 8),
           9: ("A", 628, 205, 8), 10: ("A", 628, 205, 8), 11: ("A", 833, 199, 0),
           12: ("A", 1032, 221, 0), 13: ("A", 1032, 221, 0), 14: ("C", 413, 226, 0)}
# Map header +27: 11 record counts, then the records of types 0-7 in order,
# each type of fixed size; the two compressed layers follow straight after.
COUNTS, RECORDS = 27, 38
RECORD_SIZES = (5, 6, 5, 7, 3, 5, 6, 5)
TELEPORT, DOOR, STAIRS, SWITCH, CHEST = 0, 1, 2, 3, 5
ITEMS, ITEM_SIZE = 0x436C0, 25   # MAIN.EXE item table, name in the first 14
PER_ROW_WIDTH = 3200       # sheet: wrap to a new row past this many pixels


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


def records(floor: bytes) -> list[list[bytes]]:
    """The event records of one map, by type (see formats.md)."""
    out, p = [], RECORDS
    for t, size in enumerate(RECORD_SIZES):
        n = floor[COUNTS + t]
        out.append([floor[p + i * size:p + (i + 1) * size] for i in range(n)])
        p += n * size
    return out


def tile_layer(floor: bytes) -> bytes:
    """The tile layer: right after the event records."""
    start = RECORDS + sum(floor[COUNTS + t] * size for t, size in enumerate(RECORD_SIZES))
    w, h = floor[0], floor[1]
    tiles, _ = vm.decode(floor, start + 16, floor[start:start + 16], w * h)
    return tiles


def listing(maps: list[bytes], zh: bytes) -> None:
    """Markdown: the records of every map, coordinates as (x,y) in tiles."""
    def item(i: int) -> str:
        rec = zh[ITEMS + i * ITEM_SIZE:ITEMS + i * ITEM_SIZE + 14]
        return rec.split(b"\0")[0].decode("cp932")

    def to(e: int, m: int, x: int, y: int) -> str:
        return "大地圖" if m == 0xFF else f"MAP {e}-{chr(65 + m)} ({x},{y})"

    for e in range(FIRST, LAST + 1):
        print(f"\n### {e} {name(zh, e)}\n")
        for f, floor in enumerate(floors(maps[e])):
            r = records(floor)
            rows = []
            for c in r[CHEST]:
                rows.append(f"寶箱 ({c[0]},{c[1]})：{item(c[2])}" + ("（特殊）" if c[3] else ""))
            for c in r[STAIRS]:
                rows.append(f"樓梯／出入口 ({c[0]},{c[1]}) → {to(e, c[2], c[3], c[4])}")
            for c in r[DOOR]:
                rows.append(f"門 ({c[0]},{c[1]}) → {to(e, c[3], c[4], c[5])}")
            for c in r[TELEPORT]:
                if c[2] == 3:
                    rows.append(f"傳送陣 ({c[0]},{c[1]}) → ({c[3]},{c[4]})")
            for c in r[SWITCH]:
                rows.append(f"機關 ({c[0]},{c[1]})")
            print(f"- **MAP {e}-{chr(65 + f)}**（{floor[0]}×{floor[1]}）")
            for row in rows:
                print(f"  - {row}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("out", nargs="?", help="output directory")
    ap.add_argument("--list", action="store_true", help="print the event records instead")
    ap.add_argument("--guide", help="also write annotated maps to this directory")
    ap.add_argument("--game", default="game/KAMI")
    ap.add_argument("--build", default="build/KAMI", help="for the translated names")
    args = ap.parse_args()

    maps = vm.entries(worldmap.read(os.path.join(args.game, "VDMAP.DAT")))
    exe = worldmap.read(os.path.join(args.game, "MAIN.EXE"))
    zh = worldmap.read(os.path.join(args.build, "MAIN.EXE"))
    if args.list:
        listing(maps, zh)
        return
    if not args.out:
        ap.error("需要輸出目錄")
    os.makedirs(args.out, exist_ok=True)
    sets = {"A": vm.Tiles(os.path.join(args.game, "VDMAPG_A.DAT")),
            "C": vm.Tiles(os.path.join(args.game, "VDMAPG_C.DAT"))}
    font = ImageFont.truetype(worldmap.FONTS["zh"], 40)
    small = ImageFont.truetype(worldmap.FONTS["zh"], 28)
    mark = ImageFont.truetype(worldmap.FONTS["zh"], 14)
    if args.guide:
        os.makedirs(args.guide, exist_ok=True)

    for e in range(FIRST, LAST + 1):
        title = name(zh, e)
        images, guides = [], []
        for f, floor in enumerate(floors(maps[e])):
            w, h, pal_no = floor[0], floor[1], floor[PALETTE_BYTE]
            file_id, first, _, bits = TILESET[pal_no]
            layer = tile_layer(floor)
            im = Image.new("P", (w * 16, h * 16))
            im.putpalette(vm.palette_bytes(exe, pal_no))
            tiles = sets[file_id]
            for i, v in enumerate(layer):
                tile = tiles.get(first + v)
                if bits:
                    tile = tile.point(lambda c: c | bits)
                im.paste(tile, ((i % w) * 16, (i // w) * 16))
            im = im.convert("RGB")
            im.save(os.path.join(args.out, f"{e}_{title}-{chr(65 + f)}.png"))
            images.append(im)
            if args.guide:
                g = annotate(im, floor, zh, mark)
                g.save(os.path.join(args.guide, f"{e}_{title}-{chr(65 + f)}.png"))
                guides.append(g)
        sheet(images, e, title, font, small).save(os.path.join(args.out, f"{e}_{title}.png"))
        if args.guide:
            sheet(guides, e, title, font, small).save(os.path.join(args.guide, f"{e}_{title}.png"))
        print(f"{e} {title}（{name(exe, e)}）: {len(images)} maps")


MARKS = {"chest": (255, 214, 0), "stairs": (80, 230, 100), "door": (90, 170, 255),
         "teleport": (230, 110, 255), "switch": (255, 80, 80)}


def annotate(im: Image.Image, floor: bytes, zh: bytes, font) -> Image.Image:
    """A copy of one map with its records marked, chest contents below."""
    r = records(floor)
    out = im.copy()
    draw = ImageDraw.Draw(out)

    def box(x: int, y: int, colour) -> None:
        draw.rectangle((x * 16, y * 16, x * 16 + 15, y * 16 + 15), outline=colour, width=2)

    def label(x: int, y: int, text: str, colour) -> None:
        w = draw.textlength(text, font=font)
        lx = min(max(x * 16 + 8 - w / 2, 1), out.width - w - 1)
        ly = y * 16 - 17 if y > 0 else y * 16 + 17
        draw.text((lx, ly), text, font=font, fill=colour, stroke_width=2, stroke_fill=(0, 0, 0))

    def dest(m: int) -> str:
        return "出口" if m == 0xFF else chr(65 + m)

    for c in r[STAIRS]:
        box(c[0], c[1], MARKS["stairs"])
        label(c[0], c[1], f"→{dest(c[2])}", MARKS["stairs"])
    for c in r[DOOR]:
        box(c[0], c[1], MARKS["door"])
        label(c[0], c[1], f"門→{dest(c[3])}", MARKS["door"])
    for c in r[TELEPORT]:
        if c[2] == 3:
            box(c[0], c[1], MARKS["teleport"])
            draw.line((c[0] * 16 + 8, c[1] * 16 + 8, c[3] * 16 + 8, c[4] * 16 + 8),
                      fill=MARKS["teleport"], width=2)
            label(c[0], c[1], "傳送", MARKS["teleport"])
    for c in r[SWITCH]:
        box(c[0], c[1], MARKS["switch"])
        label(c[0], c[1], "機關", MARKS["switch"])
    lines = []
    for n, c in enumerate(r[CHEST], 1):
        box(c[0], c[1], MARKS["chest"])
        label(c[0], c[1], f"寶{n}", MARKS["chest"])
        rec = zh[ITEMS + c[2] * ITEM_SIZE:ITEMS + c[2] * ITEM_SIZE + 14]
        lines.append(f"寶{n}  {rec.split(b'\0')[0].decode('cp932')}  ({c[0]},{c[1]})")
    if not lines:
        return out
    legend = Image.new("RGB", (out.width, 8 + 20 * len(lines)), (20, 20, 20))
    ld = ImageDraw.Draw(legend)
    for k, text in enumerate(lines):
        ld.text((6, 4 + 20 * k), text, font=font, fill=MARKS["chest"])
    full = Image.new("RGB", (out.width, out.height + legend.height))
    full.paste(out, (0, 0))
    full.paste(legend, (0, out.height))
    return full


def sheet(images: list[Image.Image], number: int, name: str, font, small) -> Image.Image:
    """All maps of one dungeon: a title, then rows of maps (wrapped), each
    with a "MAP NN-X" caption above it and a line between neighbours."""
    gap, cap, head, line = 24, 44, 70, (150, 150, 150)
    rows, row = [], []
    for im in images:
        if row and sum(i.width + gap for i in row) + im.width > PER_ROW_WIDTH:
            rows.append(row)
            row = []
        row.append(im)
    rows.append(row)
    width = max(sum(i.width for i in r) + gap * (len(r) + 1) for r in rows)
    heights = [max(i.height for i in r) + cap for r in rows]
    out = Image.new("RGB", (width, head + sum(heights) + gap * len(rows)), (40, 40, 40))
    draw = ImageDraw.Draw(out)
    draw.text((gap, 14), f"{number} {name}", font=font, fill=(255, 255, 255))
    y, n = head, 0
    for r, rh in zip(rows, heights):
        if y > head:
            draw.line((0, y - gap // 2, width, y - gap // 2), fill=line, width=2)
        x = gap
        for im in r:
            if x > gap:
                draw.line((x - gap // 2, y, x - gap // 2, y + rh), fill=line, width=2)
            draw.text((x, y + 6), f"MAP {number}-{chr(65 + n)}", font=small, fill=(255, 255, 255))
            out.paste(im, (x, y + cap))
            x += im.width + gap
            n += 1
        y += rh + gap
    return out

if __name__ == "__main__":
    main()
