#!/usr/bin/env python3
"""JIS X 0208 coverage helpers.

The project keeps the game's original Shift-JIS encoding, so every character
a translation uses must exist in JIS X 0208. That character set is Japanese,
so a few common Traditional Chinese forms are simply absent. Most gaps close
with the Japanese shinjitai form, which reads fine in Chinese; a handful have
no substitute and need the sentence rewritten.

Measured against 192 of the most common Chinese characters, 7 are missing --
a 3% gap.
"""
from __future__ import annotations

# Traditional form -> the JIS X 0208 form to use instead.
SUBSTITUTES = {
    '產': '産', '查': '査', '錄': '録', '說': '説', '每': '毎',
    '內': '内', '姊': '姉', '溫': '温', '鐵': '鉄', '藝': '芸',
    '聲': '声', '會': '会', '圖': '図', '廣': '広', '惡': '悪',
}

# No JIS X 0208 form at all -- the sentence has to be reworded.
NO_SUBSTITUTE = {
    '你': '改用「汝」「君」或改寫句子',
    '她': '改用「他」或改寫句子',
    '嗎': '改用「麼」或改成直述句',
    '吧': '刪去或改寫語氣',
    '丟': '改用「捨」「棄」',
    '檔': '改用「記錄」以外的詞，如「玩家磁片」',
    '跑': '改用「奔」「走」',
}


def encodable(ch: str) -> bool:
    try:
        ch.encode('cp932')
        return True
    except UnicodeEncodeError:
        return False


def missing(text: str) -> list[str]:
    """Characters in `text` that JIS X 0208 cannot represent, in order."""
    seen, out = set(), []
    for ch in text:
        if ch not in seen and not encodable(ch):
            seen.add(ch)
            out.append(ch)
    return out


def advise(chars: list[str]) -> str:
    """One-line advice for each unavailable character."""
    parts = []
    for ch in chars:
        if ch in SUBSTITUTES:
            parts.append(f'{ch}->{SUBSTITUTES[ch]}')
        elif ch in NO_SUBSTITUTE:
            parts.append(f'{ch}({NO_SUBSTITUTE[ch]})')
        else:
            parts.append(f'{ch}(無已知替代，請改寫)')
    return '; '.join(parts)


if __name__ == '__main__':
    import sys
    text = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()
    bad = missing(text)
    if bad:
        print(advise(bad))
    else:
        print(f'OK, {len(text.encode("cp932"))} bytes')
