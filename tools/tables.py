#!/usr/bin/env python3
"""Read and write the fixed-stride record tables that store Shift-JIS names.

Two such tables are known:

  RPDATA.CIM  monsters   stride 42, 70 records, from file offset 0
  SDATA.CIM   characters stride 33, 150 records, from file offset 0x1372

In both, the name occupies the first 15 bytes of the record, NUL-padded, and
the record's numeric data starts at offset 15 -- so a replacement name may be
at most 14 bytes (7 fullwidth characters).

`dump` writes TSV; `apply` writes glossary names back into a copy of the file.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jis

NAME_FIELD = 15          # bytes reserved for the name, NUL-padded
MAX_NAME = NAME_FIELD - 1   # one byte must stay for the terminator

TABLES = {
    "RPDATA.CIM": dict(start=0x0000, stride=42, count=70, kind="monster"),
    "SDATA.CIM": dict(start=0x1372, stride=33, count=150, kind="person"),
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


def apply_glossary(path: str, table: str, glossary: str, out_path: str) -> int:
    cfg = TABLES[table]
    data = bytearray(open(path, "rb").read())
    wanted = {}
    for row in csv.DictReader(open(glossary, encoding="utf-8"), delimiter="\t"):
        if row["kind"] == cfg["kind"] and row["zh"].strip():
            wanted[int(row["index"])] = row["zh"].strip()

    written = 0
    for index, name in sorted(wanted.items()):
        if index >= cfg["count"]:
            raise SystemExit(f"{table}: index {index} 超出 {cfg['count']} 筆")
        bad = jis.missing(name)
        if bad:
            raise SystemExit(f"{table}[{index}] {name}: " + jis.advise(bad))
        raw = name.encode("cp932")
        if len(raw) > MAX_NAME:
            raise SystemExit(
                f"{table}[{index}] {name}: {len(raw)} bytes 超過欄位 {MAX_NAME}")
        off = cfg["start"] + index * cfg["stride"]
        data[off:off + NAME_FIELD] = raw.ljust(NAME_FIELD, b"\x00")
        written += 1

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    open(out_path, "wb").write(bytes(data))
    return written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--table", choices=sorted(TABLES), required=True)
    ap.add_argument("--out", help="dump: TSV path; apply: patched file path")
    ap.add_argument("--glossary", help="apply glossary names instead of dumping")
    args = ap.parse_args()

    cfg = TABLES[args.table]
    if args.glossary:
        if not args.out:
            ap.error("apply 需要 --out")
        n = apply_glossary(args.file, args.table, args.glossary, args.out)
        print(f"{args.out}: 套用 {n} 個名稱")
        return

    out = open(args.out, "w", encoding="utf-8") if args.out else sys.stdout
    n = dump(args.file, cfg["start"], cfg["stride"], NAME_FIELD, out)
    if args.out:
        out.close()
    print(f"{args.file}: {n} records", file=sys.stderr)


if __name__ == "__main__":
    main()
