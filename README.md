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
| `tools/text.py` | 抽出可翻譯文字成 TSV（支援 XOR 解碼與區段限定） |
| `tools/tables.py` | 匯出固定長度 record 的名稱表成 TSV |
| `tools/patch.py` | 把譯文寫回遊戲檔（檢查 JIS 字庫與位元組上限） |

範例：

```sh
# 列出 NPK 容器結構並驗證解壓
.venv/bin/python tools/npk.py game/KAMI/GRAPH.NPK

# 輸出 PNG
.venv/bin/python tools/gfx.py game/KAMI/GRAPH.NPK

# 20 張 48x64 Q 版人物立繪
.venv/bin/python tools/rawgfx.py game/KAMI/FACEGRP.DAT \
    --width 48 --height 64 --bpp 3 --layout chunky --out /tmp/faces.png

# 劇情對話（EVENT.DAT 是 Shift-JIS XOR 0x77）
.venv/bin/python tools/text.py game/KAMI/EVENT.DAT --xor 0x77 \
    --out extracted/text/event_dialogue.tsv

# UI 文字（明碼 Shift-JIS，限定字串表區段）
.venv/bin/python tools/text.py game/KAMI/MAIN.EXE --start 0x40000 \
    --out extracted/text/main_ui.tsv

# 人物與魔物名稱表
.venv/bin/python tools/tables.py game/KAMI/SDATA.CIM --table SDATA.CIM \
    --out extracted/text/characters.tsv
```

## 目前抽出的文字

| 檔案 | 筆數 | 內容 |
|---|---:|---|
| `extracted/text/event_dialogue.tsv` | 2,219 | 劇情對話（約 64,000 字） |
| `extracted/text/main_ui.tsv` | 950 | 選單、道具名、季節事件文 |
| `extracted/text/characters.tsv` | 155 | 人物名 |
| `extracted/text/monsters.tsv` | 70 | 魔物名 |
| `extracted/text/open_ui.tsv` | 28 | 片頭 |
| `extracted/text/end_ui.tsv` | 24 | 結局 |

每個 TSV 都有空的譯文欄位，以及 `max_bytes`（原字串的位元組長度）——
就地覆寫時譯文不得超過這個長度。

## 翻譯與回寫

譯文放在 `translation/`，欄位與 `extracted/text/` 相同。回寫流程：

```sh
# 先檢查：譯文是否都在 JIS X 0208 內、是否超出位元組上限
.venv/bin/python tools/patch.py check --tsv translation/trial_main_ui.tsv

# 套用到 build/（絕不就地改 game/ 的原始檔）
mkdir -p build/KAMI && cp game/KAMI/* build/KAMI/
.venv/bin/python tools/patch.py apply --tsv translation/trial_main_ui.tsv \
    --target game/KAMI/MAIN.EXE --out build/KAMI/MAIN.EXE
.venv/bin/python tools/patch.py apply --tsv translation/trial_event.tsv \
    --target game/KAMI/EVENT.DAT --out build/KAMI/EVENT.DAT --xor 0x77

# 在 DOSBox-X 的 DOS/V 日文模式下執行
dosbox-x -conf tools/dosbox/kami.conf
```

字串是 NUL 結尾的，所以譯文可以短於原文；與原文等長時不補 NUL
（原字串的結束符就在 `max_bytes` 之後）。**譯文不得超過 `max_bytes`** ——
變長回寫要等 `EVENT.DAT` 的腳本結構解開後才能做。

### 字庫限制實例

JIS X 0208 收的是日系字形，繁體常用字會有缺口。試譯時實際撞到的：

| 想用 | 改用 | 備註 |
|---|---|---|
| 產 | 産 | 日系新字體 |
| 查 | 査 | 日系新字體；或換詞（「探勘地形」） |
| 錄 | 録 | 日系新字體 |
| 丟 | 捨 | 「捨棄道具」 |
| 檔 | — | 無對應字，必須換詞（「玩家磁片」而非「存檔磁片」） |
| 嗎 | — | 無對應字，必須改句式（「是否確定？」而非「確定嗎？」） |

`tools/patch.py check` 會把這類缺字全部列出來。先用它掃過整批譯文，
再逐條換字或換詞，比一個個撞有效率。

## 在模擬器上驗證

```sh
dosbox-x -conf tools/dosbox/kami.conf -nopromptfolder -fastlaunch \
         -time-limit 130 -exit
```

設定檔裡的 `config -avistart` 會從 DOS 內開始錄影，存到 `build/captures/`。
這是唯一不需要主機端螢幕錄製權限的擷取方式。`-time-limit` 強制結束時
AVI 的 index 會壞掉，用 `-fflags +ignidx` remux 後再抽影格：

```sh
ffmpeg -y -fflags +ignidx -i build/captures/kami_000.avi -c copy /tmp/k.avi
ffmpeg -y -i /tmp/k.avi -vf "fps=1/2" /tmp/frames/k%03d.png
```

`AUTOTYPE -w <秒> -p <秒> <按鍵>...` 可以在遊戲執行中送按鍵
（`-w` 會延後開始，所以能跨過 `KAMI.COM` 的交接）。片頭可用 ESC 跳過。

### 踩過的坑

- **`dosv` 屬於 `[dosv]` 區段，不是 `[dos]`。** 寫錯位置不會報錯，
  但遊戲會把對話框畫出來、裡面一個字都沒有，很容易誤判成字型缺失。
- 直接跑 `MAIN.EXE` 只有黑畫面；要走 `KAMI.COM`（它會依序載入
  `FMDRV.COM` → `OPEN.EXE` → `MAIN.EXE`）。

## 文件

## 文件

- [`docs/formats.md`](docs/formats.md) — 檔案格式分析（含未解項）

## 致謝

圖形格式的解析大量參考了 [tzengyuxio/kaodata](https://github.com/tzengyuxio/kaodata)
對早期光榮遊戲資料格式的研究，NPK 解壓演算法即移植自該專案。
