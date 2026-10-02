#!/usr/bin/env python3
"""Dump fixed-stride record tables that store Shift-JIS names.

Two such tables are known:

  RPDATA.CIM  monsters   stride 42, name at record offset 0, from file offset 0
  SDATA.CIM   characters stride 33, name at record offset 0, from file offset 0x1372

Output is TSV: index, byte offset, name, remaining record bytes as hex.
"""
from __future__ import annotations

import argparse
import csv
import sys

TABLES = {
    "RPDATA.CIM": dict(start=0x0000, stride=42, name_len=16),
    "SDATA.CIM": dict(start=0x1372, stride=33, name_len=16),
}


def decode_name(raw: bytes) -> str:
    raw = raw.split(b"\x00")[0]
    try:
        return raw.decode("cp932")
    except UnicodeDecodeError:
        return raw.decode("cp932", errors="replace")


def dump(path: str, start: int, stride: int, name_len: int, out):
    data = open(path, "rb").read()
    writer = csv.writer(out, delimiter="\t", lineterminator="\n")
    writer.writerow(["index", "offset", "name_ja", "name_zh", "record_hex"])
    index = 0
    off = start
    while off + stride <= len(data):
        rec = data[off:off + stride]
        name = decode_name(rec[:name_len])
        if not name:
            break
        writer.writerow([index, f"0x{off:04x}", name, "", rec[name_len:].hex()])
        index += 1
        off += stride
    return index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--table", choices=sorted(TABLES), help="use a known layout")
    ap.add_argument("--start", type=lambda s: int(s, 0), default=0)
    ap.add_argument("--stride", type=int)
    ap.add_argument("--name-len", type=int, default=16)
    ap.add_argument("--out", help="write TSV here instead of stdout")
    args = ap.parse_args()

    cfg = dict(TABLES[args.table]) if args.table else {}
    cfg.setdefault("start", args.start)
    cfg.setdefault("name_len", args.name_len)
    if args.stride:
        cfg["stride"] = args.stride
    if "stride" not in cfg:
        ap.error("--stride is required unless --table is given")

    out = open(args.out, "w", encoding="utf-8") if args.out else sys.stdout
    n = dump(args.file, cfg["start"], cfg["stride"], cfg["name_len"], out)
    if args.out:
        out.close()
    print(f"{args.file}: {n} records", file=sys.stderr)


if __name__ == "__main__":
    main()
