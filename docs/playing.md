# 安裝與遊玩

## 安裝中文版

到 [Releases](https://github.com/tzengyuxio/kami-zh/releases) 下載修補程式
（Windows：`kami-zh-patch-*-windows.zip`；macOS：`*-macos.zip`）。修補程式只含譯文，
需要自備 DOS/V 原版安裝後的 `KAMI` 資料夾。

1. 把 `kami-zh-patch` 放進 `KAMI` 資料夾（或旁邊）執行，也可以把 `KAMI` 資料夾拖到程式上。
2. 程式會在旁邊建立 `KAMI_ZH`，裡面就是中文版；原本的 `KAMI` 不會被修改。
   檔案與支援的原版不符（其他版本或已修改過）時會直接停止，不寫入任何東西。

Windows 首次執行若出現 SmartScreen 警告，按「其他資訊」→「仍要執行」；macOS 若被擋，
先執行 `xattr -d com.apple.quarantine kami-zh-patch`。

## 用 DOSBox-X 遊玩 DOS/V 遊戲

這是日文 DOS/V 遊戲。一般的 DOSBox 不支援 DOS/V，畫面會沒有漢字，請用
[DOSBox-X](https://dosbox-x.com/)。壓縮檔附的 `kami-zh.conf` 已設定好，
把其中 `mount c` 那行改成 `KAMI_ZH` 所在的資料夾後啟動：

```sh
dosbox-x -conf kami-zh.conf
```

（Windows 可建立 `dosbox-x.exe` 的捷徑，在「目標」後加上 `-conf "D:\Games\kami-zh.conf"`。）
也可以不用設定檔，自己在 DOSBox-X 裡操作，要點是：

1. **開啟 DOS/V 模式**：設定檔 `[dosv]` 區段寫 `dosv = jp`（不是 `[dos]` 區段）。
   沒開的話，對話框會畫出來但裡面沒有字。
2. **A: 要是真正的軟碟映像**：遊戲會檢查軟碟機，掛載資料夾當 A: 時，
   標題選單會卡住、無法開始新遊戲。在 DOSBox-X 裡輸入：

   ```
   mount c "D:\Games"
   c:
   imgmake da.img -t fd_1440
   imgmount a c:\da.img -t floppy
   copy c:\KAMI_ZH\BDISK.VER a:\
   cd KAMI_ZH
   KAMI.COM
   ```

3. **從 `KAMI.COM` 啟動**：它會安裝遊戲需要的 INT 65h，直接跑 `MAIN.EXE` 只有黑畫面。
4. **遊戲完全用滑鼠操作**：橘色方框是游標，鍵盤方向鍵無效。

存檔會記下開新遊戲當時的人名與村名，日文版的舊存檔接著玩時這些名稱仍是日文，
建議用中文版重新開始。
