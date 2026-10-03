#!/usr/bin/env python3
"""Normalise the glyph choice in translated text, in place.

Two passes, in this order:

  1. traditional preferred -- for characters where JIS X 0208 carries both
     the traditional form and the Japanese shinjitai, use the traditional one
  2. missing traditional   -- jis.SUBSTITUTES maps the other direction, for
     characters JIS has only as shinjitai; those always win

Only the translation column is touched. Both forms are two bytes, so nothing
changes length and no string outgrows its slot.

Usage: tools/normalize.py [translation/*.tsv]
"""
from __future__ import annotations

import csv
import io
import sys

sys.path.insert(0, __file__.rsplit('/', 1)[0])
import jis  # noqa: E402
from consistency import PAIRS  # noqa: E402

DST = ('translation_zh', 'zh')


def build_rules() -> dict[str, str]:
    forced = jis.SUBSTITUTES            # traditional absent -> shinjitai
    rules = {}
    for trad, shin in PAIRS:
        if trad == shin or shin in forced.values():
            continue
        if jis.missing(trad):
            continue
        rules[shin] = trad
    rules.update(forced)
    return rules


def run(path: str, rules: dict[str, str]) -> int:
    raw = open(path, encoding='utf-8', newline='').read()
    rows = list(csv.reader(io.StringIO(raw), delimiter='\t'))
    head = rows[0]
    col = next((head.index(c) for c in DST if c in head), None)
    if col is None:
        print(f'{path}: 找不到譯文欄，略過')
        return 0
    out = io.StringIO()
    w = csv.writer(out, delimiter='\t', lineterminator='\r\n')
    w.writerow(head)
    changed = 0
    for row in rows[1:]:
        if len(row) > col:
            before = row[col]
            row[col] = ''.join(rules.get(c, c) for c in before)
            changed += row[col] != before
        w.writerow(row)
    open(path, 'w', encoding='utf-8', newline='').write(out.getvalue())
    print(f'{path}: {changed} 筆調整')
    return changed


if __name__ == '__main__':
    args = sys.argv[1:] or ['translation/event.tsv', 'translation/main_ui.tsv',
                            'translation/glossary.tsv']
    rules = build_rules()
    print(f'{len(rules)} 條字形規則')
    for p in args:
        run(p, rules)
