# kami-zh

《神々の大地 ～古事記外伝～》(KOEI, 1993, DOS/V 版) 中文化專案。

目標是把遊戲文字以**漢字與中文**呈現，沿用原本 DOS/V 的漢字編碼
（Shift-JIS / JIS X 0208），不修改編碼、不替換字型、不擴充字庫——
譯文只使用原字庫涵蓋得到的字。

## 本 repo 不包含遊戲檔案

遊戲 binary 與素材皆未納入版控。請自備遊戲，解壓到 `game/KAMI/`：

```
game/KAMI/MAIN.EXE
game/KAMI/EVENT.DAT
...
```

`extracted/text/` 下的對照表是分析產物，會進版控；
`extracted/gfx/` 下的圖片是遊戲素材，不進版控（可由工具重新產生）。

## 環境

```sh
uv venv
uv pip install pillow
```

## 工具

| 工具 | 用途 |
|---|---|
| `tools/npk.py` | NPK016 圖形容器：讀 offset table、解壓 chunk |
| `tools/gfx.py` | 把 NPK016 容器輸出成 PNG |
| `tools/rawgfx.py` | 渲染未壓縮的 planar 圖形（`FACEGRP.DAT` 等） |
| `tools/sjis_scan.py` | 掃描檔案中的 Shift-JIS 字串 |
| `tools/tables.py` | 匯出固定長度 record 的名稱表成 TSV |

範例：

```sh
# 列出 NPK 容器結構並驗證解壓
.venv/bin/python tools/npk.py game/KAMI/GRAPH.NPK

# 輸出 PNG
.venv/bin/python tools/gfx.py game/KAMI/GRAPH.NPK

# 20 張 48x64 Q 版人物立繪
.venv/bin/python tools/rawgfx.py game/KAMI/FACEGRP.DAT \
    --width 48 --height 64 --bpp 3 --layout chunky --out /tmp/faces.png

# 人物與魔物名稱表
.venv/bin/python tools/tables.py game/KAMI/SDATA.CIM --table SDATA.CIM \
    --out extracted/text/characters.tsv
```

## 文件

- [`docs/formats.md`](docs/formats.md) — 檔案格式分析（含未解項）

## 致謝

圖形格式的解析大量參考了 [tzengyuxio/kaodata](https://github.com/tzengyuxio/kaodata)
對早期光榮遊戲資料格式的研究，NPK 解壓演算法即移植自該專案。
