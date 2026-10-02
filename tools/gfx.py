#!/usr/bin/env python3
"""Export NPK016 archives to PNG.

Images are written as indexed-color (mode "P") PNGs so the 16-entry palette
can be swapped later without re-decoding. Pass --palette to supply a real
palette; without it a visually distinct placeholder ramp is used.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import npk

# Standard EGA/VGA 16-colour palette: good enough to judge image structure
# before the real palette is located.
PLACEHOLDER = [
    (0x00, 0x00, 0x00), (0x00, 0x00, 0xAA), (0x00, 0xAA, 0x00), (0x00, 0xAA, 0xAA),
    (0xAA, 0x00, 0x00), (0xAA, 0x00, 0xAA), (0xAA, 0x55, 0x00), (0xAA, 0xAA, 0xAA),
    (0x55, 0x55, 0x55), (0x55, 0x55, 0xFF), (0x55, 0xFF, 0x55), (0x55, 0xFF, 0xFF),
    (0xFF, 0x55, 0x55), (0xFF, 0x55, 0xFF), (0xFF, 0xFF, 0x55), (0xFF, 0xFF, 0xFF),
]


def to_image(pixels: bytes, width: int, height: int, palette: list) -> Image.Image:
    img = Image.frombytes("P", (width, height), pixels.ljust(width * height, b"\x00"))
    flat = []
    for rgb in palette:
        flat.extend(rgb)
    img.putpalette(flat + [0] * (768 - len(flat)))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--out-dir", default="extracted/gfx")
    ap.add_argument("--palette", help="JSON file with 16 [r,g,b] entries")
    args = ap.parse_args()

    palette = PLACEHOLDER
    if args.palette:
        palette = [tuple(c) for c in json.load(open(args.palette))]

    data = open(args.file, "rb").read()
    chunks = npk.read_archive(data) or npk.scan_archive(data)
    stem = os.path.splitext(os.path.basename(args.file))[0]
    out_dir = os.path.join(args.out_dir, stem)
    os.makedirs(out_dir, exist_ok=True)

    for c in chunks:
        px = npk.unpack(c.payload, c.width, c.height)
        img = to_image(px, c.width, c.height, palette)
        name = f"{stem}_{c.index:03d}_{c.width}x{c.height}.png"
        img.save(os.path.join(out_dir, name))
    print(f"{stem}: wrote {len(chunks)} PNGs to {out_dir}")


if __name__ == "__main__":
    main()
