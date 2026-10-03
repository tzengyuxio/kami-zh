#!/usr/bin/env python3
"""Flag inconsistencies across the translated text.

Two kinds, both of which read fine line by line but look wrong in play:

  variants   the same word written two ways (讓 vs 譲, 戰 vs 戦)
  divergent  one Japanese source string translated more than one way

Usage: tools/consistency.py [translation/*.tsv]
"""
from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict

# Traditional form -> Japanese shinjitai. Both are in JIS X 0208, so the
# verifier passes either; only consistency tells them apart.
PAIRS = [
    ('讓', '譲'), ('戰', '戦'), ('繼', '継'), ('續', '続'), ('變', '変'),
    ('亂', '乱'), ('壞', '壊'), ('惡', '悪'), ('氣', '気'), ('對', '対'),
    ('發', '発'), ('舉', '挙'), ('轉', '転'), ('擇', '択'), ('體', '体'),
    ('數', '数'), ('實', '実'), ('歡', '歓'), ('應', '応'), ('學', '学'),
    ('會', '会'), ('萬', '万'), ('與', '与'), ('當', '当'), ('兒', '児'),
    ('勞', '労'), ('單', '単'), ('圖', '図'), ('廣', '広'), ('濟', '済'),
    ('畫', '画'), ('聲', '声'), ('藝', '芸'), ('處', '処'), ('燒', '焼'),
    ('關', '関'), ('樂', '楽'), ('龍', '竜'), ('顯', '顕'), ('隱', '隠'),
    ('覽', '覧'), ('驅', '駆'), ('壯', '壮'), ('靜', '静'), ('豐', '豊'),
    ('傳', '伝'), ('殘', '残'), ('盡', '尽'), ('隨', '随'), ('帶', '帯'),
    ('壓', '圧'), ('獸', '獣'), ('戀', '恋'), ('齊', '斉'), ('濱', '浜'),
    ('擔', '担'), ('臟', '臓'), ('歲', '歳'), ('條', '条'), ('惱', '悩'),
    ('稱', '称'), ('徑', '径'), ('擴', '拡'), ('釋', '釈'), ('獻', '献'),
    ('繩', '縄'), ('總', '総'), ('縱', '縦'), ('繪', '絵'), ('雜', '雑'),
    ('霸', '覇'), ('齡', '齢'), ('勸', '勧'), ('嚴', '厳'), ('壘', '塁'),
    ('寶', '宝'), ('將', '将'), ('屬', '属'), ('巖', '巌'), ('惠', '恵'),
    ('戲', '戯'), ('晝', '昼'), ('樓', '楼'), ('歸', '帰'), ('滿', '満'),
    ('燈', '灯'), ('瑤', '瑶'), ('稻', '稲'), ('穩', '穏'), ('稅', '税'),
    ('縣', '県'), ('腦', '脳'), ('臺', '台'), ('舊', '旧'), ('莊', '荘'),
    ('蟲', '虫'), ('覺', '覚'), ('觀', '観'), ('譯', '訳'), ('讀', '読'),
    ('贊', '賛'), ('邊', '辺'), ('釀', '醸'), ('陷', '陥'), ('顏', '顔'),
    ('驛', '駅'), ('髮', '髪'), ('鹽', '塩'), ('麥', '麦'), ('劍', '剣'),
    ('鐵', '鉄'), ('鑛', '鉱'), ('獵', '猟'), ('潛', '潜'), ('澤', '沢'),
    ('禮', '礼'), ('醫', '医'), ('藥', '薬'), ('鬥', '闘'), ('舖', '舗'),
    ('祿', '禄'), ('靈', '霊'), ('險', '険'), ('餘', '余'), ('黨', '党'),
    ('齋', '斎'), ('裡', '裏'), ('驗', '験'), ('姬', '姫'),
    ('樣', '様'), ('效', '効'), ('裝', '装'), ('收', '収'), ('經', '経'),
    ('輕', '軽'), ('號', '号'), ('斷', '断'), ('騷', '騒'), ('犧', '犠'),
    ('價', '価'), ('樂', '楽'), ('爭', '争'), ('嚴', '厳'),
]

SRC = 'original_ja'
DST = 'translation_zh'


def rows(path):
    with open(path, encoding='utf-8', newline='') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            if r.get(DST, '').strip():
                yield r


def main(paths):
    counts = Counter()
    where = defaultdict(list)
    by_source = defaultdict(set)

    for path in paths:
        for r in rows(path):
            zh = r[DST]
            label = f"{path}:{r.get('block', r.get('id', '?'))}/{r.get('index', '')}"
            for ch in set(zh):
                counts[ch] += zh.count(ch)
                where[ch].append(label)
            ja = r.get(SRC, '')
            if ja:
                by_source[ja].add(zh.strip())

    problems = 0
    for trad, shin in PAIRS:
        if trad == shin or not (counts[trad] and counts[shin]):
            continue
        problems += 1
        loser, winner = ((trad, shin) if counts[trad] < counts[shin]
                         else (shin, trad))
        print(f"變體混用 {trad}({counts[trad]}) / {shin}({counts[shin]})"
              f" -- 少數的是 {loser}，出現在:")
        for label in where[loser][:6]:
            print(f"    {label}")

    for ja, zhs in sorted(by_source.items()):
        if len(zhs) < 2:
            continue
        problems += 1
        print(f"同原文多種譯法: {ja}")
        for zh in sorted(zhs):
            print(f"    {zh}")

    print(f"{len(paths)} 個檔案, {problems} 項不一致")
    return 1 if problems else 0


if __name__ == '__main__':
    args = sys.argv[1:] or ['translation/event.tsv', 'translation/main_ui.tsv']
    sys.exit(main(args))
