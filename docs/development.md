# 開發說明

建置、工具、回寫流程與模擬器操作。翻譯規則見 [`translation-style.md`](translation-style.md)，檔案格式見 [`formats.md`](formats.md)。

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

回寫譯文（`tools/install.py` 與它用到的 `patch.py`／`event.py`／`tables.py`）
**只用標準庫**，有 `python3` 就能跑，不必建虛擬環境。

圖形工具（`npk.py`／`gfx.py`／`rawgfx.py`／`worldmap.py`／`forcemap.py`／`villagemap.py`／`dungeonmap.py`／`japanmap.py`）需要 pillow：

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
| `tools/worldmap.py` | 繪製大地圖（日文／中文村名版）、各村領地與相鄰線，並列出相鄰表 |
| `tools/forcemap.py` | 繪製村莊畫面的勢力地圖：只上色的一張，以及標上村名的日文、中文各一張 |
| `tools/villagemap.py` | 繪製 32 張村莊平面圖（標出村長家、倉庫、鍛冶屋、入口等） |
| `tools/dungeonmap.py` | 繪製 13 座迷宮共 81 張地圖；`--guide` 另出標上寶箱、樓梯、門、傳送陣與機關的版本，`--list` 列成清單 |
| `tools/japanmap.py` | 在現代日本地圖上標出遊戲 30 村的對應地點 |
| `tools/palette.py` | 實測的遊戲色盤（固定 0–7 色＋地圖／村落／洞窟三組 8–15 色） |
| `tools/sjis_scan.py` | 掃描檔案中的 Shift-JIS 字串 |
| `tools/text.py` | 抽出可翻譯文字成 TSV（支援 XOR 解碼與區段限定） |
| `tools/tables.py` | 匯出固定長度 record 的名稱表成 TSV |
| `tools/patch.py` | 把譯文寫回遊戲檔（檢查 JIS 字庫與位元組上限） |
| `tools/event.py` | 解析／重建 `EVENT.DAT`，支援**變長**譯文 |
| `tools/jis.py` | 檢查用字是否在 JIS X 0208 內，並給替代建議 |
| `tools/consistency.py` | 跨檔一致性檢查：繁／日字形混用、同一句日文多種譯法 |
| `tools/normalize.py` | 就地正規化字形（繁體優先，缺字才用新字體） |
| `tools/install.py` | 一鍵把 `game/` 修補成 `build/`（跨平台，純標準庫） |
| `tools/dosbox/run.sh` | 在 DOSBox-X（DOS/V 日文模式）執行 `build/KAMI`，可帶秒數錄影 |
| `tools/mkpatch.py` | 比對原版與中文版，產生發佈用的差異檔（只含譯文） |
| `tools/release.sh` | 從頭建置乾淨的中文版並編出 Windows／macOS 修補程式（`patcher/`，Go） |
| `tools/web.sh` | 組出網頁版（`web/`）到 `web/dist/`，`serve` 參數可在本機開伺服器測試 |
| `tools/savepatch.py` | 把舊存檔裡的村名、人名更新成目前 build 的譯名（原檔留 `.bak`） |
| `tools/maxgear.py` | 遊玩輔助：把 build 的 `MAIN.EXE` 中所有武器攻擊、防具防禦設成 255（`install.py` 會還原，需重跑） |
| `tools/weakfoes.py` | 遊玩輔助：把 build 的 `RPDATA.CIM` 魔物體力、`BPDATA.CIM` 頭目各部位體力設成 10（`install.py` 會還原，需重跑） |
| `tools/mousetsr.py` | 產生腳本化滑鼠的 DOS TSR，用來自動化選單操作 |
| `tools/exptsr.py` | 產生熱鍵 TSR：遊戲中按 Ctrl+E，指定人物下次獲得經驗即升級 |
| `tools/statepeek.py` | 從 DOSBox-X 快照讀出人物等級、經驗與能力值 |

範例：

```sh
# 列出 NPK 容器結構並驗證解壓
.venv/bin/python tools/npk.py game/KAMI/GRAPH.NPK

# 輸出 PNG（色號 8–15 依 --scene 選 field／village／cave，預設 field）
.venv/bin/python tools/gfx.py game/KAMI/GRAPH.NPK
.venv/bin/python tools/gfx.py game/KAMI/GRAPH.NPK --scene cave --out-dir extracted/gfx/cave

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
| `extracted/text/main_ui.tsv` | 950 | 選單、道具名、季節事件文（`--min-chars 4` 的結果；放寬到 2 另有約 250 條短字串，見 style guide） |
| `extracted/text/characters.tsv` | 155 | 人物名 |
| `extracted/text/monsters.tsv` | 70 | 魔物名 |
| `extracted/text/open_ui.tsv` | 28 | 片頭 |
| `extracted/text/end_ui.tsv` | 24 | 結局 |

每個 TSV 都有空的譯文欄位，以及 `max_bytes`（原字串的位元組長度）——
就地覆寫時譯文不得超過這個長度。

## 翻譯與回寫

譯文放在 `translation/`，欄位與 `extracted/text/` 相同。改完譯文後的檢查與建置：

```sh
python3 tools/event.py verify --tsv translation/event.tsv     # 劇情：缺字、70 bytes 上限、控制碼
python3 tools/patch.py check --tsv translation/main_ui.tsv    # UI：缺字與 max_bytes
python3 tools/consistency.py translation/*.tsv                # 跨檔一致性
python3 tools/install.py                                      # 套用全部譯文到 build/KAMI/
```

`install.py` 依檔案類型分派三種回寫方式（UI／片頭／結局就地覆寫、人名與魔物名寫入
固定長度 record、劇情整檔重建），`game/` 永遠不改。

### 兩種回寫方式

**就地覆蓋**（`tools/patch.py`）用於 `MAIN.EXE` 等執行檔內的字串。
字串是 NUL 結尾的，譯文可以短於原文；與原文等長時不補 NUL。
**譯文不得超過 `max_bytes`**。

**整檔重建**（`tools/event.py`）用於 `EVENT.DAT` 的劇情文字。
檔案會重新組裝，所以譯文長度不受原文限制：

```sh
# 匯出全部 2365 則訊息
.venv/bin/python tools/event.py dump --out extracted/text/event_messages.tsv

# 往返驗證（重建結果應與原檔位元組相同）
.venv/bin/python tools/event.py check

# 套用（同時改寫 EVENT.DAT 與 MAIN.EXE 裡的 block 索引）
.venv/bin/python tools/event.py --main build/KAMI/MAIN.EXE \
    apply --tsv translation/event.tsv \
    --out-event build/KAMI/EVENT.DAT --out-main build/KAMI/MAIN.EXE
```

但**每則訊息仍有 70 bytes 的硬上限**（引擎固定緩衝區，含控制碼）。
原文平均 53 bytes，所以中文通常還有餘裕；真的塞不下時用 `Cnnn`
接續到下一則。翻譯時**必須原樣保留控制碼**（`G` 換行、`W` 等待、
`U` 主角名、`Cnnn` 接續等，見 `docs/formats.md`）。

### 字庫限制實例

JIS X 0208 收的是日系字形，繁體常用字會有缺口。試譯時實際撞到的：

| 想用 | 改用 | 備註 |
|---|---|---|
| 產 | 産 | 日系新字體 |
| 查 | 査 | 日系新字體；或換詞（「探勘地形」） |
| 錄 | 録 | 日系新字體 |
| 丟 | 捨 | 「捨棄道具」 |
| 檔 | — | 無對應字，必須換詞（「記録磁片」而非「存檔磁片」） |
| 嗎 | — | 無對應字，必須改句式（「是否確定？」而非「確定嗎？」） |

`tools/patch.py check` 會把這類缺字全部列出來。先用它掃過整批譯文，
再逐條換字或換詞，比一個個撞有效率。

## 發佈修補程式

```sh
tools/release.sh v1.0.0
gh release create v1.0.0 patcher/dist/*.zip
```

`release.sh` 需要 `game/KAMI` 與 Go。它在暫存目錄另做一份乾淨建置（保留片頭、
不含 `weakfoes.py` 之類的遊戲修改，不動 `build/KAMI`），用 `mkpatch.py` 產生
`patcher/kami-zh.kzp`，再交叉編譯 `patcher/`（差異檔內嵌進執行檔），輸出到
`patcher/dist/`。差異檔與執行檔都不進版控。

修補程式只支援與 `game/KAMI` 相同的原版：會先比對每個檔案的 SHA-256，
不符就停止。

## 網頁版

```sh
tools/web.sh          # 組出 web/dist/（index.html、app.js、kami-zh.kzp）
tools/web.sh serve    # 同上，並在 http://localhost:8000/ 開伺服器
```

`web/` 是純靜態網頁，沒有建置步驟：js-dos 8.5.1（含 DOSBox-X 的 WebAssembly 版）與 fflate
從 jsDelivr 載入。玩家選擇自己的原版資料夾或 zip 後，`app.js` 在瀏覽器裡用 `kami-zh.kzp`
的 SHA-256 驗證、套用差異（與 `patcher/` 相同的格式），打包成 js-dos bundle 再啟動。

- **原版檔**存在瀏覽器的 IndexedDB，修補在每次開始時重做，所以更新 `kami-zh.kzp` 後玩家不必重選檔案。
- **存檔**：js-dos 把 C: 的變動（`SAVEDATA.DAT`、軟碟映像）以固定的鍵 `kami-zh.changes` 存在瀏覽器。
  `app.js` 每 3 秒讀一次 `KAMI/SAVEDATA.DAT`，內容變了、且下一次讀到相同（寫完了）就呼叫 js-dos 的 `save()`，
  所以遊戲內存檔會自動保存。js-dos 的 `fsReadFile` 讀不存在的檔案時不會回傳，要先用 `fsTree` 確認檔案存在。
- **快照**：DOSBox-X 的狀態快照（js-dos 的 `hand_savestate`／`hand_loadstate` 事件）。`dosbox.conf` 設
  `savefile = kamistate.sav`、`usesavefile = true`，快照就寫在 bundle 根目錄（約 350 KB），`app.js` 讀出來
  連同縮圖存進 IndexedDB 的 8 個欄位，另有一格快速快照（F6 存、F7 讀，不經確認；js-dos 自己的 F6／F7 以
  `quickSave: false` 關掉）。存之前先刪掉舊的快照檔，才分辨得出「寫好了」；讀取時寫回再觸發 `hand_loadstate`。快照不含磁碟，讀快照不影響遊戲內存檔。
- **字型**：沒有系統字型可借，DOS/V 用的是 DOSBox-X 內建的預設字型，筆畫與桌面版不同。
- **跳過片頭**用與 `install.py` 相同的 NOP 改法，在瀏覽器裡改 `KAMI.COM`。

移植到其他 KOEI DOS/V 中文化專案時，可沿用的部分與 js-dos 的坑整理在 `docs/web-port.md`。

`web/dist/` 不進版控，內容只有網頁、程式與差異檔，不含遊戲資料，可以直接放上 GitHub Pages 之類的靜態主機。

## 在模擬器上執行

```sh
python3 tools/install.py  # 把 game/ 複製到 build/ 並套用全部譯文
tools/dosbox/run.sh       # 開視窗遊玩
tools/dosbox/run.sh 60    # 錄 60 秒到 build/captures/ 後自動結束
```

存檔會把開新遊戲當時的村名、人名一起存下來，之後不會再從遊戲檔讀取。
譯名有更新時，舊存檔要另外修補（先跑 `install.py`）：

```sh
python3 tools/savepatch.py build/KAMI/SAVEDATA.DAT
```

想加快升級時，產生熱鍵 TSR（參數是人物編號，0 是主角），`run.sh` 偵測到
`build/EXPKEY.COM` 就會在遊戲前載入。遊戲中按 **Ctrl+E**，列出的人物「距下一級」
變成 1，下次獲得經驗就升級；高音表示成功，低音表示沒找到資料。刪掉該檔即停用：

```sh
python3 tools/exptsr.py build/EXPKEY.COM 0 40 48
```

### 腳本化滑鼠

遊戲的選單是滑鼠驅動的，而 DOSBox-X 沒有注入滑鼠的管道。
`tools/mousetsr.py` 產生一個 DOS TSR 來解決：

```sh
# 參數是 "秒,x,y,按鍵" 的序列；按鍵 bit 0 是左鍵
.venv/bin/python tools/mousetsr.py build/FAKEMS.COM \
    "3,146,96,0; 3.6,146,96,1; 5.2,146,96,0"
tools/dosbox/run.sh 30
```

`run.sh` 偵測到 `build/FAKEMS.COM` 就會在遊戲前載入它。座標是遊戲的
640×480 DOS/V 畫面。常用位置：開始選單「開始新遊戲」`(146,96)`、
名字視窗「決定」`(383,356)`、確認框「はい」`(431,370)`、
頂端指令列 y=52（移動 105 / 術 172 / 道具 225 / 情報 282 /
調査 347 / 行動 412 / 隊列 477 / 機能 542）。

TSR 的做法見該檔的 docstring。重點是**只偽造 INT 33h function 3 不夠** ——
遊戲用 function 0Ch 註冊了事件回呼，游標只在回呼被呼叫時才更新。
所以 TSR 同時掛 INT 1Ch，以 18.2Hz 主動呼叫遊戲的回呼，
並且**要先用遊戲訂閱的遮罩過濾事件旗標**（這款只訂閱「移動」）——
不過濾的話遊戲的狀態機會錯亂，點擊完全無效。

錄影用的是 `config -avistart`，從 DOS 內啟動 —— 這是唯一不需要主機端
螢幕錄製權限的擷取方式。`-time-limit` 強制結束會弄壞 AVI 的 index，
用 `-fflags +ignidx` remux 後再抽影格：

```sh
ffmpeg -y -fflags +ignidx -i build/captures/kami_000.avi -c copy /tmp/k.avi
ffmpeg -y -i /tmp/k.avi -vf "fps=1" /tmp/frames/k%03d.png
```

### 踩過的坑

- **`dosv` 屬於 `[dosv]` 區段，不是 `[dos]`。** 寫錯位置不會報錯，
  但遊戲會把對話框畫出來、裡面一個字都沒有，很容易誤判成字型缺失。
- **A: 必須是真正的軟碟映像（`imgmake`），掛載主機目錄不行。**
  遊戲會檢查 BPB；給目錄的話它會停在只剩一個選項的選單，
  按什麼都只有閃爍。A: 放 `BDISK.VER` 就能解鎖「開始新遊戲」。
- `mount` 吃的是**主機路徑**；`imgmake` 的輸出要寫**純檔名**
  （`imgmake da.img`），給 `c:\da.img` 會失敗。
- 直接跑 `MAIN.EXE` 只有黑畫面 —— `KAMI.COM` 會安裝一個 INT 65h handler
  給它用。`KAMI.COM` 依序執行 `OPEN.EXE` → `MAIN.EXE` → `END.EXE`（`MAIN.EXE`
  以結束碼 0 結束，也就是打倒最終頭目後，才會播 ED）。`tools/install.py` 把
  執行 `OPEN.EXE` 的那段程式碼改成 NOP，藉此跳過兩分鐘的片頭又保留 INT 65h
  （設 `SKIP_OPENING=0` 可關掉）。早期是把 `OPEN.EXE` 字串改成 `MAIN.EXE`，
  結果 `MAIN.EXE` 會跑兩次，破關後回到標題畫面而不是 ED。
  `install.py` 另外產生只播 ED 的 `build/KAMI/ENDING.COM`：
  `env KAMI_START=ENDING.COM tools/dosbox/run.sh`。
- **遊戲選單是滑鼠驅動的。** 畫面上那個橘色方框就是滑鼠游標，Enter 等同
  「在游標位置點一下」，方向鍵完全無效。DOSBox-X 的 `AUTOTYPE` 只能送鍵盤，
  mapper 也沒有滑鼠移動/點擊事件 —— 所以**滑鼠驅動的畫面無法自動化**，
  要人工點。`AUTOTYPE -w <秒> -p <秒> <按鍵>...` 仍可用於送鍵盤
  （`-w` 會延後開始，能跨過 `KAMI.COM` 的交接）。
