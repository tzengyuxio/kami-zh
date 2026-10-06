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
| 遊戲內存檔檔名 | `SAVEDATA.DAT` | genpei 是 `Savedata.gp`；winning 待查 |
| 軟碟設定 | `imgmake` 兩張 1.44M，A: 放 `BDISK.VER` | 照該專案 `tools/dosbox/run.sh` 的 autoexec 搬 |
| 跳過片頭 | `KAMI.COM` 內 `OPEN.EXE` exec 的 10 bytes 改 NOP | 各啟動器 offset 不同；沒有就拿掉選項 |
| 差異檔 | `kami-zh.kzp` | 各專案用同一支 `mkpatch.py` 產生 |
| IndexedDB 名稱、`fsChanges` 鍵 | `kami-zh`、`kami-zh.changes` | 同一網域下必須各遊戲不同 |

- **檔名大小寫**：DOS 不分大小寫，`app.js` 把玩家選的檔名一律轉大寫當鍵。genpei 的原檔是混合大小寫
  （`Main.exe`），差異檔裡記的檔名查表前也要轉大寫，否則會報「缺少檔案」。
- **字型**：網頁裡沒有系統字型，`getsysfont` 無效；DOSBox-X 會用內建的預設 DOS/V 字型，中文顯示正常
  （kami 實測），只是筆畫與桌面版不同。要指定點陣字型可用 `fontxdbcs` 等 FONTX2 設定。
  genpei 有自己的 `JIS.FNT`／`FONT.DAT`，要先確認它是否走 DOS/V 字型。
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
- 自動化瀏覽器沒有音效裝置（`sampleRate === 0` 警告），聲音要用一般瀏覽器確認。
- 第一次啟動、還沒有存檔時，自動化瀏覽器裡遊戲曾自己點進「開始新遊戲」與取名確認；有存檔後沒再出現。
  移植時用一般瀏覽器確認一次。

## 多款遊戲怎麼放（待決定）

1. **各 repo 各自一份 `web/`**：每個專案獨立部署（例如 `tzengyuxio.github.io/<repo>/`），
   複製 `app.js` 改參數。最簡單、互不影響；缺點是同一個修正要改三份。
2. **單一網頁 repo，吃各專案的差異檔**：播放器程式只有一份，由每款遊戲的 manifest（上表的參數）驅動，
   首頁選遊戲。差異檔在建置網站時從各專案的 release 取得（GitHub release 的下載網址沒有 CORS，
   不能在瀏覽器裡直接抓），各專案的 release 流程要多產出 manifest 與 `.kzp`。
   同一網域下 IndexedDB 與 `fsChanges` 鍵要依遊戲區分。
