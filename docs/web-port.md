# 網頁版移植筆記（給其他 KOEI DOS/V 中文化專案）

kami-zh 的網頁版（`web/`）是第一個實作。這份筆記把可以沿用到 genpei-zh（《源平合戦》）、
winning-post-zh（《ウイニングポスト》）等同代 KOEI DOS/V 作品的部分整理出來：架構、每款遊戲要換的參數、
js-dos 的行為與踩過的坑、驗證方法。kami-zh 自己的實作細節見 `docs/development.md`「網頁版」。

## 架構

```
玩家的原版檔（資料夾或 zip）
  → 瀏覽器內：SHA-256 驗證 → 套用 .kzp 差異 → 打包成 js-dos bundle（zip：.jsdos/dosbox.conf + 遊戲資料夾）
  → js-dos 8.5.1，backend "dosboxX"（DOSBox-X 的 WebAssembly 版，含 DOS/V）
```

- **不放遊戲資料**：網站只有 HTML、JS 和差異檔（`tools/mkpatch.py` 的 KZP1 格式，只含譯文 bytes）。
  原版檔只在瀏覽器裡讀，存在 IndexedDB，修補在每次開始時重做，所以更新差異檔不必讓玩家重選檔案。
- **純靜態、無建置步驟**：js-dos 與 fflate（解 zip、打包 bundle）從 jsDelivr 載入，版本要釘死。
  js-dos 的 wasm 約 8 MB，不必自己架。
- **存檔**：js-dos 把 bundle 根目錄（模擬器的 C:）的變動存進瀏覽器；`fsChanges.urlToKey` 要回傳固定字串，
  否則 bundle 是 blob URL，每次的鍵都不同，存檔會「消失」。
- **自動保存**：輪詢遊戲的存檔檔（kami 是 `KAMI/SAVEDATA.DAT`），內容變了且下一輪讀到相同（寫完了）
  就呼叫 `props.save()`。不要讓玩家手動按「儲存」——試過，不直覺。
- **快照**：DOSBox-X 狀態快照。`[dosbox]` 設 `savefile = kamistate.sav`、`usesavefile = true`，
  `hand_savestate` 就把快照寫進 bundle 根目錄（kami 約 350 KB），JS 讀出來存進 IndexedDB 的欄位；
  讀取時 `fsWriteFile` 寫回再送 `hand_loadstate`。快照不含磁碟內容，讀快照不影響遊戲內存檔。

## 每款遊戲要換的參數

`web/app.js` 開頭的常數與 `DOSBOX_CONF`：

| 項目 | kami-zh | 移植時確認 |
|---|---|---|
| 遊戲資料夾 | `KAMI` | genpei：`GENPEI`；winning：`WINNING` |
| 啟動器 | `KAMI.COM` | genpei：`Genpei.com`；winning：`WINNING.COM`（與 `KAMI.COM` 同型） |
| 遊戲內存檔檔名 | `SAVEDATA.DAT` | genpei：`SAVEDATA.GP`（Main.exe 內寫死 `C:SAVEDATA.GP`）；winning：`SAVEDATA.DAT`（MAIN／YEAREND.EXE 內寫死） |
| 軟碟設定 | `imgmake` 兩張 1.44M，A: 放 `BDISK.VER` | 照該專案 `tools/dosbox/run.sh` 的 autoexec 搬；genpei 不需要軟碟；winning 三張，A:／B:／**E:** 各放 `ADISK.DIR`／`BDISK.DIR`／`CDISK.DIR` |
| DOSBox 其他設定 | — | 照該專案的 conf 全部搬（genpei 必須 `xms = false`、`ems = emsboard`，否則選完棟梁就卡死）；winning 要 `loadfix`（見下方坑） |
| 跳過片頭 | `KAMI.COM` 內 `OPEN.EXE` exec 的 10 bytes 改 NOP | 各啟動器 offset 不同；沒有就拿掉選項。genpei：`GENPEI.COM` 位移 `0x5A3` 的 `BA 53 05` 改 `EB 1A`（跳到 exec MAIN.EXE）；winning 拿掉（片頭在 `BGSET.EXE`，它還負責設定與 `ORG\` 還原，不能跳過） |
| 差異檔 | `kami-zh.kzp` | 各專案用同一支 `mkpatch.py` 產生 |
| IndexedDB 名稱、`fsChanges` 鍵 | `kami-zh`、`kami-zh.changes` | 同一網域下必須各遊戲不同 |

- genpei-zh 的 `web/app.js` 已把上表參數集中到開頭的 `GAME` 物件（含 DOSBox 設定），移植時只換這個物件。
- **壓縮過的 EXE 要先解包再做差異**：genpei 的 Main.exe 是 RLE 壓縮的，建置用的是解包後的映像。
  直接拿壓縮原檔對建置結果做差異，INSERT 會帶進重建的 MZ 標頭、relocation 表與原版程式碼碎片
  （33.5 KB；解包後只剩 2.7 KB 譯文）。做法：`web.sh` 把原版一側也先解包再跑 `mkpatch.py`，
  `app.js` 在瀏覽器裡用同一套解包（`unpackExe()`）後再驗證與修補。解包失敗就保留原檔，讓 SHA-256 檢查報錯。
  反例：winning 的 `MAIN.EXE` 也是壓縮檔，但它的建置是**就地改壓縮檔、大小不變**，直接做差異只有 5.5 KB，不必解包。
  先看建置怎麼改那支 EXE 再決定。
- **只在建置裡才有的檔不會進差異檔**（`mkpatch.py` 忽略）。winning 的 `install.py` 會建立 `WINNING\ORG\`
  （8 個 `.CIM` 的副本，遊戲開新局時從這裡還原），網頁版要在 `app.js` 打包時自己從修補後的檔案複製出來。
- **檔名大小寫**：DOS 不分大小寫，`app.js` 把玩家選的檔名一律轉大寫當鍵。genpei 的原檔是混合大小寫
  （`Main.exe`），差異檔裡記的檔名查表前也要轉大寫，否則會報「缺少檔案」。
- **字型**：網頁裡沒有系統字型，`getsysfont` 無效；DOSBox-X 會用內建的預設 DOS/V 字型，中文顯示正常
  （kami 實測），只是筆畫與桌面版不同。要指定點陣字型可用 `fontxdbcs` 等 FONTX2 設定。
  genpei 的 `JIS.FNT` 沒有程式讀，`FONT.DAT` 只給 DOSJP.COM 用，兩者在 dosv=jp 下都用不到；
  genpei 主選單用 `ci.screenshot()` 取 640×480 原始畫面，與桌面版（macOS、`getsysfont=true`）逐像素比對，
  只差滑鼠游標，字型完全一致。
- **快照大小因遊戲而異**：genpei 的 `genpeistate.sav` 約 820 KB（kami 約 350 KB）。
- **音樂**：FM 音源（`FMDRV.COM`）在網頁版正常（kami 實測有聲音）。

## js-dos 的行為與坑（8.5.1）

- `Dos(el, options)` 的 options：`backend: "dosboxX"`、`pathPrefix`（指到 `dist/emulators/`）、
  `kiosk: true`（隱藏 js-dos 自己的側欄）、`noCloud: true`、`autoSave: true`（切分頁、離開全螢幕時存）、
  `quickSave: false`（關掉 js-dos 自己的 F6／F7，它只存在記憶體裡、不會保留）、`fsChanges`、`onEvent`。
- `onEvent(event, ci)`：`event === "ci-ready"` 時拿到 CommandInterface，之後才能讀寫檔案。
- CommandInterface 有 `fsTree()`、`fsReadFile(path)`、`fsWriteFile(path, data)`、`fsDeleteFile(path)`、
  `screenshot()`（快照縮圖用）、`sendBackendEvent({ type: "wc-trigger-event", event })`。路徑相對於 bundle 根目錄，
  例如 `KAMI/SAVEDATA.DAT`。
- **`fsReadFile` 讀不存在的檔案時永遠不會回傳**（不是丟錯）。先用 `fsTree()` 確認存在再讀。
- 存快照前先刪掉舊的快照檔：同一畫面連存兩次可能得到完全相同的內容，只比對內容會分不出「寫好了沒」。
- `Dos()` 回傳的 props 有 `save()`、`stop()`、`setAutoSave()` 等；`save()` 存的是 C: 的變動，不是快照。
- 每次開機都 `imgmake` 會讓存進瀏覽器的變動多出數 MB，autoexec 改成 `if not exist da.img imgmake ...`。
- **`loadfix 程式名` 會讓 js-dos 當掉**（wasm `RuntimeError`，每次都會）。桌面版 DOSBox-X 正常。
  要先佔住低 64KB 的遊戲（winning 的壓縮 `MAIN.EXE`）改成兩行：`loadfix > nul`，下一行再執行啟動器。
- **開機偶發當機**：開機約 1.5 秒時偶爾丟 wasm `RuntimeError: null function`（或 `unreachable`），畫面停住。
  約一成機率，kami 的 bundle（24 次中 3 次）、winning（BGSET 單獨執行也會）都有；有視窗的瀏覽器也會，不是
  headless 才有。只跑 `loadfix`、`FMDRV.COM` 不會。js-dos 是跨來源 script，`window` 的 `error` 事件裡
  `e.error` 是 null，只能比對 `e.message`。winning 的做法：開機 15 秒內遇到就重新整理頁面並自動開始（最多 3 次）。
- 在片頭播放中存讀快照，曾出現之後一直黑畫面（未查明，可能只是剛好在淡出）。遊戲本體中存讀正常。
- 譯文更新後，舊快照仍是更新前的記憶體內容（含已載入的舊文字），讀舊快照可能看到舊譯文；遊戲內存檔不受影響。

## 驗證方法（Playwright）

- 本機：`tools/web.sh serve`，或直接在 `web/dist/` 跑 `python3 -m http.server`。
- 選檔：`page.setInputFiles('#pick-zip', '<原版 zip 絕對路徑>')`。
- 點擊遊戲要用真實滑鼠：`page.mouse.move(...)`（分步移動）→ `down()` → `up()`；`browser_click` 對 canvas 不夠。
- 讀模擬器內的檔案、模擬存檔變動：測試時把 `ci` 掛到 `window`（只放在 `web/dist/` 的副本，不進原始碼），
  再用 `page.evaluate` 呼叫 `fsReadFile`／`fsWriteFile`。
- 截圖只能存到 repo 底下（Playwright MCP 的允許路徑），放 `build/` 以免進版控；
  Playwright 會在 repo 根目錄留下 `.playwright-mcp/`，測完刪掉。
- **Playwright MCP 的瀏覽器同時只能給一個 session 用**（另一個 session 占著時報 `Browser is already in use`）。
  改用 `playwright-cli -s=<名稱> open <url>` 開獨立的瀏覽器，再用 `playwright-cli -s=<名稱> run-code "async (page) => {...}"`
  操作。`run-code` 裡沒有 `require`，要存檔就把資料（例如 `ci.screenshot()` 轉成的 data URL）當回傳值印出來，
  再在 shell 解碼；`page.on('dialog')` 在 `run-code` 裡接不到 `confirm()`，要改用 `playwright-cli dialog-accept`。
  `playwright-cli` 會在目前目錄留下 `.playwright-cli/`，測完刪掉。
- 和桌面版比對畫面時，用 `ci.screenshot()` 取模擬器的原始 640×480 畫面，不要拿縮放過的頁面截圖。
  桌面版那一側可用 `run.sh <秒數>` 錄影（ZMBV 無損），`ffmpeg -sseof -1 … -frames:v 1` 取最後一格，選一個會停住等輸入的畫面。
- **滑鼠落點不是 1:1**：js-dos 把整個畫布線性對應到遊戲用 INT 33h 設的游標範圍。winning 的範圍約 632×420，
  遊戲座標 (x, y) 要點畫布的 (x/0.97, y/0.875)，否則按鈕點不到（kami、genpei 沒遇到）。玩家只看到遊戲游標，不受影響。
  先把滑鼠移到幾個已知點、截圖看游標位置就能量出比例。
- `playwright-cli` 的 `setInputFiles` 只能讀它啟動目錄底下的檔案（`outside allowed roots`），原版 zip 要先複製過去。
- Claude Code 裡用背景執行的 `python3 -m http.server` 會被不定時收掉（exit 144，`nohup` 也一樣），
  改成在同一個指令裡起 server、跑測試、再關掉。
- 自動化瀏覽器沒有音效裝置（`sampleRate === 0` 警告），聲音要用一般瀏覽器確認。
- 第一次啟動、還沒有存檔時，自動化瀏覽器裡遊戲曾自己點進「開始新遊戲」與取名確認；有存檔後沒再出現。
  移植時用一般瀏覽器確認一次。

## 多款遊戲怎麼放（2026-10-09 決議）

**單一網頁 repo，吃各專案的差異檔。** 原本的選項「各 repo 各自一份 `web/`」已放棄：三份 `app.js` 各約 500 行，
彼此有 140–180 行不同，已經開始各自分歧，同一個修正要改三次。

- **網站定位**：方便遊玩「中文化過的 DOS 遊戲」的地方，不限光榮，但也不是一般的 DOS 線上遊玩站。
  收錄條件就是這套模式能成立：玩家自備原版檔、網站只提供中文化差異檔。
- **網頁 repo `dosgame-zh`**（放 Forgejo）：共用的播放器（js-dos 啟動、選原版檔、套用差異檔、自動保存、快照與 F6/F7）、
  首頁選遊戲，以及每款遊戲的 manifest（上表的參數）與 `.kzp`。
- **各翻譯 repo**：只產出 `.kzp`（沿用 `mkpatch.py`），不再放網頁程式。建置需要原版遊戲檔，所以 `.kzp` 在本機做好，
  再 commit 進網頁 repo 或附在 release 上（GitHub release 的下載網址沒有 CORS，不能在瀏覽器裡直接抓）。
  `.kzp` 只含譯文 bytes，修補程式本來就公開發佈它。
- **IndexedDB 與 `fsChanges` 鍵依遊戲區分**：三款遊戲在同一網域下。
- **搬遷順序**：以 kami-zh 的 `web/` 為基礎，把三份的差異抽成 manifest，依序接上 genpei-zh、winning-post-zh，
  每接一款都用一般瀏覽器實際跑一次；三款都能跑之後，再刪除各 repo 的 `web/`，只留產生 `.kzp` 的步驟。

**部署**：自己的 VPS，不用 GitHub Pages。

- repo 在 Forgejo，GitHub Pages 得另外鏡像到 GitHub。
- 網站是純靜態：Forgejo Actions 建置後 rsync 到 VPS，由 Caddy 之類的伺服器提供。
- 用自己的網域（子網域待定，可能掛在 `simagame.me` 底下，`cdosgame.simagame.me` 已在那裡）。網域一開始就要定好：IndexedDB 依網域區分，換網域等於讓玩家的原版檔與快照全部重來。
- 流量很小：js-dos 的 wasm 從 jsDelivr 載入，網站本身只提供頁面與 `.kzp`。

另一個網站 `koei-kao`（光榮臉譜工具，由大眾臉探索器擴大而成）也採同樣的分工，見 genpei-zh
`docs/backlog/mob-kao-explorer-integration.md`。
