#!/usr/bin/env python3
"""KOEI NPK016 container reader.

Archive layout (e.g. GRAPH.NPK, BIG.DAT, UNIT.DAT, OPENGRP.DAT):

    u32[n]      offset table; n = offsets[0] / 4
    blob[n]     each blob is an "NPK016" chunk

NPK016 chunk layout (14-byte header, verified: the stream decodes to
exactly width * height pixels and consumes the payload exactly):

    +0x00  char[6]  "NPK016"
    +0x06  u16      bit planes (always 4 -> 16 colors)
    +0x08  u16      width in pixels
    +0x0a  u16      height in pixels
    +0x0c  u16      chunk size, including this 14-byte header
    +0x0e  ...      bit-flagged RLE stream, decodes to one index byte per pixel

The palette is NOT stored in the chunk; it lives elsewhere (MAIN.EXE).

Ported from https://github.com/tzengyuxio/kaodata (dekoei/utils.py).
"""
from __future__ import annotations

import io
import struct
import sys
from dataclasses import dataclass

MAGIC = b"NPK016"


HEADER_SIZE = 0x0E


@dataclass
class Chunk:
    index: int
    offset: int
    size: int
    planes: int
    width: int
    height: int
    declared_size: int
    payload: bytes


def conv_palette(v: int) -> tuple[int, int, int]:
    """16-bit GRB (4 bits per channel) -> 24-bit RGB."""
    b = (v >> 0) & 0x0F
    r = (v >> 4) & 0x0F
    g = (v >> 8) & 0x0F
    return (r * 0x11, g * 0x11, b * 0x11)


def read_chunk(data: bytes, offset: int, size: int, index: int = 0) -> Chunk | None:
    if data[offset:offset + 6] != MAGIC:
        return None
    planes, width, height, declared = struct.unpack_from("<4H", data, offset + 6)
    return Chunk(
        index=index,
        offset=offset,
        size=size,
        planes=planes,
        width=width,
        height=height,
        declared_size=declared,
        payload=data[offset + HEADER_SIZE:offset + size],
    )


def read_archive(data: bytes) -> list[Chunk]:
    """Read the u32 offset table and return every NPK016 chunk it points at."""
    first = struct.unpack_from("<I", data, 0)[0]
    if first == 0 or first % 4 != 0 or first > len(data):
        return []
    count = first // 4
    offsets = list(struct.unpack_from(f"<{count}I", data, 0))
    offsets.append(len(data))
    chunks = []
    for i in range(count):
        chunk = read_chunk(data, offsets[i], offsets[i + 1] - offsets[i], i)
        if chunk is not None:
            chunks.append(chunk)
    return chunks


def scan_archive(data: bytes) -> list[Chunk]:
    """Fallback: locate chunks by searching for the magic."""
    offsets = []
    pos = data.find(MAGIC)
    while pos != -1:
        offsets.append(pos)
        pos = data.find(MAGIC, pos + 1)
    offsets.append(len(data))
    return [
        c
        for i in range(len(offsets) - 1)
        if (c := read_chunk(data, offsets[i], offsets[i + 1] - offsets[i], i)) is not None
    ]


def unpack(src: bytes, line: int, height: int) -> bytes:
    """Decompress an NPK016 payload into one byte per pixel (4bpp index)."""
    data = io.BytesIO(src)
    dest = bytearray()
    bitflag = 0x0000
    data_len = len(src)
    dest_len = line * height
    while data.tell() < data_len and len(dest) < dest_len:
        if not (bitflag & 0xFF00):
            bitflag = 0xFF00 | data.read(1)[0]
        if bitflag & 1:
            # back-reference: repeat `run_size * 4` pixels from `run_offset` back
            b = data.read(1)[0]
            run_size = (b & 0x1F) + 1
            run_offset = ((b & 0x60) >> 5) + 1
            run_offset = run_offset * line if (b & 0x80) else run_offset * 4
            for _ in range(run_size * 4):
                dest.append(dest[-run_offset])
        else:
            # literal: 2 packed bytes -> 4 pixels, bit-planes interleaved
            pair = data.read(2)
            if len(pair) < 2:
                break
            b1, b2 = pair[0], pair[1]
            for _ in range(4):
                dest.append(
                    ((b1 & 0x80) >> 4) | ((b1 & 0x08) >> 1)
                    | ((b2 & 0x80) >> 6) | ((b2 & 0x08) >> 3)
                )
                b1 = (b1 << 1) & 0xFF
                b2 = (b2 << 1) & 0xFF
        bitflag >>= 1
    return bytes(dest)


def main():
    path = sys.argv[1]
    data = open(path, "rb").read()
    chunks = read_archive(data)
    how = "offset table"
    if not chunks:
        chunks = scan_archive(data)
        how = "magic scan"
    print(f"{path}: {len(chunks)} chunks via {how} ({len(data)} bytes)")
    for c in chunks:
        px = unpack(c.payload, c.width, c.height)
        want = c.width * c.height
        flag = "ok " if len(px) == want else "BAD"
        print(
            f"  [{c.index:03d}] off={c.offset:08x} size={c.size:7d} "
            f"(declared {c.declared_size:7d}) planes={c.planes} "
            f"{c.width:4d}x{c.height:4d} -> {flag} {len(px)}/{want} px"
        )


if __name__ == "__main__":
    main()
