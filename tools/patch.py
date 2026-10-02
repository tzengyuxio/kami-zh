#!/usr/bin/env python3
"""Write translations from a TSV back into a game file.

Translations are encoded as Shift-JIS (cp932), so every character must exist
in JIS X 0208 -- that is the whole point of the project's "keep the original
encoding" constraint. `check` reports what would fail; `apply` writes the
patched file.

Strings in this game are NUL-terminated, so a translation shorter than the
original is fine: we write it followed by a NUL and leave the rest alone.
A translation that is exactly as long as the original needs no NUL -- the
original's own terminator already sits just past max_bytes.
"""
from __future__ import annotations

import argparse
import csv
import os
import shutil
import sys


def load(tsv: str) -> list[dict]:
    with open(tsv, encoding="utf-8") as f:
        return [r for r in csv.DictReader(f, delimiter="\t")
                if r.get("translation_zh", "").strip()]


def encode(text: str) -> tuple[bytes | None, list[str]]:
    """Encode to Shift-JIS, reporting characters JIS X 0208 cannot represent."""
    missing = []
    for ch in text:
        try:
            ch.encode("cp932")
        except UnicodeEncodeError:
            missing.append(ch)
    if missing:
        return None, missing
    return text.encode("cp932"), []


def check(rows: list[dict]) -> list[str]:
    problems = []
    for r in rows:
        raw, missing = encode(r["translation_zh"])
        if missing:
            problems.append(
                f"[{r['id']}] {r['translation_zh']!r}: "
                f"不在 JIS X 0208 內的字: {' '.join(missing)}")
            continue
        limit = int(r["max_bytes"])
        if len(raw) > limit:
            problems.append(
                f"[{r['id']}] {r['translation_zh']!r}: "
                f"{len(raw)} bytes 超過上限 {limit}")
    return problems


def apply(rows: list[dict], target: str, out: str, xor: int) -> int:
    data = bytearray(open(target, "rb").read())
    for r in rows:
        raw, missing = encode(r["translation_zh"])
        if missing:
            raise SystemExit(f"[{r['id']}] 無法編碼: {' '.join(missing)}")
        limit = int(r["max_bytes"])
        if len(raw) > limit:
            raise SystemExit(f"[{r['id']}] {len(raw)} bytes 超過上限 {limit}")
        payload = raw if len(raw) == limit else raw + b"\x00"
        if xor:
            payload = bytes(b ^ xor for b in payload)
        off = int(r["offset"], 16)
        data[off:off + len(payload)] = payload
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    open(out, "wb").write(bytes(data))
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["check", "apply"])
    ap.add_argument("--tsv", required=True)
    ap.add_argument("--target", help="original game file (apply only)")
    ap.add_argument("--out", help="where to write the patched file")
    ap.add_argument("--xor", type=lambda s: int(s, 0), default=0)
    args = ap.parse_args()

    rows = load(args.tsv)
    problems = check(rows)
    for p in problems:
        print("  " + p, file=sys.stderr)
    if args.action == "check":
        print(f"{args.tsv}: {len(rows)} 筆譯文, {len(problems)} 筆有問題")
        return
    if problems:
        raise SystemExit("有問題的譯文，請先修正")
    if not args.target or not args.out:
        raise SystemExit("apply 需要 --target 與 --out")
    n = apply(rows, args.target, args.out, args.xor)
    print(f"{args.out}: 套用 {n} 筆譯文")


if __name__ == "__main__":
    main()
