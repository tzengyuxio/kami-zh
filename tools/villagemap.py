#!/usr/bin/env python3
"""Render the village floor plans from VDMAP.DAT, with buildings labelled.

    .venv/bin/python tools/villagemap.py build/maps/villages

Writes NN_<name>.png per map (tiles only) and NN_<name>_label.png (with the
buildings from VCDATA.CIM and the entrance marked), plus all.png, a sheet of
every plan. Format: docs/formats.md, "Village maps".
"""
from __future__ import annotations

import argparse
import os
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import palette  # noqa: E402
import worldmap  # noqa: E402

VILLAGE_MAPS = 32          # entries 0-31; 32+ are other screens
OVERLAY_SIZE = 57          # event overlays (ships, doors) are skipped
TILESET_C_FROM = 30        # entries 30+ take their tiles from VDMAPG_C.DAT
PALETTES = 0x52132         # MAIN.EXE: colours 8-15 of each scene, 8 x (b, r, g)
SANDY_FIRST_TILE = 217     # the sandy tile set is drawn with palette 2
BUILDINGS = {0:"村長家", 1: "倉庫", 2: "民家？", 3: "鍛冶屋", 4: "商人？", 5: "渡口"}
EXTRA_NAMES = {29: "熊曾", 30: "邪馬", 31: "血沼"}  # village records 29-31


def palette_bytes(exe: bytes, number: int) -> list[int]:
    """768-byte PIL palette: fixed colours 0-7 plus scene palette `number`."""
    rec = exe[PALETTES + 24 * number:PALETTES + 24 * number + 24]
    scene = [rec[k + 1] << 8 | rec[k + 2] << 4 | rec[k] for k in range(0, 24, 3)]
    pal = [c for v in palette.BASE + scene for c in palette.to_rgb(v)]
    return pal + [0] * (768 - len(pal))


def decode(src: bytes, pos: int, dic: bytes, want: int) -> tuple[bytes, int]:
    """One layer: 00-3F literal n+1, 40-7F n+1 dictionary nibbles, 80-FF run."""
    out = bytearray()
    while len(out) < want:
        b = src[pos]
        pos += 1
        if b < 0x40:
            out += src[pos:pos + b + 1]
            pos += b + 1
        elif b < 0x80:
            k = b - 0x3F
            for j in range(k):
                nib = src[pos + j // 2]
                out.append(dic[nib >> 4 if j % 2 == 0 else nib & 0x0F])
            pos += (k + 1) // 2
        else:
            out += bytes([src[pos]]) * (b - 0x7F)
            pos += 1
    return bytes(out), pos


def entries(data: bytes) -> list[bytes]:
    n = struct.unpack_from(">I", data, 0)[0] // 4
    offs = list(struct.unpack_from(f">{n}I", data, 0)) + [len(data)]
    return [data[offs[i]:offs[i + 1]] for i in range(n)]


def parse(entry: bytes) -> tuple[tuple[int, int], int, int, int, bytes]:
    """(entrance), width, height, first tile, tile layer."""
    x, y, w, h = entry[:4]
    first = entry[4] << 8 | entry[5]
    p = 8 + OVERLAY_SIZE * entry[7]
    tiles, _ = decode(entry, p + 16, entry[p:p + 16], w * h)
    return (x, y), w, h, first, tiles


class Tiles:
    def __init__(self, path: str):
        self.data = worldmap.read(path)
        self.cache: dict[int, Image.Image] = {}

    def get(self, t: int) -> Image.Image:
        if t not in self.cache:
            c = self.data[t * 128:(t + 1) * 128]
            px = bytearray(256)
            for i in range(256):
                v = 0
                for p in range(4):
                    v |= ((c[p * 32 + i // 8] >> (7 - i % 8)) & 1) << p
                px[i] = v
            self.cache[t] = Image.frombytes("P", (16, 16), bytes(px))
        return self.cache[t]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("out", help="output directory")
    ap.add_argument("--game", default="game/KAMI")
    ap.add_argument("--build", default="build/KAMI")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    maps = entries(worldmap.read(os.path.join(args.game, "VDMAP.DAT")))
    vc = worldmap.read(os.path.join(args.game, "VCDATA.CIM"))
    sets = {"A": Tiles(os.path.join(args.game, "VDMAPG_A.DAT")),
            "C": Tiles(os.path.join(args.game, "VDMAPG_C.DAT"))}
    _, ja = worldmap.territories(args.game)
    names = worldmap.zh_names(args.build, ja)
    exe = worldmap.read(os.path.join(args.game, "MAIN.EXE"))
    font = ImageFont.truetype(worldmap.FONTS["zh"], 22)
    big = ImageFont.truetype(worldmap.FONTS["zh"], 40)
    thumbs = []

    for e in range(VILLAGE_MAPS):
        (ex, ey), w, h, first, layer = parse(maps[e])
        tiles = sets["C" if e >= TILESET_C_FROM else "A"]
        im = Image.new("P", (w * 16, h * 16))
        im.putpalette(palette_bytes(exe, 2 if first == SANDY_FIRST_TILE else 1))
        for i, v in enumerate(layer):
            im.paste(tiles.get(first + v), ((i % w) * 16, (i // w) * 16))
        name = names[e] if e < worldmap.VILLAGE_COUNT else EXTRA_NAMES[e]
        stem = os.path.join(args.out, f"{e:02d}_{name}")
        im = im.convert("RGB")
        im.save(stem + ".png")

        draw = ImageDraw.Draw(im)
        rec = vc[e * 31:(e + 1) * 31]
        for k in range(5):
            bx, by, kind = rec[11 + 4 * k:14 + 4 * k]
            if kind in BUILDINGS:
                worldmap.label(draw, (bx * 16 + 8, by * 16 - 12), BUILDINGS[kind], font)
        worldmap.label(draw, (ex * 16 + 8, ey * 16 - 30), "入口", font)
        draw.text((12, 8), f"{e:02d} {name}", font=big, fill=(255, 255, 255),
                  stroke_width=4, stroke_fill=(0, 0, 0))
        im.save(stem + "_label.png")
        thumbs.append(im)

    # Overview sheet: every labelled plan scaled to the same width.
    cell = 600
    rows = (len(thumbs) + 3) // 4
    scaled = [t.resize((cell, round(t.height * cell / t.width))) for t in thumbs]
    row_h = [max(s.height for s in scaled[r * 4:r * 4 + 4]) for r in range(rows)]
    sheet = Image.new("RGB", (cell * 4 + 50, sum(row_h) + 10 * (rows + 1)), (40, 40, 40))
    y = 10
    for r in range(rows):
        for c, s in enumerate(scaled[r * 4:r * 4 + 4]):
            sheet.paste(s, (10 + c * (cell + 10), y))
        y += row_h[r] + 10
    sheet.save(os.path.join(args.out, "all.png"))


if __name__ == "__main__":
    main()
