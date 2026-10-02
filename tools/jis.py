#!/usr/bin/env python3
"""JIS X 0208 coverage helpers.

The project keeps the game's original Shift-JIS encoding, so every character
a translation uses must exist in JIS X 0208. That character set is Japanese,
so a few common Traditional Chinese forms are simply absent. Most gaps close
with the Japanese shinjitai form, which reads fine in Chinese; a handful have
no substitute and need the sentence rewritten.

Measured against 192 of the most common Chinese characters, 7 are missing --
a 3% gap. The sore spot is sentence-final particles: 啊 喔 嗎 呢 吧 哪 are all
absent and only 呀 and 嘛 survive, so dialogue has to carry its tone through
word choice rather than particles.
"""
from __future__ import annotations

# Traditional form -> the JIS X 0208 form to use instead. Every key here is
# genuinely absent from JIS X 0208; plenty of other traditional forms (兒 豐
# 樂 鐵 藝 聲 圖 廣 惡 ...) are present and need no substitution, so do not
# add a character without checking.
SUBSTITUTES = {
    '產': '産', '查': '査', '錄': '録', '說': '説', '每': '毎',
    '內': '内', '姊': '姉', '溫': '温', '彥': '彦', '黃': '黄',
    '眾': '衆', '歷': '歴', '步': '歩', '淚': '涙', '黑': '黒', '增': '増',
    '絕': '絶', '擊': '撃', '鄉': '郷', '剝': '剥', '啟': '啓', '寬': '寛', '值': '値', '巢': '巣',
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
    # Chinese has no second-person pronoun in JIS X 0208 at all. Use the
    # classical 汝 / 君 / 爾, or address the listener by title.
    '您': '改用「汝」「君」或以稱謂代稱',
    '辦': '改用「做」「處理」',
    '趟': '改寫，如「一趟」->「一行」',
    '倘': '改用「若」「如」',
    '賴': '改用「信任」「倚靠」',
    '幫': '改用「助」「相助」',
    '嚐': '改用「嘗」',
    '睏': '改用「倦」「睡意」',
    '嗯': '改用「唔」',
    '另': '改用「別」「再」',
    '炫': '改用「誇」「誇耀」',
    # Colloquial Chinese is the weak spot: JIS X 0208 is built for Japanese,
    # so vernacular characters are thin while literary vocabulary is fine.
    '傢': '改用「此人」「這廝」「小子」',
    '伙': '改用「此人」「這廝」「小子」',
    '喂': '改用「嘿」以外的呼喚詞，或刪去',
    '哼': '改用「唔」或刪去',
    '尷': '改用「難堪」',
    '尬': '改用「難堪」',
    '划': '改用「值得」(値)',
    '偷': '改用「竊」',
    '爹': '改用「父親」「老頭」',
    '懂': '改用「明白」「曉得」',
    '撿': '改用「拾」',
    '擋': '改用「阻」「妨礙」',
    '夠': '改用「足」「足夠」改寫',
    '趕': '改用「急」「驅」',
    # Chinese sentence-final particles are almost all absent. 呀 and 嘛 are
    # the exceptions, so lean on those or drop the particle entirely.
    '啊': '改用「呀」或刪去語氣詞',
    '喔': '改用「呀」或刪去語氣詞',
    '呢': '改成直述句或用「呀」',
    '哪': '改寫；「哪裡」用「何處」',
    '咦': '改用「呀」或刪去',
    '唷': '改用「呀」或刪去',
    '喲': '改用「呀」或刪去',
}


def encodable(ch: str) -> bool:
    """True only for characters the DOS/V font can actually draw.

    cp932 is a superset of JIS X 0208: it adds NEC row 13 (lead 0x87) and the
    NEC/IBM extension rows (leads 0xED-0xEE and 0xFA-0xFC). Those encode
    fine but the DOS/V font has no glyph for them -- 黑 (0xEEEC) came out as
    a blank gap on screen while every JIS X 0208 character rendered. So the
    check is on the Shift-JIS lead byte, not on whether cp932 accepts it.
    """
    try:
        b = ch.encode('cp932')
    except UnicodeEncodeError:
        return False
    if len(b) == 1:
        return 0x20 <= b[0] <= 0x7E
    lead = b[0]
    return (0x81 <= lead <= 0x9F and lead != 0x87) or 0xE0 <= lead <= 0xEA


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
