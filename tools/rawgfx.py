#!/usr/bin/env python3
"""Render raw (uncompressed) planar graphics files.

FACEGRP.DAT / CHARA.DAT etc. carry no header, so width, height and bit depth
have to be supplied. Two bit layouts are supported:

  packed   - N bits per pixel, pixels stored consecutively (nibble pairs)
  rowplane - N separate 1bpp bit planes, one full row per plane
  chunky   - N bytes encode 8 pixels; byte k holds bit k of each pixel
             (KOEI's "8 pixels in N bytes" layout, LSB plane first)
"""
from __future__ import annotations

import argparse
import os

from PIL import Image

def gray_ramp(bpp: int) -> list[tuple[int, int, int]]:
    n = 1 << bpp
    return [(i * 255 // (n - 1),) * 3 for i in range(n)]


def decode_packed(data: bytes, bpp: int) -> list[int]:
    out = []
    if bpp == 4:
        for b in data:
            out.append(b >> 4)
            out.append(b & 0x0F)
    elif bpp == 8:
        out.extend(data)
    else:
        raise ValueError(bpp)
    return out


def decode_chunky(data: bytes, bpp: int) -> list[int]:
    """Every `bpp` bytes hold 8 pixels; byte k supplies bit k.

    The blitter at MAIN.EXE lin 0x1a4a writes byte 0 to VGA map mask 1,
    byte 1 to mask 2, byte 2 to mask 4 -- so byte k is plane k, LSB first.
    """
    out = []
    for base in range(0, len(data) - bpp + 1, bpp):
        for bit in range(7, -1, -1):
            v = 0
            for p in range(bpp):
                v |= ((data[base + p] >> bit) & 1) << p
            out.append(v)
    return out


def decode_rowplane(data: bytes, bpp: int, row_bytes: int) -> list[int]:
    """Row-interleaved planes: each row stores plane0..planeN-1 back to back."""
    out = []
    stride = row_bytes * bpp
    for base in range(0, len(data) - stride + 1, stride):
        for byte_i in range(row_bytes):
            for bit in range(7, -1, -1):
                v = 0
                for p in range(bpp):
                    v |= ((data[base + p * row_bytes + byte_i] >> bit) & 1) << (bpp - 1 - p)
                out.append(v)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--width", type=int, required=True)
    ap.add_argument("--height", type=int, required=True)
    ap.add_argument("--bpp", type=int, default=4)
    ap.add_argument("--layout", choices=["packed", "rowplane", "chunky"], default="chunky")
    ap.add_argument("--count", type=int, default=0, help="0 = as many as fit")
    ap.add_argument("--cols", type=int, default=8)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    data = open(args.file, "rb").read()
    tile_bytes = args.width * args.height * args.bpp // 8
    count = args.count or len(data) // tile_bytes

    palette = []
    for rgb in gray_ramp(args.bpp):
        palette.extend(rgb)
    palette += [0] * (768 - len(palette))

    cols = min(args.cols, count)
    rows = (count + cols - 1) // cols
    sheet = Image.new("P", (cols * args.width, rows * args.height))
    sheet.putpalette(palette)

    for i in range(count):
        chunk = data[i * tile_bytes:(i + 1) * tile_bytes]
        if args.layout == "packed":
            px = decode_packed(chunk, args.bpp)
        elif args.layout == "chunky":
            px = decode_chunky(chunk, args.bpp)
        else:
            px = decode_rowplane(chunk, args.bpp, args.width // 8)
        px = px[:args.width * args.height]
        px += [0] * (args.width * args.height - len(px))
        tile = Image.frombytes("P", (args.width, args.height), bytes(px))
        tile.putpalette(palette)
        sheet.paste(tile, ((i % cols) * args.width, (i // cols) * args.height))

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    sheet.save(args.out)
    print(f"{args.file}: {count} tiles {args.width}x{args.height} "
          f"{args.bpp}bpp {args.layout} -> {args.out}")


if __name__ == "__main__":
    main()
