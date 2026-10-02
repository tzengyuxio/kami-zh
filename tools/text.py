#!/usr/bin/env python3
"""Extract translatable game text into TSV work files.

The game stores text three different ways:

  EVENT.DAT    story dialogue, Shift-JIS with every byte XOR'd by 0x77
  MAIN.EXE     UI and system messages, plain Shift-JIS
  *.CIM        name tables, plain Shift-JIS in fixed-stride records

Output columns are: id, offset, byte length, original, translation.
`max_bytes` is the hard limit a translation must respect when written back
in place -- Shift-JIS costs 2 bytes per kanji or kana, same as the original.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata

EVENT_XOR = 0x77


def sjis_runs(data: bytes, min_chars: int):
    """Yield (offset, byte_length, text) for every decodable Shift-JIS run."""
    runs = []
    i, n = 0, len(data)
    while i < n:
        start, chars = i, []
        while i < n:
            b = data[i]
            if (0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEF) and i + 1 < n:
                try:
                    ch = data[i:i + 2].decode("cp932")
                except UnicodeDecodeError:
                    break
                if unicodedata.category(ch).startswith("C"):
                    break
                chars.append(ch)
                i += 2
            elif 0xA1 <= b <= 0xDF:
                chars.append(bytes([b]).decode("cp932"))
                i += 1
            elif 0x20 <= b <= 0x7E:
                chars.append(chr(b))
                i += 1
            else:
                break
        if len(chars) >= min_chars:
            runs.append((start, i - start, "".join(chars)))
        if i == start:
            i += 1
    return runs


JP_PUNCT = "「」『』、。・ー～　！？…（）"

# The only ASCII that legitimately appears inside game text: printf format
# specifiers and the C<digit> colour-change codes.
MARKUP = re.compile(r"%[-0-9.]*[sudxXc]|C[0-9]")


def japanese_count(text: str) -> int:
    return sum(
        1 for c in text
        if 0x3040 <= ord(c) <= 0x30FF or 0x4E00 <= ord(c) <= 0x9FFF
    )


def looks_like_text(text: str) -> bool:
    """Reject runs that decode by accident out of code or graphics data.

    Real text in this game is fullwidth Japanese plus ASCII (printf formats
    and the C6/C7 colour codes). Accidental runs are riddled with halfwidth
    katakana, so a single one is enough to drop the run.
    """
    for c in text:
        cp = ord(c)
        if 0xFF61 <= cp <= 0xFF9F:          # halfwidth katakana -> noise
            return False
        ok = (
            0x3040 <= cp <= 0x30FF          # kana
            or 0x4E00 <= cp <= 0x9FFF       # kanji
            or 0xFF01 <= cp <= 0xFF5E       # fullwidth ASCII
            or 0x20 <= cp <= 0x7E           # ASCII
            or c in JP_PUNCT
        )
        if not ok:
            return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--xor", type=lambda s: int(s, 0), default=0,
                    help=f"XOR key; use 0x{EVENT_XOR:02x} for EVENT.DAT")
    ap.add_argument("--min-chars", type=int, default=4)
    ap.add_argument("--min-japanese", type=int, default=2,
                    help="drop runs with fewer than this many kana/kanji")
    ap.add_argument("--start", type=lambda s: int(s, 0), default=0,
                    help="only scan from this file offset "
                         "(the EXEs keep their string table in one region)")
    ap.add_argument("--end", type=lambda s: int(s, 0),
                    help="only scan up to this file offset")
    ap.add_argument("--out", help="write TSV here instead of stdout")
    args = ap.parse_args()

    data = open(args.file, "rb").read()
    if args.xor:
        data = bytes(b ^ args.xor for b in data)
    base = args.start
    data = data[args.start:args.end]

    runs = [r for r in sjis_runs(data, args.min_chars)
            if japanese_count(r[2]) >= args.min_japanese and looks_like_text(r[2])]

    out = open(args.out, "w", encoding="utf-8") if args.out else sys.stdout
    w = csv.writer(out, delimiter="\t", lineterminator="\n")
    w.writerow(["id", "offset", "max_bytes", "original_ja", "translation_zh"])
    for i, (off, length, text) in enumerate(runs):
        w.writerow([i, f"0x{base + off:06x}", length, text, ""])
    if args.out:
        out.close()
    print(f"{args.file}: {len(runs)} strings, "
          f"{sum(len(t) for _, _, t in runs)} characters", file=sys.stderr)


if __name__ == "__main__":
    main()
