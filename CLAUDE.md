# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

《神々の大地 ～古事記外伝～》(KOEI, 1993, DOS/V) 的繁體中文化專案。核心限制：**不改編碼、不換字型、不擴字庫**——譯文只能用 JIS X 0208 內的字，以原本的 Shift-JIS 寫回遊戲檔。

## 遊戲檔不在 repo

遊戲原檔放 `game/KAMI/`（gitignored，版權因素**絕不 commit**；`.gitignore` 也擋了 `*.EXE` `*.DAT` `*.CIM` 等）。`game/` 永遠保持原樣，所有修補輸出到 `build/KAMI/`。沒有 `game/` 時，大部分工具無法執行。

## 常用指令

沒有測試套件與 linter；「驗證」就是下面這些檢查工具。回寫鏈（`install.py`／`patch.py`／`event.py`／`tables.py`／`jis.py`）**只用標準庫**，`python3` 即可；只有圖形工具（`npk.py`／`gfx.py`／`rawgfx.py`）需要 `.venv`（`uv venv && uv pip install pillow`）。

```sh
# 完整建置：game/ → build/，套用所有譯文（SKIP_OPENING=0 保留片頭）
python3 tools/install.py

# 劇情譯文檢查：缺字、70 bytes 上限、控制碼序列是否一致
python3 tools/event.py verify --tsv translation/event.tsv

# EVENT.DAT 解析／重建的往返驗證（應 byte-identical）
python3 tools/event.py check

# UI 譯文檢查：缺字與 max_bytes
python3 tools/patch.py check --tsv translation/main_ui.tsv

# 跨檔一致性：繁／日字形混用、同一句日文多種譯法
python3 tools/consistency.py translation/*.tsv

# 就地正規化字形（繁體優先，缺字才用新字體）
python3 tools/normalize.py translation/*.tsv

# 在 DOSBox-X（DOS/V 日文模式）執行；帶秒數則錄影到 build/captures/
tools/dosbox/run.sh [秒數]
```

改完譯文後的基本驗證：`event.py verify` / `patch.py check` + `consistency.py` + `install.py` 跑得過（它會檢查 `MAIN.EXE` 大小沒變）。

## 架構：三種回寫路徑

`translation/*.tsv` 是譯文正本；`extracted/text/*.tsv` 是工具抽出的原文對照（分析產物，有進版控）。`tools/install.py` 把它們依檔案類型分派給三種不同的回寫機制，順序有依賴：

1. **就地覆寫**（`patch.py`）——`MAIN.EXE` 的 UI 字串（`main_ui.tsv`）、`OPEN.EXE` 的片頭敘事（`open_ui.tsv`）與 `END.EXE` 的結局獨白（`end_ui.tsv`）。譯文**不得超過 `max_bytes`**，比原文短補 NUL。`MAIN.EXE` 大小必須不變。片頭旁白用原始 `0x0a` 換行，在 TSV 中寫成 `\n`；片頭的 `W`／`N`／`X` 控制碼同劇情規則，須原樣同序保留（`patch.py` 不檢查這點）。`extracted/text/open_ui.tsv` 是被換行切碎的舊抽取結果，以 `translation/open_ui.tsv` 為準。
2. **固定長度 record**（`tables.py`）——`SDATA.CIM`（人物 150 筆）、`RPDATA.CIM`（魔物 70 筆），來源是 `translation/glossary.tsv`，名稱上限 14 bytes（7 個全形字）。
3. **整檔重建**（`event.py`）——`EVENT.DAT` 劇情（`event.tsv`，以 `block`+`index` 定位）。訊息長度可變，但 block 位移索引存在 `MAIN.EXE`（`0x049f10`、`0x049fd0` 兩張 47×u32 表），所以 `event.py apply` 吃**已修補過的** `MAIN.EXE` 再寫回去——必須在 `patch.py` 之後執行。

`SDATA.CIM` 另有一份與 `MAIN.EXE 0x04be94` 相同的村落表（`0x92` 起），新遊戲從這份讀；`install.py` 會把 `MAIN.EXE` 已譯的村名複製過去，所以村名只改 `main_ui.tsv`。存檔（`SAVEDATA.DAT`）的每個欄位都是 `SDATA.CIM` 的快照，名稱在開新遊戲時就固定了——譯名更新後要用 `tools/savepatch.py` 修補舊存檔。

`trial_event.tsv` 是早期就地覆寫試譯的遺留格式，`install.py` 不使用它。

格式細節（NPK016 壓縮、XOR 0x77、block 結構、控制碼）見 `docs/formats.md`。

圖形匯出（`gfx.py`／`rawgfx.py`）的顏色來自 `tools/palette.py`，是從 DOSBox-X raw 截圖（索引色 PNG，帶實際 DAC 值）量出來的：色號 0–7 全遊戲固定，8–15 依場景（`--scene field|village|cave`）。圖檔色號＝螢幕色號，所以要確認新場景的色盤，就截圖後讀 PNG 的 palette，再拿 chunk 與截圖逐像素比對（見 `docs/formats.md` §2）。

## 翻譯時的硬限制

- **JIS X 0208 ≠ cp932**：cp932 能編碼的 NEC/IBM 擴充字在 DOS/V 字型裡沒字模（顯示空白）。用 `tools/jis.py` 的檢查，不要只看「能不能 encode cp932」。
- **字形政策：JIS 有繁體字形就用繁體**（`讓` 不寫 `譲`），只有 `jis.SUBSTITUTES` 列的缺字才用日系新字體（`産` `査` `録`…）。新增 SUBSTITUTES 前要先確認該字真的不在 JIS X 0208。
- **口語缺字嚴重**：`你` `您` `嗎` `啊` `呢` `吧` 等都不在字庫，因此整體語域偏文言（`汝`、`可否？`、`乎？`、`也／矣／哉`）。替換表與用語統一表在 `docs/translation-style.md`，翻譯前先讀。
- **劇情每則訊息硬上限 70 bytes**（引擎固定緩衝區，含控制碼）；超過可用 `Cnnn` 接續，各段內容可重新分配。
- **控制碼（訊息中所有 ASCII）必須原樣、同序保留**：`G` 換行、`W` 等待、`N`/`X` 換頁、`S`、`U` 主角名、`Y`、`Cnnn`、`Fnnn`、`%s` 等。
- **UI 字串**：printf 格式符個數與順序不變；半形空白是對齊用的，譯文變短要補空白。`extracted/text/main_ui.tsv` 約 90 筆 offset 落在字串中段、帶亂碼前綴——那是前一筆資料的尾巴，不能覆寫。
- `consistency.py` 剩下的 8 筆「同原文多種譯法」是已知誤報（跨訊息的句尾片段），列在 `docs/translation-style.md`。
- 人名以古事記漢字原形為準，依據見 `docs/glossary-review.md`。

## 發佈

`tools/release.sh VERSION` 產生玩家用的修補程式（`patcher/`，Go，內嵌 `mkpatch.py` 做的差異檔），輸出到 `patcher/dist/`。它自己在暫存目錄建置，不含遊戲修改；不要拿 `build/KAMI` 做差異（可能套過 `weakfoes.py`、跳過片頭）。

網頁版在 `web/`（js-dos＋DOSBox-X WASM，玩家在瀏覽器裡選原版檔、套用同一份 `kami-zh.kzp`），`tools/web.sh` 組出 `web/dist/`，細節見 `docs/development.md`。

## 模擬器踩坑

`tools/dosbox/run.sh` 已處理好下列問題，修改時別弄壞：`dosv` 設定屬於 `[dosv]` 區段；A: 必須是 `imgmake` 做的真軟碟映像並放 `BDISK.VER`；不能直接跑 `MAIN.EXE`（需 `KAMI.COM` 安裝 INT 65h，`install.py` 把 `KAMI.COM` 執行 `OPEN.EXE` 的程式碼改成 NOP 來跳過片頭；改字串會讓 `MAIN.EXE` 跑兩次、破關後不播 ED）。遊戲選單是滑鼠驅動的，自動化要用 `tools/mousetsr.py` 產生 `build/FAKEMS.COM`（原理與常用座標見 `docs/development.md`）。

## 文件同步

翻譯進度表在 `README.md`，工具表與開發流程在 `docs/development.md`，風格規則在 `docs/translation-style.md`；改變進度、新增工具或確立新的用字規則時一併更新。
