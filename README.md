# kami-zh

《神々の大地 ～古事記外伝～》(KOEI, 1993, DOS/V 版) 中文化專案。

目標是把遊戲文字以**漢字與中文**呈現，沿用原本 DOS/V 的漢字編碼
（Shift-JIS / JIS X 0208），不修改編碼、不替換字型、不擴充字庫——
譯文只使用原字庫涵蓋得到的字。

## 安裝與遊玩

到 [Releases](https://github.com/tzengyuxio/kami-zh/releases) 下載修補程式（Windows／macOS），
放進自備的 DOS/V 原版 `KAMI` 資料夾執行，旁邊會產生中文版 `KAMI_ZH`（原資料夾不動）。
用 [DOSBox-X](https://dosbox-x.com/) 的 DOS/V 模式遊玩，壓縮檔附有設定檔。

也可以在瀏覽器裡玩（網頁版，見 [`docs/playing.md`](docs/playing.md#網頁版)）。

詳細步驟、DOSBox-X 設定要點見 [`docs/playing.md`](docs/playing.md)。

## 翻譯進度

| 範圍 | 狀態 |
|---|---|
| 人物名 | ✅ 150 / 150 |
| 劇情（`translation/event.tsv`） | ✅ 2365 / 2365 |
| UI（`translation/main_ui.tsv`） | ✅ 1309 條（全畫面：道具、術法、職業、村落指令、情報、戰鬥、部隊、商店、系統訊息、開始選單、磁片提示） |
| 片頭（`translation/open_ui.tsv`） | ✅ 4 段敘事（`OPEN.EXE` 的錯誤訊息未譯） |
| 結局（`translation/end_ui.tsv`） | ✅ 4 段獨白（`END.EXE` 的錯誤訊息未譯） |
| 魔物名 | ✅ 60 / 60（另 10 筆是空白佔位） |

人名以**古事記的漢字原形**為準（150 筆中 57 筆有典可考，其餘依音義組字）。
審閱用的拆分清單見 [`docs/glossary-review.md`](docs/glossary-review.md)，
附每個組字名的依據。

## 開發

遊戲檔不在 repo 內，請自備並解壓到 `game/KAMI/`。

```sh
python3 tools/install.py   # game/ → build/，套用全部譯文
tools/dosbox/run.sh        # 在 DOSBox-X 執行
tools/release.sh v1.0.0    # 編出玩家用的修補程式
```

環境、工具一覽、回寫流程、發佈與模擬器踩坑見 [`docs/development.md`](docs/development.md)。

## 文件

- [`docs/playing.md`](docs/playing.md) — 安裝中文版、用 DOSBox-X 遊玩
- [`docs/development.md`](docs/development.md) — 開發說明：工具、回寫流程、發佈、模擬器
- [`docs/formats.md`](docs/formats.md) — 檔案格式分析（含未解項）
- [`docs/translation-style.md`](docs/translation-style.md) — 翻譯風格指南（語域、缺字處理、專有名詞表）
- [`docs/glossary-review.md`](docs/glossary-review.md) — 人名譯法審閱清單
- [`docs/guide/`](docs/guide/README.md) — 遊玩攻略資料（地圖與路線、迷宮寶箱、各村、鍛冶、道具、術法、身分、人物）

## 致謝

圖形格式的解析大量參考了 [tzengyuxio/kaodata](https://github.com/tzengyuxio/kaodata)
對早期光榮遊戲資料格式的研究，NPK 解壓演算法即移植自該專案。
