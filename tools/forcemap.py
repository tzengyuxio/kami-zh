#!/usr/bin/env python3
"""Render the 勢力地図 (the village screen's territory map) with village names.

    .venv/bin/python tools/forcemap.py build/maps

Writes force_ja.png and force_zh.png: the map background (GRAPH.NPK #3)
with every territory filled (neighbours never share a colour) and labelled
in a 16-dot pixel font, then scaled up 4x in total without smoothing. The font is
DotGothic16 (SIL OFL), fetched once into build/fonts/:

    curl -sL -o build/fonts/DotGothic16-Regular.ttf \
      https://github.com/google/fonts/raw/main/ofl/dotgothic16/DotGothic16-Regular.ttf

FORCEGRP.DAT starts with one 1bpp mask per territory, in village order with
クマソ last, packed back to back (MSB = leftmost pixel). Their placement is
not stored anywhere found; the positions below were measured by matching the
masks against a screenshot (screen origin of the map: 248,72). Format notes:
docs/formats.md, "勢力地圖".
"""
from __future__ import annotations

import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import npk  # noqa: E402
import palette  # noqa: E402
import worldmap  # noqa: E402

BACKGROUND = 3   # GRAPH.NPK chunk: 312 x 320
PRE, POST = 2, 2   # labels go on the 2x map, then everything doubles again
FONT = "build/fonts/DotGothic16-Regular.ttf"
COLOURS = [(217, 162, 95), (143, 181, 115), (111, 163, 199), (201, 123, 132),
           (163, 139, 196), (212, 196, 106), (108, 181, 168)]
# (x, y, width in bytes, height) per territory, village order, クマソ last.
MASKS = [
    (0, 205, 9, 69), (48, 238, 7, 68), (80, 237, 11, 74), (112, 209, 7, 49),
    (152, 212, 8, 56), (160, 255, 8, 51), (208, 243, 8, 69), (264, 213, 6, 99),
    (240, 174, 6, 95), (200, 175, 6, 67), (176, 165, 5, 61), (248, 115, 5, 63),
    (256, 30, 7, 92), (216, 110, 5, 78), (224, 57, 5, 57), (152, 104, 9, 68),
    (200, 49, 4, 64), (168, 69, 5, 55), (248, 14, 5, 78), (208, 5, 6, 51),
    (184, 10, 4, 58), (144, 4, 6, 68), (120, 10, 5, 57), (96, 47, 8, 51),
    (96, 94, 5, 46), (64, 115, 8, 68), (8, 136, 9, 57), (56, 77, 6, 62),
    (80, 15, 6, 61), (40, 30, 7, 62),
]


def main_body(mask: Image.Image) -> Image.Image:
    """Keep the largest 4-connected part. クマソ's mask carries a thin strip
    at its right edge, over and beside イト; in the game both are green, so
    it never shows, but with distinct colours it looks like a stray patch."""
    w, h = mask.size
    px = mask.load()
    seen: set[tuple[int, int]] = set()
    best: list[tuple[int, int]] = []
    for sy in range(h):
        for sx in range(w):
            if not px[sx, sy] or (sx, sy) in seen:
                continue
            part, stack = [], [(sx, sy)]
            seen.add((sx, sy))
            while stack:
                x, y = stack.pop()
                part.append((x, y))
                for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= q[0] < w and 0 <= q[1] < h and px[q] and q not in seen:
                        seen.add(q)
                        stack.append(q)
            if len(part) > len(best):
                best = part
    out = Image.new("1", mask.size)
    for p in best:
        out.putpixel(p, 1)
    return out


def masks(data: bytes) -> list[tuple[int, int, Image.Image]]:
    out, off = [], 0
    for x, y, wb, h in MASKS:
        im = Image.frombytes("1", (wb * 8, h), data[off:off + wb * h])
        out.append((x, y, main_body(im)))
        off += wb * h
    return out


def colouring(regions: list[tuple[int, int, Image.Image]]) -> list[int]:
    """Greedy colour choice so that touching territories differ."""
    size = (312, 320)
    owner = {}
    for k, (x, y, m) in enumerate(regions):
        px = m.load()
        for j in range(m.height):
            for i in range(m.width):
                if px[i, j]:
                    owner[(x + i, y + j)] = k
    near: dict[int, set[int]] = {k: set() for k in range(len(regions))}
    for (x, y), k in owner.items():
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                o = owner.get((x + dx, y + dy))
                if o is not None and o != k and 0 <= x + dx < size[0]:
                    near[k].add(o)
    chosen: list[int] = []
    for k in range(len(regions)):
        used = {chosen[o] for o in near[k] if o < k}
        free = [c for c in range(len(COLOURS)) if c not in used]
        chosen.append(min(free, key=lambda c: chosen.count(c)))
    return chosen


def centre(x: int, y: int, mask: Image.Image) -> tuple[int, int]:
    """A point inside the mask near its middle, for the label."""
    px = mask.load()
    pts = [(i, j) for j in range(mask.height) for i in range(mask.width) if px[i, j]]
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    i, j = min(pts, key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)
    return x + i, y + j


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("out", help="output directory")
    ap.add_argument("--game", default="game/KAMI")
    ap.add_argument("--build", default="build/KAMI")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    graph = worldmap.read(os.path.join(args.game, "GRAPH.NPK"))
    chunk = npk.read_archive(graph)[BACKGROUND]
    bg = Image.frombytes("P", (chunk.width, chunk.height),
                         npk.unpack(chunk.payload, chunk.width, chunk.height))
    pal = [c for rgb in palette.palette("field") for c in rgb]
    bg.putpalette(pal + [0] * (768 - len(pal)))
    bg = bg.convert("RGBA")

    regions = masks(worldmap.read(os.path.join(args.game, "FORCEGRP.DAT")))
    base = bg.convert("RGB")
    for k, c in enumerate(colouring(regions)):
        x, y, m = regions[k]
        base.paste(Image.new("RGB", m.size, COLOURS[c]), (x, y), m)

    _, ja = worldmap.territories(args.game)
    names = {"ja": ja, "zh": worldmap.zh_names(args.build, ja)}
    spots = [centre(x, y, m) for x, y, m in regions]
    font = ImageFont.truetype(FONT, 16)
    base = base.resize((base.width * PRE, base.height * PRE), Image.NEAREST)
    for lang, label in names.items():
        im = base.copy()
        draw = ImageDraw.Draw(im)
        draw.fontmode = "1"   # no anti-aliasing: keep the dots
        for k, (x, y) in enumerate(spots):
            text = label[k]
            w = round(draw.textlength(text, font=font))
            left = min(max(x * PRE - w // 2, 2), im.width - w - 3)
            top = y * PRE - 8
            for dx in (-1, 0, 1):          # 1-dot dark outline, no box
                for dy in (-1, 0, 1):
                    draw.text((left + dx, top + dy), text, font=font, fill=(30, 15, 10))
            draw.text((left, top), text, font=font, fill=(255, 250, 235))
        im = im.resize((im.width * POST, im.height * POST), Image.NEAREST)
        im.save(os.path.join(args.out, f"force_{lang}.png"))


if __name__ == "__main__":
    main()
