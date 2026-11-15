# 介面範例（其他程式 ↔ fyy）

這裡每個 `.json` 是一則「對方實際會送來的請求」或「對方實際會回的內容」，
照對方程式碼抄下來的。`tests/test_contracts.py` 會逐一拿來打 fyy。

**要改介面格式時**：先改這裡的範例，再改 fyy；另一邊的對話拿同一份範例去對。
範例裡的 `__FEEDBACK_TOKEN__` 是佔位字，測試時換成測試用權杖，真的權杖不放進 repo。

| 檔案 | 誰送的 | 來源程式碼 |
|---|---|---|
| `feedback_desktop.json` | 地籍便民系統(意見回饋) | `landreg-desktop/main.py` 送 `FEEDBACK_URL` 那段 |
| `feedback_landmap.json` | 阿生地圖(緊急推播) | `landmap/server/landreg.py` `push_line()` |
| `report_push_daily.json` | 阿生地圖(每日檢查) | `landmap/server/owner_daily_check.py` |
| `report_push_watch.json` | 阿生地圖(守門員) | `landmap/tools/watch_site.py` `_push_watch_report()` |
| `cadastral_fail.json` | 地籍圖處理工具 | `landreg-desktop/cadastral_v03/fail_report.py` `send()` |
| `landmap_auth_company.json` | 阿生地圖回給 fyy | `landmap/server/app.py` `/api/auth/company` |
| `landmap_intel_line.json` | fyy 送給阿生地圖 | `fyy/app.py` `_intel_call()` → `landmap` `/api/intel/line` |

通訊錄三個端點(`/contacts/download`、`/meta`、`/upload`)的請求只有標頭沒有內容，
直接寫在 `tests/test_contacts.py`，對應 `landreg-desktop/main.py` 的 `_contacts_headers()`。
