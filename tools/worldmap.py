#!/usr/bin/env python3
"""Render the world map, label the villages, and list which villages border.

    .venv/bin/python tools/worldmap.py build/maps            # ja + zh maps
    .venv/bin/python tools/worldmap.py build/maps --adjacency  # also print table

Sources (docs/formats.md section "World map"):

  AMAPDATA.DAT   90 x 60 metatile codes, row-major
  MAIN.EXE       0x45700: 190 metatiles x 4 AMAPGRP tile numbers (TL TR BL BR)
  AMAPGRP.DAT    209 tiles, 16x16, 3bpp, one whole plane after another;
                 drawn with colour = 8 + value
  SDATA.CIM      0x3640: 5400 x 5-byte cell records; +1 u16 links the cells
                 of one territory into a chain, the chain head is the u16 at
                 +9 of the village record (0x92 + 29*v). The one chain no
                 village record points at belongs to クマソ.

Village names come from game/ (Japanese) and build/ (translated). Villages
border when their territories share a cell edge; the manual allows moving
people and supplies only between bordering villages.
"""
from __future__ import annotations

import argparse
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import palette  # noqa: E402

W, H = 90, 60
METATILES = 0x45700
VILLAGES, VILLAGE_SIZE, VILLAGE_COUNT = 0x92, 29, 29
CELLS = 0x3640
VILLAGE_CODE = 5  # metatile with the village gate
EXTRA = ("クマソ", "熊曾")  # the 30th territory, not in the village table
# Where the player can walk, as observed in the game (both ways). Not stored
# anywhere found; the border-sharing table from --adjacency is wider.
ROUTES = """
出雲-黄泉比良坂 出雲-多藝志 多藝志-須賀 須賀-稻羽 須賀-吉備 稻羽-但馬 吉備-但馬 吉備-三輪
三輪-熊野 三輪-三輪山 熊野-阿波見 阿波見-伊吹 阿波見-山城 阿波見-美濃 伊吹-尾張 尾張-燒津
燒津-相模 相模-新治 新治-沼河 沼河-越 沼河-須佐 沼河-生贄洞窟 越-科野 越-和奈美 科野-山城
科野-美濃 山城-相樂 相樂-和奈美 須佐-穴門 須佐-須佐沼 穴門-筑紫 筑紫-阿多 阿多-日向
日向-隼人 日向-高千穗岳 隼人-宇佐 宇佐-伊都 伊都-熊曾
血沼-死靈祭壇 死靈祭壇-邪馬 邪馬-邪馬神殿
""".split()
# Routes that only open for a while: closed once the event there is over,
# or reached by talking to someone in the village (by boat), not by walking.
CLOSED_LATER = ["稻羽-山賊洞窟", "伊吹-伊吹山"]
BY_DIALOGUE = ["吉備-鬼之島", "和奈美-海賊之島"]
# Map cells of the places on ROUTES that are not villages: cave entrances
# (metatile 4) next to the village that leads there, and the four buildings
# of the mist continent, village / dungeon / village / dungeon from top to
# bottom (order confirmed in the game).
SITES = {"黄泉比良坂": (22, 41), "三輪山": (75, 52), "生贄洞窟": (59, 8), "須佐沼": (50, 9),
         "高千穗岳": (27, 26), "山賊洞窟": (44, 46), "伊吹山": (60, 44), "鬼之島": (51, 56),
         "海賊之島": (80, 6), "血沼": (5, 8), "死靈祭壇": (3, 12), "邪馬": (4, 15),
         "邪馬神殿": (6, 18)}

FONTS = {
    "ja": "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "zh": os.path.expanduser("~/.local/share/fonts/STHeiti Medium.ttc"),
}


def read(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def tile(grp: bytes, t: int) -> Image.Image:
    c = grp[t * 96:(t + 1) * 96]
    px = bytearray(256)
    for i in range(256):
        v = 0
        for p in range(3):
            v |= ((c[p * 32 + i // 8] >> (7 - i % 8)) & 1) << p
        px[i] = 8 + v
    return Image.frombytes("P", (16, 16), bytes(px))


def render(game: str) -> Image.Image:
    amap = read(os.path.join(game, "AMAPDATA.DAT"))
    grp = read(os.path.join(game, "AMAPGRP.DAT"))
    exe = read(os.path.join(game, "MAIN.EXE"))
    tiles = [tile(grp, t) for t in range(len(grp) // 96)]
    pal = [c for rgb in palette.palette("field") for c in rgb]
    im = Image.new("P", (W * 32, H * 32))
    im.putpalette(pal + [0] * (768 - len(pal)))
    for i, code in enumerate(amap):
        meta = exe[METATILES + 4 * code:METATILES + 4 * code + 4]
        x, y = (i % W) * 32, (i // W) * 32
        for k, t in enumerate(meta):
            im.paste(tiles[t], (x + (k & 1) * 16, y + (k >> 1) * 16))
    return im.convert("RGB")


def territories(game: str) -> tuple[list[int], list[str]]:
    """Owner of every cell (-1 = none) and the Japanese village names."""
    sdata = read(os.path.join(game, "SDATA.CIM"))
    link = [sdata[CELLS + 5 * i + 1] | sdata[CELLS + 5 * i + 2] << 8 for i in range(W * H)]
    owner = [-1] * (W * H)
    names = []
    for v in range(VILLAGE_COUNT):
        rec = sdata[VILLAGES + v * VILLAGE_SIZE:VILLAGES + (v + 1) * VILLAGE_SIZE]
        names.append(rec[:9].rstrip(b"\0").decode("cp932"))
        c = rec[9] | rec[10] << 8
        while c < W * H and owner[c] < 0:
            owner[c] = v
            c = link[c]
    linked = set(l for l in link if l < W * H)
    for i in range(W * H):
        if owner[i] < 0 and (link[i] < W * H or i in linked):
            owner[i] = VILLAGE_COUNT
    names.append(EXTRA[0])
    return owner, names


def adjacency(owner: list[int]) -> dict[int, set[int]]:
    adj: dict[int, set[int]] = {}
    for i, a in enumerate(owner):
        x, y = i % W, i // W
        for j in ([i + 1] if x < W - 1 else []) + ([i + W] if y < H - 1 else []):
            b = owner[j]
            if a >= 0 and b >= 0 and a != b:
                adj.setdefault(a, set()).add(b)
                adj.setdefault(b, set()).add(a)
    return adj


def zh_names(build: str, ja: list[str]) -> list[str]:
    sdata = read(os.path.join(build, "SDATA.CIM"))
    out = [sdata[VILLAGES + v * VILLAGE_SIZE:VILLAGES + v * VILLAGE_SIZE + 9]
           .rstrip(b"\0").decode("cp932") for v in range(VILLAGE_COUNT)]
    return out + [EXTRA[1]]


def label(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str,
          font: ImageFont.FreeTypeFont) -> None:
    x, y = xy
    box = draw.textbbox((0, 0), text, font=font)
    w, h = box[2] - box[0], box[3] - box[1]
    left, top = x - w // 2 - 6, y + 20
    draw.rounded_rectangle((left, top, left + w + 12, top + h + 10), 6,
                           fill=(255, 250, 235), outline=(90, 40, 20), width=2)
    draw.text((left + 6 - box[0], top + 5 - box[1]), text, font=font, fill=(60, 20, 10))


def dashed(draw: ImageDraw.ImageDraw, a: tuple[int, int], b: tuple[int, int],
           fill, dash: tuple[int, int], width: int = 7) -> None:
    length = math.dist(a, b)
    step = sum(dash)
    for k in range(int(length // step) + 1):
        t0, t1 = k * step / length, min((k * step + dash[0]) / length, 1)
        draw.line((a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0,
                   a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1), fill=fill, width=width)


def legend(draw: ImageDraw.ImageDraw, font) -> None:
    """Key for the route lines, bottom left."""
    x, y = 30, H * 32 - 170
    draw.rectangle((x - 14, y - 14, x + 560, y + 136), fill=(20, 30, 50), outline=(255, 255, 255))
    rows = [((255, 255, 255), None, "可走的路線"),
            ((255, 255, 255), (18, 12), "事件解決後無法前往"),
            ((0, 210, 255), (10, 8), "在村內對話前往（搭船，不經大地圖）")]
    for k, (colour, dash, text) in enumerate(rows):
        ly = y + 20 + k * 44
        if dash:
            dashed(draw, (x, ly), (x + 90, ly), colour, dash)
        else:
            draw.line((x, ly, x + 90, ly), fill=colour, width=5)
        draw.text((x + 110, ly - 17), text, font=font, fill=(255, 255, 255))


def villages(amap: bytes, owner: list[int]) -> dict[int, tuple[int, int]]:
    """Pixel centre of each village's gate metatile."""
    return {owner[i]: ((i % W) * 32 + 16, (i // W) * 32 + 16)
            for i, c in enumerate(amap) if c == VILLAGE_CODE and owner[i] >= 0}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("out", help="output directory")
    ap.add_argument("--game", default="game/KAMI")
    ap.add_argument("--build", default="build/KAMI")
    ap.add_argument("--adjacency", action="store_true", help="print the border table")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    base = render(args.game)
    owner, ja = territories(args.game)
    zh = zh_names(args.build, ja)
    pos = villages(read(os.path.join(args.game, "AMAPDATA.DAT")), owner)
    adj = adjacency(owner)

    base.save(os.path.join(args.out, "world.png"))
    for lang, names in (("ja", ja), ("zh", zh)):
        font = ImageFont.truetype(FONTS[lang], 26)
        im = base.copy()
        draw = ImageDraw.Draw(im)
        for v, xy in sorted(pos.items()):
            label(draw, xy, names[v], font)
        im.save(os.path.join(args.out, f"world_{lang}.png"))

    # Territories tinted over the map, with a line between bordering villages.
    hues = [(230, 25, 75), (60, 180, 75), (255, 225, 25), (0, 130, 200),
            (245, 130, 48), (145, 30, 180), (70, 240, 240), (240, 50, 230),
            (210, 245, 60), (250, 190, 212), (0, 128, 128), (220, 190, 255)]
    tint = Image.new("RGBA", base.size)
    td = ImageDraw.Draw(tint)
    for i, v in enumerate(owner):
        if v >= 0:
            x, y = (i % W) * 32, (i // W) * 32
            td.rectangle((x, y, x + 31, y + 31), fill=hues[v % len(hues)] + (90,))
    for i, v in enumerate(owner):
        x, y = (i % W) * 32, (i // W) * 32
        if v >= 0 and (i % W == W - 1 or owner[i + 1] != v):
            td.line((x + 31, y, x + 31, y + 31), fill=(0, 0, 0, 255), width=3)
        if v >= 0 and (i // W == H - 1 or owner[i + W] != v):
            td.line((x, y + 31, x + 31, y + 31), fill=(0, 0, 0, 255), width=3)
        if v >= 0 and (i % W == 0 or owner[i - 1] != v):
            td.line((x, y, x, y + 31), fill=(0, 0, 0, 255), width=3)
        if v >= 0 and (i // W == 0 or owner[i - W] != v):
            td.line((x, y, x + 31, y), fill=(0, 0, 0, 255), width=3)
    where = {zh[v]: xy for v, xy in pos.items()}
    where.update({n: (x * 32 + 16, y * 32 + 16) for n, (x, y) in SITES.items()})
    for route in ROUTES:
        a, b = route.split("-")
        td.line(where[a] + where[b], fill=(255, 255, 255, 230), width=5)
    for routes, colour, dash in ((CLOSED_LATER, (255, 255, 255, 230), (18, 12)),
                                 (BY_DIALOGUE, (0, 210, 255, 255), (10, 8))):
        for route in routes:
            a, b = route.split("-")
            dashed(td, where[a], where[b], colour, dash)
    im = Image.alpha_composite(base.convert("RGBA"), tint).convert("RGB")
    draw = ImageDraw.Draw(im)
    font = ImageFont.truetype(FONTS["zh"], 26)
    for name, (x, y) in where.items():
        if name in SITES and name not in ("血沼", "邪馬"):
            draw.polygon(((x, y - 11), (x + 11, y), (x, y + 11), (x - 11, y)),
                         fill=(255, 220, 120), outline=(0, 0, 0), width=3)
        else:
            draw.ellipse((x - 8, y - 8, x + 8, y + 8), fill=(255, 255, 255),
                         outline=(0, 0, 0), width=3)
        label(draw, (x, y), name, font)
    legend(draw, font)
    im.save(os.path.join(args.out, "territory_zh.png"))

    if args.adjacency:
        for v in range(len(ja)):
            print(f"{v:2d} {zh[v]}（{ja[v]}）: " + "、".join(zh[b] for b in sorted(adj.get(v, ()))))


if __name__ == "__main__":
    main()
