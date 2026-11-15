# fyy（阿生生 LINE 機器人）

Flask + line-bot-sdk，部署在 Render（`https://fyy-l8a3.onrender.com`），資料存 MongoDB。
主要程式在 `app.py`。

## 改程式的規矩

1. **推上去之前先跑測試**，全過才推：
   ```
   pip install -r requirements.txt -r requirements-dev.txt
   python -m pytest -q
   ```
   全部在本機跑（假的 LINE、假的 MongoDB、假的對外連線），不到一秒，不會真的推播或連資料庫。
2. **修了一個問題，就補一個對應的測試案例**，讓同一個問題不會再回來。
3. **不可以為了讓測試通過而刪掉、跳過測試**。測試失敗時先判斷是程式錯還是預期變了；預期變了才改測試，並在回報裡說明。
4. 測試過了不代表線上沒問題（假的 LINE、假的阿生地圖不會跟真的完全一樣）。上線後仍要靠守門員／每日檢查。

## 跟其他程式的介面

fyy 不是獨立的，下面這些端點有別的程式在呼叫。**要改格式，先改 `tests/contracts/` 的範例，再改程式**，
並告訴使用者另一邊也要跟著改。

| 端點 | 誰在呼叫 | repo |
|---|---|---|
| `/feedback` | 地籍便民系統意見回饋；阿生地圖緊急推播 | `landreg-desktop`、`landmap` |
| `/report_push` | 阿生地圖每日檢查、守門員 | `landmap` |
| `/cadastral_fail` | 地籍圖處理工具 | `landreg-desktop`（`cadastral_v03/fail_report.py`） |
| `/contacts/download`、`/meta`、`/upload` | 地籍便民系統通訊錄同步 | `landreg-desktop`（`main.py`） |
| `/help`、`/help_img/*`、`/install`、`/download` | 地籍便民系統、LINE 選單 | `landreg-desktop`、`tw-land-tools`(安裝檔) |

fyy 自己會去呼叫阿生地圖（`map.windsky-sky.com`）：
`/api/auth/company`（通訊錄確認是不是同事）、`/api/intel/line`（最新行情情報綁定與存檔）。
兩者的回應樣子也在 `tests/contracts/`。

權杖 `FEEDBACK_TOKEN`、`CONTACTS_DL_TOKEN`、`CONTACTS_ADMIN_TOKEN` 是 Render 環境變數，
要跟對方程式設定的值一致。真的權杖不可以寫進 repo 或測試。

## 跨專案協作紀錄（fyy・阿生地圖・地籍資料查詢系統）

- 三個專案各自有對話在改，使用者喜歡**直接改、不開 PR**（直接推 main），但改了要讓別人知道。紀錄放在阿生地圖 repo（私有）的 `協作紀錄.md`。
- **開工前**先看最上面幾則（新的在上面），有寫到要 fyy 跟著做的，先跟使用者提：
  `gh api repos/windskyshao/landmap/contents/協作紀錄.md -H "Accept: application/vnd.github.raw"`
- **改完**會影響別的專案的東西（上面「跟其他程式的介面」那些端點、權杖、回應格式）：在 `協作紀錄.md` 最上面加一則
  （本機有阿生地圖就用 `python tools/collab_note.py "fyy" "改了什麼" "影響" "誰要跟著做"`，會順便寄信給使用者；
  雲端就用 GitHub 網頁或 `gh api` 直接改），並在回覆裡明白告訴使用者要通知哪個對話。
- 推完程式用 `https://fyy-l8a3.onrender.com/version` 確認 Render 換上新版（回 commit 前 7 碼，約 2 分鐘）。
- 這個 repo 是**私有**的（2026-11-15 起）。Render 用使用者的 GitHub 帳號（Render GitHub App，已開放 fyy）抓程式部署。
  若推上去後 `/version` 一直沒換新版，先看 Render 服務的 Events 頁有沒有抓程式失敗；不行就暫時改回公開並告訴使用者。
  權杖、帳密、個人資料仍一律放 Render 環境變數，不寫進 repo。

## 測試檔對照

- `tests/conftest.py`：假的 LINE / MongoDB / 對外連線，`say('檢查', uid=...)` 模擬使用者傳訊息
- `tests/test_contracts.py`：拿 `tests/contracts/` 的範例打各端點
- `tests/test_feedback.py`：回饋速率限制、截圖、失敗回報、報告存放
- `tests/test_contacts.py`：通訊錄權限（阿生地圖登入、同事驗證、舊權杖過渡期、連不上時的退路）
- `tests/test_line_commands.py`：LINE 指令（安裝、檢查、守門員、綁定、轉傳情報）
- `tests/test_pages.py`：安裝頁、使用說明、`/download`
- `tests/test_oil_cron.py`：油價推播（不調整不推、不重複推）
