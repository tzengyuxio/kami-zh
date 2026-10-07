《神々の大地 ～古事記外伝～》繁體中文化修補程式 @VERSION@
https://github.com/tzengyuxio/kami-zh

本程式只含譯文，不含遊戲本體。需要自備 KOEI 1993 年 DOS/V 版的遊戲檔
（安裝後的 KAMI 資料夾，裡面有 MAIN.EXE、EVENT.DAT 等檔案）。

== 修補 ==

1. 把 kami-zh-patch 放進 KAMI 資料夾（或放在它旁邊），直接執行。
   也可以把 KAMI 資料夾拖到程式圖示上。
2. 程式會在 KAMI 旁邊建立 KAMI_ZH 資料夾，裡面就是中文版。
   原本的 KAMI 資料夾不會被修改。

只支援原版檔案。寫入前會先檢查所有檔案，一次列出不符的檔案與原因
（其他版本、已改過，或複製時就已損毀）：
  - MAIN.EXE、EVENT.DAT 不符時無法修補，不會寫入任何東西。
  - END.EXE（結局）、OPEN.EXE（片頭）、SDATA.CIM（人名、村名）、RPDATA.CIM（魔物名）
    不符時，可以選擇跳過：其他檔案照常中文化，跳過的檔案原樣複製。
    換成完好的原版檔後重新執行，就能完整中文化。

Windows：首次執行若出現「Windows 已保護您的電腦」，按「其他資訊」→「仍要執行」。
macOS：在終端機執行；若被系統擋下，先執行
       xattr -d com.apple.quarantine kami-zh-patch

== 用 DOSBox-X 遊玩 ==

這是 DOS/V（日文 DOS）遊戲，一般的 DOSBox 不支援 DOS/V 的漢字顯示，
請用 DOSBox-X（https://dosbox-x.com/）。

1. 用記事本打開 kami-zh.conf，把 mount c 那行的路徑改成「KAMI_ZH 所在的資料夾」，
   例如 KAMI_ZH 在 D:\Games\KAMI_ZH，就寫 mount c "D:\Games"。
2. 以這份設定啟動 DOSBox-X：
     dosbox-x -conf kami-zh.conf
   Windows 也可以建立 dosbox-x.exe 的捷徑，在「目標」後面加上
     -conf "D:\Games\kami-zh.conf"

設定檔做的事（也可以在 DOSBox-X 裡手動輸入）：
  - [dosv] dosv = jp：開啟日文 DOS/V 模式，才能顯示漢字。
  - 建立兩張空白軟碟映像掛到 A:、B:，並把 BDISK.VER 複製到 A:。
    遊戲會檢查軟碟機；A: 不是真正的軟碟映像時，標題選單會卡住，無法「開始新遊戲」。
  - 從 KAMI.COM 啟動（不能直接執行 MAIN.EXE，會黑畫面）。

遊戲完全用滑鼠操作（橘色方框是游標），鍵盤方向鍵無效。

== 舊存檔 ==

存檔（SAVEDATA.DAT）會記下開新遊戲當時的人名與村名。用日文版的存檔
接著玩，這些名稱會維持日文；建議用中文版重新開始。
