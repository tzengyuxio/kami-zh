#!/usr/bin/env python3
"""Mark the game's 30 villages at their real places on a map of modern Japan.

    curl -sL -o build/geo/japan.geojson \
      https://raw.githubusercontent.com/dataofjapan/land/master/japan.geojson
    .venv/bin/python tools/japanmap.py build/maps/japan_zh.png
    .venv/bin/python tools/japanmap.py --routes build/maps/japan_zh_routes.png

The game's world map is not drawn to geography -- an affine fit of the
village gates to these places leaves ~650 px of error on a 2880 px map --
so the villages are placed by their real locations instead of warping
world.png. Places are approximate (shrine, old capital or town of the
name). 和奈美 (ワナミ, Kojiki 和那美之水門 in 高志国) has no agreed site;
it is put at 和南津 (Nagaoka, Niigata, on the Uono river), one proposed match.
"""
from __future__ import annotations

import argparse
import json
import math

from PIL import Image, ImageDraw, ImageFont

import worldmap

GEOJSON = "build/geo/japan.geojson"
LON, LAT = (129.3, 141.6), (30.9, 38.4)
WIDTH = 2400
# name -> (lat, lon)
PLACES = {
    "熊曾": (32.21, 130.76), "伊都": (33.56, 130.20), "筑紫": (33.52, 130.53),
    "宇佐": (33.53, 131.35), "日向": (31.91, 131.42), "阿多": (31.42, 130.32),
    "隼人": (31.74, 130.76), "出雲": (35.40, 132.69), "多藝志": (35.37, 132.75),
    "須賀": (35.30, 132.95), "稻羽": (35.50, 134.23), "但馬": (35.54, 134.82),
    "吉備": (34.66, 133.92), "三輪": (34.53, 135.85), "熊野": (33.72, 135.99),
    "阿波見": (35.00, 135.87), "伊吹": (35.42, 136.41), "尾張": (35.13, 136.91),
    "山城": (35.01, 135.77), "相樂": (34.74, 135.82), "美濃": (35.42, 136.76),
    "科野": (36.05, 138.11), "燒津": (34.87, 138.32), "穴門": (33.96, 130.94),
    "須佐": (34.63, 131.60), "沼河": (37.04, 137.86), "新治": (36.30, 140.10),
    "相模": (35.38, 139.38), "越": (36.69, 137.21), "和奈美": (37.27, 138.86),
}
# Label offsets (from the dot) where neighbours would overlap; default (13, -18).
LABEL_AT = {"出雲": (-90, -46), "多藝志": (-120, 6), "須賀": (14, 4), "山城": (-90, -20),
            "阿波見": (14, -2), "伊吹": (-80, -20), "美濃": (14, -20)}
# Colour = stage of the game the village belongs to.
STAGES = [
    ("初期南方村落（村莊順序多為單線往前或簡單分支）", (77, 146, 214),
     "出雲 多藝志 須賀 稻羽 但馬 吉備"),
    ("中期 1（勢力地圖東南方，開始有軍隊戰鬥，路線可自由選擇）", (92, 170, 92),
     "三輪 熊野 阿波見 伊吹 尾張 美濃 山城"),
    ("中期 2（勢力地圖北方與東北方）", (178, 112, 200),
     "燒津 相模 新治 科野 越 和奈美 相樂 沼河 須佐 穴門"),
    ("後期左上村落", (214, 96, 77), "筑紫 阿多 日向 隼人 宇佐 伊都 熊曾"),
]
SEAS = {"瀨戶內海": (34.28, 133.45)}
TITLE_FONT = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"   # kana sized to match kanji


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("out")
    ap.add_argument("--routes", action="store_true",
                    help="also draw the walkable routes between villages (worldmap.ROUTES)")
    args = ap.parse_args()
    stage = {name: k for k, (_, _, names) in enumerate(STAGES) for name in names.split()}

    k = math.cos(math.radians(sum(LAT) / 2))
    scale = WIDTH / ((LON[1] - LON[0]) * k)
    height = round((LAT[1] - LAT[0]) * scale)

    def xy(lat: float, lon: float) -> tuple[float, float]:
        return (lon - LON[0]) * k * scale, (LAT[1] - lat) * scale

    im = Image.new("RGB", (WIDTH, height), (170, 200, 225))
    draw = ImageDraw.Draw(im)
    for feature in json.load(open(GEOJSON, encoding="utf-8"))["features"]:
        geom = feature["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in polys:
            ring = [xy(lat, lon) for lon, lat in poly[0]]
            if len(ring) > 2:
                draw.polygon(ring, fill=(236, 230, 212), outline=(190, 180, 160))

    if args.routes:
        for route in worldmap.ROUTES:
            a, b = route.split("-")
            if a in PLACES and b in PLACES:
                draw.line(xy(*PLACES[a]) + xy(*PLACES[b]), fill=(90, 90, 90), width=4)
    font = ImageFont.truetype(worldmap.FONTS["zh"], 30)
    for name, (lat, lon) in PLACES.items():
        x, y = xy(lat, lon)
        colour = STAGES[stage[name]][1]
        draw.ellipse((x - 9, y - 9, x + 9, y + 9), fill=colour, outline=(40, 40, 40), width=2)
        text = name + ("？" if name == "和奈美" else "")
        dx, dy = LABEL_AT.get(name, (13, -18))
        draw.text((x + dx, y + dy), text, font=font, fill=(30, 30, 30),
                  stroke_width=4, stroke_fill=(255, 255, 255))

    sea = ImageFont.truetype(worldmap.FONTS["zh"], 34)
    for name, (lat, lon) in SEAS.items():
        x, y = xy(lat, lon)
        draw.text((x, y), name, font=sea, fill=(40, 80, 140), anchor="mm")
    big = ImageFont.truetype(TITLE_FONT, 44)
    draw.text((40, 30), "神々の大地：遊戲中的村落在現代日本的位置", font=big, fill=(30, 30, 30))
    for i, (text, colour, _) in enumerate(STAGES):
        y = 100 + i * 42
        draw.ellipse((44, y + 8, 64, y + 28), fill=colour, outline=(40, 40, 40), width=2)
        draw.text((76, y), text, font=font, fill=(30, 30, 30))
    draw.text((40, height - 60), "遊戲的大地圖不依實際地理比例；位置取神社、古都或同名地點，皆為概略。",
              font=font, fill=(60, 60, 60))
    im.save(args.out)


if __name__ == "__main__":
    main()
