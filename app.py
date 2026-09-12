# -- coding: utf-8 --**
#載入LineBot所需要的套件
from flask import Flask, request, abort, Response
from linebot import (LineBotApi, WebhookHandler, exceptions)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import *
import re
import requests
from line_bot import *
from bs4 import BeautifulSoup 
import twstock
import yfinance as yf
import pandas as pd
import datetime
import Msg_Template
import EXRate
import mongodb
import twder
import json
import time
import place
import realestate
import os
import uuid
import base64
from urllib.parse import quote_plus

def get_stock_name(code):
    """取得股票中文名稱，查不到就回傳英文或代號"""
    try:
        info = twstock.codes.get(code)
        if info:
            return info.name
    except:
        pass
    for suffix in ('.TW', '.TWO'):
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            name = ticker.info.get('shortName')
            if name:
                return name
        except:
            pass
    return code

def get_stock_history(code, period="1d"):
    """取得股票歷史價，先試上市(.TW)再試上櫃(.TWO)。回傳 hist 或 None"""
    for suffix in ('.TW', '.TWO'):
        try:
            ticker = yf.Ticker(f"{code}{suffix}")
            hist = ticker.history(period=period)
            if hist is not None and not hist.empty:
                return hist
        except Exception:
            pass
    return None

def build_stock_detail_flex(text, user_name, search_keyword=None):
    """組裝股票詳情 flex，含關注按鈕與設定條件按鈕。
    text: 股票代號（4-6 位數字）
    回傳 FlexSendMessage 或 None（查無資料）
    """
    hist = pd.DataFrame()
    for attempt in range(2):
        got = get_stock_history(text, "7d")
        if got is not None:
            hist = got
            break
        if attempt == 0:
            time.sleep(1)
    if hist.empty:
        return None
    latest = hist.iloc[-1]
    prev_close = hist.iloc[-2]["Close"] if len(hist) >= 2 else latest["Open"]
    change = latest["Close"] - prev_close
    change_pct = (change / prev_close) * 100 if prev_close != 0 else 0
    arrow = "▲" if change >= 0 else "▼"
    change_color = "#FF3B30" if change >= 0 else "#34C759"
    stock_name = get_stock_name(text)
    current_price = f"{latest['Close']:.2f}"
    history_items = []
    for date, row in hist.iloc[::-1].iterrows():
        history_items.append({
            "type": "box", "layout": "horizontal",
            "contents": [
                {"type": "text", "text": date.strftime("%m/%d"), "size": "sm", "color": "#888888", "flex": 3},
                {"type": "text", "text": f"{row['Close']:.2f}", "size": "sm", "align": "end", "flex": 3},
                {"type": "text", "text": f"{int(row['Volume']):,}", "size": "xxs", "align": "end", "color": "#aaaaaa", "flex": 4}
            ]
        })
    is_followed = mongodb.is_stock_followed(user_name, text)
    # 查使用者目前對這檔的條件設定，在 footer 顯示
    current_condition_text = None
    try:
        db = mongodb.constructor_stock()
        entry = db[user_name].find_one({"favorite_stock": text})
        if entry:
            cond = entry.get('condition', '')
            tgt = entry.get('price', '0')
            if tgt and tgt != '0' and cond in ('<', '>'):
                cond_word = '低於' if cond == '<' else '高於'
                current_condition_text = f"📌 目前條件：{cond_word} {tgt}"
    except Exception:
        pass
    stock_quick_reply = None
    if search_keyword:
        other_results = [(c, n) for c, n in search_stock_by_name(search_keyword) if c != text]
        if other_results:
            stock_quick_reply = QuickReply(items=[
                QuickReplyButton(action=MessageAction(label=f"{n} {c}", text=f"#{c}@{search_keyword}"))
                for c, n in other_results[:8]
            ])
    return FlexSendMessage(
        alt_text=f"{text} 股價查詢",
        contents={
            "type": "bubble",
            "header": {
                "type": "box", "layout": "vertical",
                "contents": [
                    {
                        "type": "box", "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": stock_name, "weight": "bold", "size": "xl", "color": "#333333", "flex": 0},
                            {"type": "text", "text": text, "size": "md", "color": "#888888", "gravity": "center", "flex": 1, "margin": "md"},
                            {"type": "box", "layout": "vertical", "flex": 0, "width": "70px", "height": "30px",
                             "contents": [
                                 {"type": "text", "align": "center", "gravity": "center", "size": "xs", "weight": "bold",
                                  "text": "★已關注" if is_followed else "☆關注",
                                  "color": "#FFFFFF" if is_followed else "#888888"}
                             ],
                             "backgroundColor": "#FF5252" if is_followed else "#EEEEEE",
                             "cornerRadius": "15px", "justifyContent": "center", "alignItems": "center",
                             "action": {
                                 "type": "postback",
                                 "label": "★已關注" if is_followed else "☆關注",
                                 "data": f"action=unfollow&stock={text}" if is_followed else f"action=follow&stock={text}"
                             }}
                        ]
                    },
                    {
                        "type": "box", "layout": "horizontal", "margin": "md",
                        "contents": [
                            {"type": "text", "text": current_price, "size": "xxl", "weight": "bold", "color": change_color},
                            {
                                "type": "box", "layout": "vertical", "margin": "md",
                                "contents": [
                                    {"type": "text", "text": f"{arrow} {abs(change):.2f} ({abs(change_pct):.2f}%)", "size": "sm", "color": change_color, "align": "end"}
                                ],
                                "justifyContent": "center"
                            }
                        ]
                    }
                ],
                "paddingAll": "15px",
                "backgroundColor": "#FAFAFA"
            },
            "body": {
                "type": "box", "layout": "vertical",
                "contents": [
                    {
                        "type": "box", "layout": "horizontal",
                        "contents": [
                            {"type": "box", "layout": "vertical", "contents": [
                                {"type": "text", "text": "開盤", "size": "xs", "color": "#888888"},
                                {"type": "text", "text": f"{latest['Open']:.2f}", "size": "sm", "weight": "bold"}
                            ], "flex": 1},
                            {"type": "box", "layout": "vertical", "contents": [
                                {"type": "text", "text": "最高", "size": "xs", "color": "#888888"},
                                {"type": "text", "text": f"{latest['High']:.2f}", "size": "sm", "weight": "bold", "color": "#FF3B30"}
                            ], "flex": 1},
                            {"type": "box", "layout": "vertical", "contents": [
                                {"type": "text", "text": "最低", "size": "xs", "color": "#888888"},
                                {"type": "text", "text": f"{latest['Low']:.2f}", "size": "sm", "weight": "bold", "color": "#34C759"}
                            ], "flex": 1},
                            {"type": "box", "layout": "vertical", "contents": [
                                {"type": "text", "text": "成交量", "size": "xs", "color": "#888888"},
                                {"type": "text", "text": f"{int(latest['Volume']):,}", "size": "sm", "weight": "bold"}
                            ], "flex": 1}
                        ]
                    },
                    {"type": "separator", "margin": "lg"},
                    {
                        "type": "box", "layout": "horizontal", "margin": "lg",
                        "contents": [
                            {"type": "text", "text": "日期", "size": "xs", "color": "#888888", "weight": "bold", "flex": 3},
                            {"type": "text", "text": "收盤價", "size": "xs", "color": "#888888", "weight": "bold", "align": "end", "flex": 3},
                            {"type": "text", "text": "成交量", "size": "xs", "color": "#888888", "weight": "bold", "align": "end", "flex": 4}
                        ]
                    }
                ] + history_items,
                "paddingAll": "15px",
                "spacing": "sm"
            },
            "footer": {
                "type": "box", "layout": "vertical",
                "contents": ([
                    {"type": "text", "text": current_condition_text, "size": "sm", "color": "#1DB446", "align": "center", "weight": "bold", "margin": "sm"}
                ] if current_condition_text else []) + [
                    {"type": "text", "text": "📌 設定通知條件", "size": "xs", "color": "#888888", "align": "center", "weight": "bold", "margin": "md"},
                    {
                        "type": "box", "layout": "horizontal",
                        "contents": [
                            {"type": "button", "style": "secondary", "height": "sm", "flex": 1,
                             "action": {"type": "message", "label": f"📈 高於 {current_price}", "text": f"關注{text}>{current_price}"}},
                            {"type": "button", "style": "secondary", "height": "sm", "flex": 1,
                             "action": {"type": "message", "label": f"📉 低於 {current_price}", "text": f"關注{text}<{current_price}"}}
                        ], "spacing": "sm"
                    },
                    {
                        "type": "box", "layout": "horizontal",
                        "contents": [
                            {"type": "button", "style": "link", "height": "sm", "flex": 1,
                             "action": {"type": "message", "label": "✏️ 自訂高於", "text": f"自訂股條{text}>"}},
                            {"type": "button", "style": "link", "height": "sm", "flex": 1,
                             "action": {"type": "message", "label": "✏️ 自訂低於", "text": f"自訂股條{text}<"}}
                        ], "spacing": "sm"
                    },
                    {"type": "separator", "margin": "sm"},
                    {"type": "text", "text": "📊 K線圖", "size": "xs", "color": "#888888", "align": "center", "weight": "bold", "margin": "sm"},
                    {
                        "type": "box", "layout": "horizontal",
                        "contents": [
                            {"type": "button", "style": "primary", "color": "#1DB446", "height": "sm", "flex": 1,
                             "action": {"type": "message", "label": "3個月", "text": f"@K{text} 3m"}},
                            {"type": "button", "style": "primary", "color": "#2196F3", "height": "sm", "flex": 1,
                             "action": {"type": "message", "label": "半年", "text": f"@K{text} 6m"}}
                        ], "spacing": "sm"
                    },
                    {
                        "type": "box", "layout": "horizontal",
                        "contents": [
                            {"type": "button", "style": "primary", "color": "#FF9800", "height": "sm", "flex": 1,
                             "action": {"type": "message", "label": "1年", "text": f"@K{text} 1y"}},
                            {"type": "button", "style": "primary", "color": "#9C27B0", "height": "sm", "flex": 1,
                             "action": {"type": "message", "label": "2年", "text": f"@K{text} 2y"}}
                        ], "spacing": "sm"
                    },
                    {"type": "button", "style": "link", "height": "sm",
                     "action": {"type": "message", "label": "↩ 返回股價查詢", "text": "股價查詢"}}
                ],
                "spacing": "sm", "paddingAll": "10px"
            }
        },
        quick_reply=stock_quick_reply
    )

def is_trading_hours():
    """判斷現在是否為台股盤中時段（週一至週五 09:00-14:00 Asia/Taipei）

    台股正規盤 9:00-13:30，這裡上界放寬到 14:00 給 30 分鐘緩衝，
    讓設在 13:35 / 13:45 的 cron 也能正常執行（盤後幾分鐘的價格與收盤相同）。
    Render 在 UTC 跑，台灣沒有日光節約時間，固定 +8 即可。
    """
    now_tw = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    if now_tw.weekday() >= 5:  # 5=週六, 6=週日
        return False
    minutes = now_tw.hour * 60 + now_tw.minute
    return 9 * 60 <= minutes <= 14 * 60

def get_sell_rate(currency):
    """取得賣出匯率，優先即期、fallback 到現金（韓元/泰銖等弱勢貨幣無即期資料時使用）

    回傳 (rate_str, rate_type)：rate_type 為 '即期' 或 '現金'；皆無資料時回傳 (None, None)
    """
    try:
        rate, _ = EXRate.now_rate(currency)   # 臺銀被反爬蟲擋→改用 open.er-api.com 中價
        if rate:
            return f"{rate:.4f}", '參考'
    except Exception:
        pass
    return None, None

def search_stock_by_name(keyword, max_results=10):
    """用中文名稱搜尋股票代號（只搜普通股與 ETF，排除權證、牛熊證等衍生商品）"""
    results = []
    allowed_types = {'股票', 'ETF'}
    try:
        for code, info in twstock.codes.items():
            if keyword in info.name and info.market == '上市' and info.type in allowed_types:
                results.append((code, info.name))
            if len(results) >= max_results:
                break
        if len(results) < max_results:
            for code, info in twstock.codes.items():
                if keyword in info.name and info.market == '上櫃' and info.type in allowed_types:
                    results.append((code, info.name))
                if len(results) >= max_results:
                    break
    except:
        pass
    return results
from flask import send_from_directory
#=================這裡是呼叫的內容=====================

app = Flask(__name__)
IMGUR_CLIENT_ID = os.environ.get('IMGUR_CLIENT_ID', '')
access_token = os.environ.get('CHANNEL_ACCESS_TOKEN', '')
mat_d={}


def show_loading(user_id, seconds=25):
    """在聊天室顯示「…」載入動畫(告知正在查詢中)。查詢較久的功能開頭呼叫，不佔訊息數。"""
    if not user_id or not access_token:
        return
    try:
        requests.post("https://api.line.me/v2/bot/chat/loading/start",
                      headers={"Authorization": "Bearer " + access_token, "Content-Type": "application/json"},
                      json={"chatId": user_id, "loadingSeconds": max(5, min(60, seconds))}, timeout=4)
    except Exception:
        pass

# 圖片暫存資料夾
CHART_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'charts')
os.makedirs(CHART_DIR, exist_ok=True)
RENDER_URL = 'https://fyy-l8a3.onrender.com'

@app.route('/charts/<filename>')
def serve_chart(filename):
    return send_from_directory(CHART_DIR, filename)


# 📖 地籍資料查詢系統使用說明（給 LINE「使用說明」按鈕連結用）
@app.route('/help')
def help_page():
    _here = os.path.dirname(os.path.abspath(__file__))
    return send_from_directory(_here, 'help.html')


# 📷 使用說明裡的介面截圖（help_img 資料夾）
@app.route('/help_img/<filename>')
def help_img(filename):
    _img_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'help_img')
    return send_from_directory(_img_dir, filename)


# 🔧 意見回饋：推播對象預設＝管理員本人（已知 userId），可用環境變數覆蓋
ADMIN_USER_ID = os.environ.get('ADMIN_USER_ID', 'U60ff9aa248221639d7717bf54d1db609')
# 🔧 意見回饋端點的簡單權杖；未設定環境變數時不檢查（方便先測，要鎖再設）
FEEDBACK_TOKEN = os.environ.get('FEEDBACK_TOKEN', '')


# 🔧 意見回饋接收端點：主程式(main.py)把「截圖+版本+訊息」POST 到這裡，
#    伺服器存截圖取得網址後，推播到管理員的 LINE（阿生生聊天室）。
@app.route('/feedback', methods=['POST'])
def feedback():
    # 同時支援 JSON(截圖用 base64，主程式走這條) 與 multipart(用 curl 測試)
    if request.is_json:
        d = request.get_json(silent=True) or {}
        token = request.headers.get('X-Feedback-Token', '') or d.get('token', '')
        version = (d.get('version') or '未知').strip()
        name = (d.get('name') or '匿名').strip()
        category = (d.get('category') or '').strip()
        message = (d.get('message') or '(無內容)').strip()
        b64 = d.get('screenshot_b64') or ''
        hostname = (d.get('hostname') or '').strip()
        username = (d.get('username') or '').strip()
        lan_ip = (d.get('lan_ip') or '').strip()
    else:
        token = request.headers.get('X-Feedback-Token', '') or request.form.get('token', '')
        version = (request.form.get('version') or '未知').strip()
        name = (request.form.get('name') or '匿名').strip()
        category = (request.form.get('category') or '').strip()
        message = (request.form.get('message') or '(無內容)').strip()
        b64 = ''
        hostname = (request.form.get('hostname') or '').strip()
        username = (request.form.get('username') or '').strip()
        lan_ip = (request.form.get('lan_ip') or '').strip()

    # 1) 權杖驗證（擋亂打）；未設定 FEEDBACK_TOKEN 時不檢查
    if FEEDBACK_TOKEN and token != FEEDBACK_TOKEN:
        return ('forbidden', 403)
    if not ADMIN_USER_ID:
        return ('admin not set', 500)

    # 2) 組文字訊息
    lines = ['📩 新意見回饋', f'版本：{version}']
    if category:
        lines.append(f'類型：{category}')
    lines.append(f'來自：{name}')
    lines.append(f'內容：{message}')
    # 補上可辨識資訊（匿名回饋也能查到是誰/哪台）：對外真實IP由連線取得，區網IP/電腦/使用者由主程式帶上
    real_ip = (request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or '')
    if username:
        lines.append(f'使用者：{username}')
    if hostname:
        lines.append(f'電腦：{hostname}')
    if lan_ip:
        lines.append(f'區網IP：{lan_ip}')
    if real_ip:
        lines.append(f'對外IP：{real_ip}')
    messages = [TextSendMessage(text='\n'.join(lines))]

    # 3) 截圖（選填）：取得 bytes（base64 或 multipart 檔），存進 charts/ 取得公開網址
    img_bytes = None
    if b64:
        try:
            img_bytes = base64.b64decode(b64)
        except Exception as e:
            print(f'[feedback] base64 解碼失敗: {e}')
    elif not request.is_json:
        fileobj = request.files.get('screenshot')
        if fileobj and fileobj.filename:
            img_bytes = fileobj.read()
    if img_bytes:
        fname = f'feedback_{uuid.uuid4().hex[:10]}.png'
        try:
            with open(os.path.join(CHART_DIR, fname), 'wb') as f:
                f.write(img_bytes)
            url = f'{RENDER_URL}/charts/{fname}'
            messages.append(ImageSendMessage(original_content_url=url, preview_image_url=url))
        except Exception as e:
            print(f'[feedback] 存截圖失敗: {e}')

    # 4) 推播給管理員
    try:
        line_bot_api.push_message(ADMIN_USER_ID, messages)
        return ('ok', 200)
    except Exception as e:
        print(f'[feedback] push 失敗: {e}')
        return ('push failed', 500)


# 📇 通訊錄雲端同步：檔案存 MongoDB(私密)，主程式用戶端下載/上傳；避免個資進公開 GitHub。
CONTACTS_DL_TOKEN = os.environ.get('CONTACTS_DL_TOKEN', 'ksp-contacts-dl-2026')      # 下載(輕量token)
CONTACTS_ADMIN_TOKEN = os.environ.get('CONTACTS_ADMIN_TOKEN', '')                    # 上傳(僅管理者，務必在Render設強密碼)


@app.route('/report_push', methods=['POST'])
def report_push():
    """雲端(landmap)把每日檢查報告推過來存著；你傳「檢查」時機器人直接回這份。
    ★方向很重要：機器人主動打雲端會被 Cloudflare 擋(機房 IP)，但雲端打機器人是通的。
    權杖沿用 FEEDBACK_TOKEN。存 MongoDB(Render 免費方案會休眠重啟，記憶體會清空)。"""
    token = request.headers.get('X-Feedback-Token', '') or (request.get_json(silent=True) or {}).get('token', '')
    if FEEDBACK_TOKEN and token != FEEDBACK_TOKEN:
        return ('forbidden', 403)
    d = request.get_json(silent=True) or {}
    text = (d.get('text') or '').strip()
    if not text:
        return ('empty', 400)
    import datetime as _dt
    payload = json.dumps({'text': text, 'at': d.get('at', ''), 'ok': d.get('ok'),
                          'failed': d.get('failed'), 'changes': d.get('changes')}, ensure_ascii=False)
    try:
        mongodb.save_app_file('landmap_daily_report', base64.b64encode(payload.encode('utf-8')).decode(),
                              _dt.datetime.now().isoformat(timespec='seconds'))
    except Exception as e:
        return (f'save failed: {e}', 500)
    return ('ok', 200)


@app.route('/contacts/download', methods=['GET'])
def contacts_download():
    """用戶端下載最新通訊錄(xlsx bytes)。輕量 token 防亂打。"""
    token = request.headers.get('X-Contacts-Token', '') or request.args.get('token', '')
    if CONTACTS_DL_TOKEN and token != CONTACTS_DL_TOKEN:
        return ('forbidden', 403)
    try:
        data_b64, updated = mongodb.get_app_file('contacts_xlsx')
    except Exception as e:
        print(f'[contacts] 讀取失敗: {e}')
        return ('db error', 500)
    if not data_b64:
        return ('not found', 404)
    try:
        raw = base64.b64decode(data_b64)
    except Exception as e:
        print(f'[contacts] base64 解碼失敗: {e}')
        return ('decode error', 500)
    resp = Response(raw, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    resp.headers['X-Contacts-Updated'] = updated or ''
    resp.headers['Content-Disposition'] = 'attachment; filename="contacts.xlsx"'
    return resp


@app.route('/contacts/upload', methods=['POST'])
def contacts_upload():
    """管理者上傳通訊錄(multipart file 欄位)。需強 token CONTACTS_ADMIN_TOKEN(只有管理者電腦有)。"""
    token = request.headers.get('X-Contacts-Admin-Token', '') or request.form.get('token', '')
    if not CONTACTS_ADMIN_TOKEN or token != CONTACTS_ADMIN_TOKEN:
        return ('forbidden', 403)
    fileobj = request.files.get('file')
    if not fileobj or not fileobj.filename:
        return ('no file', 400)
    raw = fileobj.read()
    if not raw or len(raw) < 100:
        return ('empty', 400)
    import datetime as _dt
    try:
        mongodb.save_app_file('contacts_xlsx', base64.b64encode(raw).decode(),
                              _dt.datetime.now().isoformat(timespec='seconds'))
    except Exception as e:
        print(f'[contacts] 儲存失敗: {e}')
        return ('db error', 500)
    return ({'ok': True, 'size': len(raw)}, 200)


@app.route('/contacts/meta', methods=['GET'])
def contacts_meta():
    """輕量查詢：只回雲端通訊錄的更新時間，用來讓用戶端判斷有無新版（不回檔案本體）。"""
    token = request.headers.get('X-Contacts-Token', '') or request.args.get('token', '')
    if CONTACTS_DL_TOKEN and token != CONTACTS_DL_TOKEN:
        return ('forbidden', 403)
    try:
        _b64, updated = mongodb.get_app_file('contacts_xlsx')
    except Exception as e:
        print(f'[contacts] meta 讀取失敗: {e}')
        return ('db error', 500)
    return ({'updated': updated or '', 'exists': bool(_b64)}, 200)


def build_currency_alert_flex(currency_data, new_trigger_count, currently_triggered):
    """組裝匯率通知 flex：列出所有關注幣別，區分「剛達標」與「持續達標」"""
    rows = []
    for d in currency_data:
        if d['rate'] > 0:
            rate_text = f"{d['rate']} (現金)" if d['rate_type'] == '現金' else str(d['rate'])
        else:
            rate_text = '無資料'
        if d.get('is_new'):
            status_text = f"🔔 剛達標！{'低於' if d['condition'] == '<' else '高於'} {d['price']}"
            status_color = "#FF5252"
            status_weight = "bold"
        elif d['triggered']:
            status_text = f"✅ 持續{'低於' if d['condition'] == '<' else '高於'} {d['price']}"
            status_color = "#1DB446"
            status_weight = "regular"
        elif d['condition'] == '未設定':
            status_text = "未設定條件"
            status_color = "#888888"
            status_weight = "regular"
        else:
            status_text = f"條件：{d['condition']}{d['price']}（未達）"
            status_color = "#FF9800"
            status_weight = "regular"
        rows.append({
            "type": "box", "layout": "horizontal", "margin": "lg",
            "contents": [
                {"type": "text", "text": d['cur_name'], "size": "sm", "color": "#333333", "flex": 2},
                {"type": "text", "text": rate_text, "size": "sm", "weight": "bold", "align": "end", "flex": 2, "color": "#2196F3"},
            ]
        })
        rows.append({"type": "text", "text": status_text, "size": "xxs", "color": status_color, "weight": status_weight, "margin": "sm"})
    subtitle = f"剛有 {new_trigger_count} 項達成條件"
    if currently_triggered > new_trigger_count:
        subtitle += f"（另有 {currently_triggered - new_trigger_count} 項持續達標中）"
    return FlexSendMessage(
        alt_text=f"📢 匯率通知（{new_trigger_count} 項剛達標）",
        contents={
            "type": "bubble",
            "header": {
                "type": "box", "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "📢 匯率通知", "weight": "bold", "size": "lg", "color": "#FF5252"},
                    {"type": "text", "text": subtitle, "size": "xs", "color": "#888888", "margin": "sm", "wrap": True}
                ], "paddingAll": "15px"
            },
            "body": {
                "type": "box", "layout": "vertical",
                "contents": rows,
                "paddingAll": "15px"
            },
            "footer": {
                "type": "box", "layout": "vertical",
                "contents": [
                    {"type": "button", "style": "primary", "color": "#2196F3", "height": "sm",
                     "action": {"type": "message", "label": "查看我的外幣", "text": "我的外幣"}}
                ], "paddingAll": "10px"
            }
        }
    )

@app.route('/cron/check_currency')
def cron_check_currency():
    """排程自動檢查匯率條件並推播通知

    交叉觸發 + 一次性失效：只在「從未達 → 剛達標」當次推播。
    達標期間每天檢查但不重複推；條件鬆開（rate 跨回）後 notified 重置，
    下次再達標時又會推一次。
    """
    try:
        db = mongodb.constructor_currency()
        nameList = db.list_collection_names()
        notified = 0
        for col_name in nameList:
            collect = db[col_name]
            entries = list(collect.find({"tag": "currency"}))
            currency_data = []
            new_trigger_count = 0
            currently_triggered = 0
            uid = None
            for entry in entries:
                if uid is None:
                    uid = entry.get('userID')
                currency = entry.get('favorite_currency')
                condition = entry.get('condition', '未設定')
                price = entry.get('price', '未設定')
                notified_before = bool(entry.get('notified', False))
                rate_val, rate_type = get_sell_rate(currency)
                rate = float(rate_val) if rate_val is not None else 0
                cur_name = mongodb.currency_list.get(currency, currency)
                triggered = False
                if condition != '未設定' and price != '未設定' and rate > 0:
                    try:
                        target = float(price)
                        if condition == '<' and rate < target:
                            triggered = True
                        elif condition == '>' and rate > target:
                            triggered = True
                    except ValueError:
                        pass
                # 同步 notified 狀態：達標→True，鬆開→False
                if triggered != notified_before:
                    try:
                        mongodb.update_currency_notified(col_name, currency, triggered)
                    except Exception as e:
                        print(f"[cron] Update notified failed {col_name}/{currency}: {e}")
                is_new_trigger = triggered and not notified_before
                if triggered:
                    currently_triggered += 1
                if is_new_trigger:
                    new_trigger_count += 1
                currency_data.append({
                    'cur_name': cur_name,
                    'rate': rate,
                    'rate_type': rate_type,
                    'condition': condition,
                    'price': price,
                    'triggered': triggered,
                    'is_new': is_new_trigger,
                })
            # 只在「至少一筆是首次達標」才推播
            if not uid or new_trigger_count == 0 or not currency_data:
                continue
            try:
                flex = build_currency_alert_flex(currency_data, new_trigger_count, currently_triggered)
                line_bot_api.push_message(uid, flex)
                notified += 1
            except Exception as e:
                print(f"[cron] Error pushing currency alert to {uid}: {e}")
        return f"OK, notified={notified}", 200
    except Exception as e:
        return f"Error: {e}", 500

def build_stock_alert_flex(stock_data, new_trigger_count, currently_triggered):
    """組裝股票通知 flex：列出所有關注股票，區分「剛達標」與「持續達標」"""
    rows = []
    for d in stock_data:
        if d['price_now'] is not None:
            rate_text = f"{d['price_now']:.2f}"
        else:
            rate_text = '無資料'
        condition = d['condition']
        target = d['target']
        if d.get('is_new'):
            status_text = f"🔔 剛達標！{'低於' if condition == '<' else '高於'} {target}"
            status_color = "#FF5252"
            status_weight = "bold"
        elif d['triggered']:
            status_text = f"✅ 持續{'低於' if condition == '<' else '高於'} {target}"
            status_color = "#1DB446"
            status_weight = "regular"
        elif target is None:
            status_text = "未設定條件"
            status_color = "#888888"
            status_weight = "regular"
        else:
            status_text = f"條件：{condition}{target}（未達）"
            status_color = "#FF9800"
            status_weight = "regular"
        rows.append({
            "type": "box", "layout": "horizontal", "margin": "lg",
            "contents": [
                {"type": "text", "text": f"{d['stock_name']} {d['stock_code']}", "size": "sm", "color": "#333333", "flex": 3},
                {"type": "text", "text": rate_text, "size": "sm", "weight": "bold", "align": "end", "flex": 2, "color": "#2196F3"},
            ]
        })
        rows.append({"type": "text", "text": status_text, "size": "xxs", "color": status_color, "weight": status_weight, "margin": "sm"})
    subtitle = f"剛有 {new_trigger_count} 檔達成條件"
    if currently_triggered > new_trigger_count:
        subtitle += f"（另有 {currently_triggered - new_trigger_count} 檔持續達標中）"
    return FlexSendMessage(
        alt_text=f"📢 股票通知（{new_trigger_count} 檔剛達標）",
        contents={
            "type": "bubble",
            "header": {
                "type": "box", "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "📢 股票通知", "weight": "bold", "size": "lg", "color": "#FF5252"},
                    {"type": "text", "text": subtitle, "size": "xs", "color": "#888888", "margin": "sm", "wrap": True}
                ], "paddingAll": "15px"
            },
            "body": {
                "type": "box", "layout": "vertical",
                "contents": rows,
                "paddingAll": "15px"
            },
            "footer": {
                "type": "box", "layout": "vertical",
                "contents": [
                    {"type": "button", "style": "primary", "color": "#2196F3", "height": "sm",
                     "action": {"type": "message", "label": "查看股票清單", "text": "股票清單"}}
                ], "paddingAll": "10px"
            }
        }
    )

@app.route('/cron/check_stock')
def cron_check_stock():
    """排程自動檢查股票條件並推播通知

    交叉觸發 + 一次性失效：只在「從未達 → 剛達標」當次推播。
    達標期間每天檢查但不重複推；條件鬆開（價格跨回）後 notified 重置，
    下次再達標時又會推一次。

    盤中時段才實際檢查，避免假日/盤後重複觸發或浪費 yfinance 配額。
    """
    if not is_trading_hours():
        return "OK, skipped (not trading hours)", 200
    try:
        db = mongodb.constructor_stock()
        nameList = db.list_collection_names()
        notified = 0
        for col_name in nameList:
            collect = db[col_name]
            entries = list(collect.find({"tag": "stock"}))
            stock_data = []
            new_trigger_count = 0
            currently_triggered = 0
            uid = None
            for entry in entries:
                if uid is None:
                    uid = entry.get('userID')
                stock_code = entry.get('favorite_stock')
                condition = entry.get('condition', '>')
                price_str = entry.get('price', '0')
                notified_before = bool(entry.get('notified', False))
                if not stock_code:
                    continue
                # 取得現價（自動 fallback 上櫃 .TWO）
                price_now = None
                try:
                    hist = get_stock_history(stock_code, "1d")
                    if hist is not None:
                        price_now = float(hist.iloc[-1]['Close'])
                except Exception as e:
                    print(f"[cron_stock] Error fetching {stock_code}: {e}")
                # 計算 target / triggered
                target = None
                triggered = False
                if price_str and price_str != '0':
                    try:
                        target = float(price_str)
                        if price_now is not None:
                            if condition == '<' and price_now < target:
                                triggered = True
                            elif condition == '>' and price_now > target:
                                triggered = True
                    except ValueError:
                        pass
                # 同步 notified 狀態
                if triggered != notified_before:
                    try:
                        mongodb.update_stock_notified(col_name, stock_code, triggered)
                    except Exception as e:
                        print(f"[cron_stock] Update notified failed {col_name}/{stock_code}: {e}")
                is_new_trigger = triggered and not notified_before
                if triggered:
                    currently_triggered += 1
                if is_new_trigger:
                    new_trigger_count += 1
                stock_data.append({
                    'stock_code': stock_code,
                    'stock_name': get_stock_name(stock_code),
                    'price_now': price_now,
                    'condition': condition,
                    'target': target,
                    'triggered': triggered,
                    'is_new': is_new_trigger,
                })
            if not uid or new_trigger_count == 0 or not stock_data:
                continue
            try:
                flex = build_stock_alert_flex(stock_data, new_trigger_count, currently_triggered)
                line_bot_api.push_message(uid, flex)
                notified += 1
            except Exception as e:
                print(f"[cron_stock] Error pushing alert to {uid}: {e}")
        return f"OK, notified={notified}", 200
    except Exception as e:
        return f"Error: {e}", 500

def build_my_stock_flex(uid, user_name, title=None, subtitle=None):
    """組裝「我的關注股票」flex，與 build_my_currency_flex 風格一致

    title/subtitle 可選，用於每日報告等場景客製標題。
    """
    db = mongodb.constructor_stock()
    collect = db[user_name]
    dataList = list(collect.find({"userID": uid}))
    if not dataList:
        return None
    rows = []
    for entry in dataList:
        code = entry['favorite_stock']
        condition = entry.get('condition', '>')
        price_str = entry.get('price', '0')
        try:
            hist = get_stock_history(code, "1d")
            price_now = float(hist.iloc[-1]['Close']) if hist is not None else None
        except:
            price_now = None
        stock_name = get_stock_name(code)
        target = None
        triggered = False
        if price_str and price_str != '0':
            try:
                target = float(price_str)
                if price_now is not None:
                    if condition == '<' and price_now < target:
                        triggered = True
                    elif condition == '>' and price_now > target:
                        triggered = True
            except ValueError:
                pass
        if triggered:
            status_text = f"✅ 已{'低於' if condition == '<' else '高於'} {target}"
            status_color = "#1DB446"
        elif target is None:
            status_text = "未設定條件"
            status_color = "#888888"
        else:
            status_text = f"條件：{condition}{target}（未達）"
            status_color = "#FF9800"
        price_text = f"{price_now:.2f}" if price_now is not None else "無資料"
        rows.append({
            "type": "box", "layout": "horizontal", "margin": "md",
            "contents": [
                {"type": "text", "text": f"{stock_name}({code})", "size": "sm", "color": "#333333", "flex": 3},
                {"type": "text", "text": price_text, "size": "sm", "weight": "bold", "align": "end", "flex": 2, "color": "#2196F3"},
                {"type": "box", "layout": "vertical", "flex": 0, "width": "50px", "height": "25px",
                 "contents": [{"type": "text", "text": "刪除", "size": "xs", "color": "#FFFFFF", "align": "center", "gravity": "center"}],
                 "backgroundColor": "#FF5252", "cornerRadius": "12px", "justifyContent": "center", "margin": "md",
                 "action": {"type": "message", "label": "刪除", "text": f"刪除{code}"}}
            ]
        })
        rows.append({"type": "text", "text": f"  {status_text}", "size": "xxs", "color": status_color, "margin": "sm"})
    return FlexSendMessage(
        alt_text="我的關注股票清單",
        contents={
            "type": "bubble",
            "header": {
                "type": "box", "layout": "vertical",
                "contents": [
                    {"type": "text", "text": title or "📈 我的關注股票", "weight": "bold", "size": "lg", "color": "#1DB446"},
                    {"type": "text", "text": subtitle or f"共 {len(dataList)} 檔（上限 {mongodb.MAX_STOCKS_PER_USER}）", "size": "xs", "color": "#888888", "margin": "sm", "wrap": True}
                ], "paddingAll": "15px"
            },
            "body": {
                "type": "box", "layout": "vertical",
                "contents": rows,
                "paddingAll": "15px"
            },
            "footer": {
                "type": "box", "layout": "vertical",
                "contents": [
                    {
                        "type": "box", "layout": "horizontal",
                        "contents": [
                            {"type": "button", "style": "secondary", "height": "sm",
                             "action": {"type": "message", "label": "檢查條件", "text": "股價提醒"}},
                            {"type": "button", "style": "secondary", "height": "sm", "color": "#FFCCCC",
                             "action": {"type": "message", "label": "清空全部", "text": "清空股票"}}
                        ], "spacing": "sm"
                    },
                    {"type": "button", "style": "link", "height": "sm",
                     "action": {"type": "message", "label": "↩ 返回股價查詢", "text": "股價查詢"}}
                ], "paddingAll": "10px", "spacing": "sm"
            }
        }
    )

@app.route('/cron/daily_stock_report')
def cron_daily_stock_report():
    """每個交易日早上推播一份關注股報告，列出所有關注的股票現況。
    無論是否達標都會推；冪等保護避免同日重複推。
    """
    now_tw = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    # 週末不推（沒新資料）
    if now_tw.weekday() >= 5:
        return "OK, skipped (weekend)", 200
    today_str = now_tw.strftime('%Y-%m-%d')
    if mongodb.get_cron_last_run('daily_stock_report') == today_str:
        return f"OK, already sent today ({today_str})", 200
    try:
        db = mongodb.constructor_stock()
        sent = 0
        subtitle = f"{now_tw.strftime('%m/%d')} 早安！您的關注股現況"
        for col_name in db.list_collection_names():
            collect = db[col_name]
            sample = collect.find_one({"tag": "stock"})
            if not sample:
                continue
            uid = sample.get('userID')
            if not uid:
                continue
            flex = build_my_stock_flex(uid, col_name, title="📈 早安股報告", subtitle=subtitle)
            if not flex:
                continue
            try:
                line_bot_api.push_message(uid, flex)
                sent += 1
            except Exception as e:
                print(f"[daily_stock_report] Push failed for {uid}: {e}")
        mongodb.set_cron_last_run('daily_stock_report', today_str)
        return f"OK, sent={sent}", 200
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/cron/oil_price')
def cron_oil_price():
    """排程推播下週油價預測給所有追蹤者；同一天重複觸發不會重複推播"""
    try:
        # 冪等保護：cron-job.org 若超時重試，會多次呼叫此 endpoint，
        # 用「今天是否已成功推播」擋掉重複，避免使用者收到多則一樣的通知。
        # 加 ?force=1 可跳過冪等，供資料源修正後手動重推
        # 加 ?test=1 只推給管理員白名單（不打擾其他人），且不寫入當日冪等
        force = request.args.get('force') == '1'
        test_mode = request.args.get('test') == '1'
        today_str = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        if not force and not test_mode and mongodb.get_cron_last_run('oil_price') == today_str:
            return f"OK, already sent today ({today_str})", 200
        data = oil_price(force=True)   # 每週排程重抓最新→順便刷新快取，之後使用者查詢直接吃快取
        # 若拿到 transmit 結構（含 cpc/fpc），用 flex；否則 fallback 純文字
        use_flex = bool(data.get('cpc'))
        if test_mode:
            followers = ['U60ff9aa248221639d7717bf54d1db609']
        else:
            followers = mongodb.get_all_followers()
        sent = 0
        if use_flex:
            oil_flex = build_oil_price_flex(data)
            for uid in followers:
                try:
                    line_bot_api.push_message(uid, oil_flex)
                    sent += 1
                except Exception as e:
                    print(f"[cron_oil] Failed to push to {uid}: {e}")
        else:
            prices = data.get('prices', {})
            forecast = data.get('forecast', {})
            label_map = {'92': '92無鉛', '95': '95無鉛', '98': '98無鉛', '柴油': '超級柴油', '今日中油油價': None}
            price_lines = ""
            for key, val in prices.items():
                label = label_map.get(key, key)
                if label is None:
                    continue
                price_lines += f"  {label}:${val}\n"
            forecast_lines = ""
            if forecast.get('日期'):
                forecast_lines += f"{forecast['日期']}\n"
            if forecast.get('汽油調整'):
                forecast_lines += f"  汽油:{forecast['汽油調整']}\n"
            if forecast.get('柴油預計調整'):
                forecast_lines += f"  柴油:{forecast['柴油預計調整']}\n"
            if forecast.get('變動幅度'):
                forecast_lines += f"  變動幅度:{forecast['變動幅度']}\n"
            msg = f"⛽ 油價週報\n\n本週油價:\n{price_lines}\n📊 下週預測:\n{forecast_lines}"
            for uid in followers:
                try:
                    line_bot_api.push_message(uid, TextSendMessage(text=msg.strip()))
                    sent += 1
                except Exception as e:
                    print(f"[cron_oil] Failed to push to {uid}: {e}")
        # 推播完成才標記「今日已執行」，避免推播失敗時被誤鎖
        # 測試模式不寫入，避免擋住當日正式推播
        if not test_mode:
            mongodb.set_cron_last_run('oil_price', today_str)
        tag = ' (test)' if test_mode else ''
        return f"OK, sent={sent}{tag}", 200
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/keep_alive')
def keep_alive():
    """保持服務清醒用，供 cron-job.org 等監控服務定期 ping"""
    return "alive", 200

@app.route('/cron/status')
def cron_status():
    """診斷端點：顯示伺服器時間、盤中判斷、各 cron 上次成功執行日"""
    now_tw = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    keys = ['oil_price', 'daily_stock_report']
    last_runs = {k: mongodb.get_cron_last_run(k) for k in keys}
    weekday_zh = ['一', '二', '三', '四', '五', '六', '日']
    info = {
        "現在時間 (台北)": now_tw.strftime('%Y-%m-%d %H:%M:%S') + f" 週{weekday_zh[now_tw.weekday()]}",
        "是否盤中時段": is_trading_hours(),
        "上次推播": last_runs,
    }
    lines = [f"{k}: {v}" for k, v in info.items()]
    return "\n".join(lines), 200, {"Content-Type": "text/plain; charset=utf-8"}

@app.route('/cron/bot_health')
def cron_bot_health():
    """診斷 bot 健康：LINE quota、followers 數、webhook token 有效性"""
    import json as _json
    out = {}
    headers = {'Authorization': f'Bearer {access_token}'}
    try:
        info_r = requests.get('https://api.line.me/v2/bot/info', headers=headers, timeout=8)
        out['bot_info_status'] = info_r.status_code
        out['bot_info'] = info_r.json() if info_r.status_code == 200 else info_r.text[:200]
    except Exception as e:
        out['bot_info_error'] = str(e)
    try:
        quota_r = requests.get('https://api.line.me/v2/bot/message/quota', headers=headers, timeout=8)
        usage_r = requests.get('https://api.line.me/v2/bot/message/quota/consumption', headers=headers, timeout=8)
        out['quota'] = quota_r.json()
        out['usage'] = usage_r.json()
    except Exception as e:
        out['quota_error'] = str(e)
    try:
        followers = mongodb.get_all_followers()
        out['followers_count'] = len(followers)
        out['followers_sample'] = followers[:3]
    except Exception as e:
        out['followers_error'] = str(e)
    return _json.dumps(out, ensure_ascii=False, indent=2), 200, {"Content-Type": "application/json; charset=utf-8"}

@app.route('/cron/oil_debug')
def cron_oil_debug():
    """診斷 oil_price 資料結構，看實際用了哪個來源，不推播"""
    import json as _json
    try:
        data = oil_price()
        has_cpc = bool(data.get('cpc'))
        has_fpc = bool(data.get('fpc'))
        summary = {
            'source': data.get('_source', 'unknown'),
            'has_cpc': has_cpc,
            'has_fpc': has_fpc,
            'effective_date': data.get('effective_date', ''),
            'cpc_next': data.get('cpc_next', {}),
            'fpc_next': data.get('fpc_next', {}),
            'deltas': data.get('deltas', {}),
            'prices': data.get('prices', {}),
            'forecast': data.get('forecast', {}),
            'will_use_flex': has_cpc,
        }
        # 也試單獨呼叫 transmit / MOEA 看誰壞了
        t_res = _fetch_transmit_oil()
        m_res = _fetch_moea_oil()
        summary['transmit_ok'] = bool(t_res and t_res.get('cpc'))
        summary['moea_ok'] = bool(m_res)
        return _json.dumps(summary, ensure_ascii=False, indent=2, default=str), 200, {"Content-Type": "application/json; charset=utf-8"}
    except Exception as e:
        import traceback
        return f"Error: {e}\n\n{traceback.format_exc()}", 500

@app.route('/register_me/<user_id>')
def register_me(user_id):
    """手動註冊現有用戶（用於已追蹤但未記錄的用戶）"""
    try:
        mongodb.save_follower(user_id)
        count = len(mongodb.get_all_followers())
        return f"OK, registered {user_id}, total followers={count}", 200
    except Exception as e:
        return f"Error: {e}", 500


#這段主要在畫k線圖
#pip3 install pyimgur
import yfinance as yf
import mplfinance as mpf
import pyimgur

def plot_stock_k_chart(IMGUR_CLIENT_ID, stock="0050", date_from='2020-01-01'):
    """
    進行個股k線繪製。優先嘗試 .TW（上市），失敗則 fallback .TWO（上櫃）。
    """
    df = None
    ticker_symbol = None
    for suffix in ('.TW', '.TWO'):
        try:
            candidate = str(stock) + suffix
            print(f"正在獲取股票數據: {candidate}")
            tmp = yf.download(candidate, start=date_from)
            if tmp is not None and not tmp.empty:
                df = tmp
                ticker_symbol = candidate
                break
        except Exception as e:
            print(f"K線下載失敗 {candidate}: {e}")
    if df is None or df.empty:
        print(f"未能獲取到股票數據（已試 .TW / .TWO）")
        return None
    try:
        # 新版 yfinance 回傳多層欄位，需要攤平
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 產生唯一檔名
        filename = f"kchart_{stock}_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(CHART_DIR, filename)

        print("繪製 K 線圖...")
        mpf.plot(df, type='candle', mav=(5, 20), volume=True,
                 ylabel=ticker_symbol.upper() + ' Price', savefig=filepath)

        # 優先使用本地路由（穩定）
        local_url = f"{RENDER_URL}/charts/{filename}"
        print(f"使用本地圖片: {local_url}")
        return local_url

    except Exception as e:
        print(f"K線圖錯誤: {e}")
        return None

#Line 回傳圖片函式
def reply_image(msg, rk, token):
    headers = {'Authorization':f'Bearer {token}','Content-Type':'application/json'}
    body = {
    'replyToken':rk,
    'messages':[{
          'type': 'image',
          'originalContentUrl': msg,
          'previewImageUrl': msg
        }]
    }
    req = requests.request('POST','https://api.line.me/v2/bot/message/reply',headers=headers,data=json.dumps(body).encode('utf-8'))
    print(req.text)

# 產生「我的外幣關注」Flex Message（共用）
def build_my_currency_flex(uid, user_name):
    db = mongodb.constructor_currency()
    collect = db[user_name]
    dataList = list(collect.find({"userID": uid}))
    if not dataList:
        return None
    rows = []
    for entry in dataList:
        cur = entry['favorite_currency']
        condition = entry.get('condition', '未設定')
        price = entry.get('price', '未設定')
        cur_name = mongodb.currency_list.get(cur, cur)
        try:
            rate_val, rate_type = get_sell_rate(cur)
            if rate_val is None:
                rate_text = '無資料'
            elif rate_type == '現金':
                rate_text = f"{float(rate_val)} (現金)"
            else:
                rate_text = str(float(rate_val))
        except:
            rate_text = '查詢失敗'
        cond_text = f" ({condition}{price})" if condition != '未設定' else ""
        rows.append({
            "type": "box", "layout": "horizontal", "margin": "md",
            "contents": [
                {"type": "text", "text": f"{cur_name}({cur})", "size": "sm", "color": "#333333", "flex": 3},
                {"type": "text", "text": rate_text, "size": "sm", "weight": "bold", "align": "end", "flex": 2, "color": "#2196F3"},
                {"type": "box", "layout": "vertical", "flex": 0, "width": "50px", "height": "25px",
                 "contents": [{"type": "text", "text": "刪除", "size": "xs", "color": "#FFFFFF", "align": "center", "gravity": "center"}],
                 "backgroundColor": "#FF5252", "cornerRadius": "12px", "justifyContent": "center",
                 "margin": "md",
                 "action": {"type": "message", "label": "刪除", "text": f"刪除外幣{cur}"}}
            ]
        })
        if cond_text:
            rows.append({"type": "text", "text": f"  通知條件：{condition}{price}", "size": "xxs", "color": "#888888", "margin": "sm"})
    return FlexSendMessage(
        alt_text="我的外幣關注清單",
        contents={
            "type": "bubble",
            "header": {
                "type": "box", "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "💱 我的外幣關注", "weight": "bold", "size": "lg", "color": "#2196F3"},
                    {"type": "text", "text": f"共 {len(dataList)} 個幣別", "size": "xs", "color": "#888888", "margin": "sm"}
                ], "paddingAll": "15px"
            },
            "body": {
                "type": "box", "layout": "vertical",
                "contents": rows,
                "paddingAll": "15px"
            },
            "footer": {
                "type": "box", "layout": "vertical",
                "contents": [
                    {
                        "type": "box", "layout": "horizontal",
                        "contents": [
                            {"type": "button", "style": "secondary", "height": "sm",
                             "action": {"type": "message", "label": "檢查條件", "text": "匯率推播"}},
                            {"type": "button", "style": "secondary", "height": "sm", "color": "#FFCCCC",
                             "action": {"type": "message", "label": "清空全部", "text": "清空外幣"}}
                        ], "spacing": "sm"
                    },
                    {"type": "button", "style": "link", "height": "sm",
                     "action": {"type": "message", "label": "↩ 返回匯率查詢", "text": "匯率查詢"}}
                ], "paddingAll": "10px", "spacing": "sm"
            }
        }
    )

# 抓使用者設定它關心的匯率
def cache_users_currency():
    db=mongodb.constructor_currency()
    nameList = db.list_collection_names()
    users = []
    for i in range(len(nameList)):
        collect = db[nameList[i]]
        cel = list(collect.find({"tag":'currency'}))
        users.append(cel)
    return users
def Usage(event):
    push_msg(event,"🌟🌟 使用說明 🌟🌟\n"
        "\n📈 股票功能\n"
        "  #2330 ➦ 查詢股價\n"
        "  股價查詢 ➦ 熱門股票選單\n"
        "  股票清單 ➦ 我的關注清單\n"
        "  股價提醒 ➦ 關注股票現價\n"
        "\n💱 匯率功能\n"
        "  外幣USD ➦ 查詢美元匯率\n"
        "  換匯USD/TWD ➦ 匯率換算\n"
        "  幣別種類 ➦ 所有幣別\n"
        "\n⛽ 其他功能\n"
        "  油價查詢 ➦ 最新油價\n"
        "  最新氣象 ➦ 天氣查詢\n"
        "  雷達回波 ➦ 雷達回波圖")
# 監聽所有來自 /callback 的 Post Request
def push_msg(event,msg):
    try:
        user_id = event.source.user_id
        line_bot_api.push_message(user_id,TextSendMessage(text=msg))
    except:
        room_id = event.source.room_id
        line_bot_api.push_message(room_id,TextSendMessage(text=msg))

# 抓使用者設定它關心的股票
def cache_users_stock():
    db=mongodb.constructor_stock()
    nameList = db.list_collection_names()
    users = []
    for i in range(len(nameList)):
        collect = db[nameList[i]]
        cel = list(collect.find({"tag":'stock'}))
        users.append(cel)
    return users

# 油價報你知
def _fetch_transmit_oil():
    """從 gasoline.transmit-info.com 抓中油+台塑對照油價（本週/下週 + 變動）
    回傳 dict：cpc/fpc 本週價、下週價、變動幅度、生效日期；抓不到回 None
    """
    try:
        r = requests.get('https://gasoline.transmit-info.com/',
                         headers={'User-Agent': 'Mozilla/5.0'}, timeout=7, verify=False)
        r.encoding = 'utf-8'
        html = r.text
    except Exception:
        return None
    row_re = re.compile(
        r'<td>\s*(中油|台塑)\s*(98|95|92|柴油)(?:無鉛)?\s*</td>\s*'
        r'<td>\s*([\d.]+)\s*</td>\s*'
        r'<td[^>]*>\s*([^<]*?)\s*</td>',   # 下週欄可能是「尚無數據」（週日中油未公布前）
        re.S,
    )
    rows = row_re.findall(html)
    if len(rows) < 8:
        return None
    data = {'cpc': {}, 'fpc': {}, 'cpc_next': {}, 'fpc_next': {}, 'deltas': {}}
    for company, fuel, cur, nxt_raw in rows[:8]:
        target = 'cpc' if company == '中油' else 'fpc'
        data[target][fuel] = float(cur)
        try:
            nxt = float(nxt_raw)
            data[f'{target}_next'][fuel] = nxt
            data['deltas'].setdefault(fuel, round(nxt - float(cur), 2))
        except (ValueError, TypeError):
            # 下週資料尚未公布（如週日早上），只保留本週價
            pass
    date_m = re.search(r'(\d{4}/\d{2}/\d{2})\s*~\s*(\d{4}/\d{2}/\d{2})', html)
    if date_m:
        try:
            from datetime import datetime as _dt, timedelta as _td
            end_of_this_week = _dt.strptime(date_m.group(2), '%Y/%m/%d')
            data['effective_date'] = (end_of_this_week + _td(days=1)).strftime('%Y/%m/%d')
        except Exception:
            data['effective_date'] = ''
    else:
        data['effective_date'] = ''
    data['_source'] = 'transmit'
    return data

def build_oil_price_flex(data):
    """組裝油價週報 flex：中油 vs 台塑對照 + 下週變動。
    data 需含 cpc/fpc/cpc_next/fpc_next/deltas/effective_date。
    若無 fpc（例如 fallback MOEA 只有中油）則只顯示中油。
    """
    cpc = data.get('cpc', {})
    fpc = data.get('fpc', {})
    cpc_next = data.get('cpc_next', {})
    fpc_next = data.get('fpc_next', {})
    deltas = data.get('deltas', {})
    eff = data.get('effective_date', '')
    has_fpc = bool(fpc)
    def _row_num(text, color="#333333", size="lg", weight="bold", align="end", flex=2):
        c = {"type": "text", "text": text, "size": size, "color": color, "align": align, "flex": flex}
        if weight:
            c["weight"] = weight
        return c
    def _delta_text(d):
        if d is None:
            return "—", "#888888"
        if abs(d) < 0.001:
            return "持平", "#888888"
        return (f"▼ {abs(d):.1f}", "#1DB446") if d < 0 else (f"▲ {abs(d):.1f}", "#FF3B30")
    # 表頭：欄位標籤放大到 md
    header_cols = [
        {"type": "text", "text": "油品", "size": "md", "color": "#888888", "weight": "bold", "flex": 3},
        {"type": "text", "text": "中油", "size": "md", "color": "#FF6600", "weight": "bold", "align": "end", "flex": 2},
    ]
    if has_fpc:
        header_cols.append({"type": "text", "text": "台塑", "size": "md", "color": "#2196F3", "weight": "bold", "align": "end", "flex": 2})
    header_cols.append({"type": "text", "text": "變動", "size": "md", "color": "#888888", "weight": "bold", "align": "end", "flex": 2})
    rows = [{"type": "box", "layout": "horizontal", "contents": header_cols, "margin": "sm"}]
    rows.append({"type": "separator", "margin": "md"})
    fuels = [('92', '92無鉛'), ('95', '95無鉛'), ('98', '98無鉛'), ('柴油', '柴油')]
    for key, label in fuels:
        d_txt, d_color = _delta_text(deltas.get(key))
        cpc_price = cpc_next.get(key) or cpc.get(key)
        cols = [
            {"type": "text", "text": label, "size": "lg", "color": "#333333", "weight": "bold", "flex": 3},
            _row_num(f"{cpc_price:.2f}" if cpc_price is not None else "—", color="#FF6600"),
        ]
        if has_fpc:
            fpc_price = fpc_next.get(key) or fpc.get(key)
            cols.append(_row_num(f"{fpc_price:.2f}" if fpc_price is not None else "—", color="#2196F3"))
        cols.append({"type": "text", "text": d_txt, "size": "lg", "color": d_color, "align": "end", "weight": "bold", "flex": 2})
        rows.append({"type": "box", "layout": "horizontal", "contents": cols, "margin": "lg"})
    subtitle = f"下週油價（{eff} 起）" if eff else "下週油價"
    return FlexSendMessage(
        alt_text=f"油價週報 - {eff}" if eff else "油價週報",
        contents={
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box", "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "⛽ 油價週報", "weight": "bold", "size": "xl", "color": "#FF6600"},
                    {"type": "text", "text": subtitle, "size": "md", "color": "#888888", "margin": "sm"}
                ],
                "paddingAll": "16px"
            },
            "body": {
                "type": "box", "layout": "vertical",
                "contents": rows,
                "paddingAll": "16px",
                "spacing": "sm"
            },
            "footer": {
                "type": "box", "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "資料來源：中油官方公告", "size": "xs", "color": "#aaaaaa", "align": "center"}
                ],
                "paddingAll": "10px"
            }
        }
    )

def _fetch_moea_oil():
    """從經濟部能源署抓中油官方公告的油價（含吸收補貼後的實際價格）。
    goodlife.tw 是「公式預估」不含中油自行吸收/貨物稅減徵，會與實際公告不符，
    因此優先用 MOEA 這個權威來源，goodlife.tw 只作 fallback。
    回傳 {'prices': {...}, 'forecast': {...}} 或 None（抓取失敗時）。
    """
    try:
        # MOEA 會擋預設的 python-requests UA，帶瀏覽器 UA 才會回完整頁面
        ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
        r = requests.get('https://www2.moeaea.gov.tw/oil111',
                         headers={'User-Agent': ua}, timeout=7, verify=False)
        r.encoding = 'utf-8'
        html = r.text
    except Exception:
        return None
    start = html.find('最新油品參考零售價格')
    if start < 0:
        return None
    section = html[start:start + 10000]
    group_re = re.compile(
        r'(92 無鉛汽油[\s\S]*?超級柴油[\s\S]*?)開始實施時間：自(\d{4}/\d{2}/\d{2})',
        re.S,
    )
    groups = group_re.findall(section)
    if not groups:
        return None
    item_re = re.compile(
        r'(92 無鉛汽油|95 無鉛汽油|98 無鉛汽油|超級柴油)\s*</div>\s*'
        r'<div class="col-5 text-center">\s*<strong>([\d.]+)</strong>[\s\S]*?'
        r'(south|north)[\s\S]{0,80}?([\d.]+)',
        re.S,
    )
    label_map = {'92 無鉛汽油': '92', '95 無鉛汽油': '95', '98 無鉛汽油': '98', '超級柴油': '柴油'}
    parsed = []
    for content, date_str in groups[:3]:
        items = item_re.findall(content)
        if len(items) < 4:
            continue
        prices = {}
        deltas = {}
        for name, price, direction, delta in items:
            k = label_map.get(name)
            if not k:
                continue
            prices[k] = float(price)
            sign = -1 if direction == 'south' else 1
            deltas[k] = sign * float(delta)
        parsed.append({'date': date_str, 'prices': prices, 'deltas': deltas})
    if not parsed:
        return None
    latest = parsed[0]
    prices_out = {
        '92': str(latest['prices'].get('92', '')),
        '95': str(latest['prices'].get('95', '')),
        '98': str(latest['prices'].get('98', '')),
        '柴油': str(latest['prices'].get('柴油', '')),
    }
    def fmt_delta(k):
        d = latest['deltas'].get(k)
        if d is None:
            return None
        if abs(d) < 0.001:
            return '不調整'
        return f"{'降' if d < 0 else '漲'} {abs(d):.1f} 元"
    forecast = {
        '日期': f"自 {latest['date']} 起",
        '汽油調整': fmt_delta('92') or '',
        '柴油預計調整': fmt_delta('柴油') or '',
        '變動幅度': '',
    }
    return {'prices': prices_out, 'forecast': forecast, '_source': 'moea'}

_OIL_CACHE = {"data": None, "ts": 0}


def oil_price(force=False):
    """回傳油價 dict（含快取）。油價一週才變一次，抓到就存起來，之後查詢直接回存檔→秒回、
    不必每次即時連那幾個從海外 Render 常常很慢的政府網站(避免拖太久→LINE reply token 過期→沒反應)。"""
    c = _OIL_CACHE
    if not force and c["data"] and (time.time() - c["ts"]) < 8 * 86400:
        return c["data"]
    data = _oil_price_fetch()
    if data and (data.get("prices") or data.get("cpc")):
        c["data"] = data
        c["ts"] = time.time()
    return data or c["data"]   # 這次抓失敗也回上次存檔(若有)，不讓使用者看到空的


def _oil_price_fetch():
    """實際抓取。優先序：transmit-info（中油+台塑對照）→ MOEA（僅中油）→ goodlife.tw（公式預估）"""
    data = _fetch_transmit_oil()
    if data:
        # 為了與舊 caller 相容，同時填入 prices/forecast 兩個舊 key
        cpc_next = data.get('cpc_next', {})
        deltas = data.get('deltas', {})
        data.setdefault('prices', {k: str(v) for k, v in cpc_next.items()})
        def _fmt_delta(k):
            d = deltas.get(k)
            if d is None:
                return ''
            if abs(d) < 0.001:
                return '不調整'
            return f"{'降' if d < 0 else '漲'} {abs(d):.1f} 元"
        data.setdefault('forecast', {
            '日期': f"自 {data.get('effective_date', '')} 起",
            '汽油調整': _fmt_delta('92'),
            '柴油預計調整': _fmt_delta('柴油'),
            '變動幅度': '',
        })
        return data
    data = _fetch_moea_oil()
    if data:
        return data
    target_url = 'https://gas.goodlife.tw/'
    rs = requests.session()
    res = rs.get(target_url, verify=False, timeout=7)   # 補上 timeout：原本無 timeout，前兩來源都失敗時這裡會無限等→LINE 完全沒反應
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')
    # 解析中油油價（key 和 value 在不同行）
    cpc_text = soup.select('#cpc')[0].text
    prices = {}
    lines = [l.strip() for l in cpc_text.split('\n') if l.strip()]
    pending_key = None
    for line in lines:
        if line.endswith(':'):
            pending_key = line[:-1].replace('油價', '').strip()
        elif pending_key:
            prices[pending_key] = line
            pending_key = None
    # 解析預計調整
    gas_lines = [l.strip() for l in soup.select('#gas-price')[0].text.split('\n') if l.strip()]
    forecast = {}
    for i, line in enumerate(gas_lines):
        if '柴油預計調整' in line and i + 1 < len(gas_lines):
            forecast['柴油預計調整'] = gas_lines[i + 1].replace(' ', '')
        if '下週' in line:
            forecast['日期'] = line
        if '不' in line and '調' in line and '整' in line:
            forecast['汽油調整'] = '不調整'
        elif '預計' not in line and ('元' in line or '+' in line or '-' in line) and '調整' not in line:
            forecast['汽油調整'] = line.replace(' ', '')
    # 解析變動幅度
    main_lines = [l.strip() for l in soup.select('#main')[0].text.split('\n') if l.strip()]
    for i, line in enumerate(main_lines):
        if '變動幅度' in line and i + 1 < len(main_lines):
            forecast['變動幅度'] = main_lines[i + 1]
    return {'prices': prices, 'forecast': forecast}

# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
# def callback():
#     # get X-Line-Signature header value
#     signature = request.headers['X-Line-Signature']

#     # get request body as text
#     body = request.get_data(as_text=True)
#     app.logger.info("Request body: " + body)

#     # handle webhook body
#     try:
#         handler.handle(body, signature)
#     except InvalidSignatureError:
#         abort(400)

#     return 'OK'

def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    #get request body as Text
    body = request.get_data(as_text=True)
    app.logger.info(f"Request body: body: {body}")

    # handle webhook body
    try:
        handler.handle(body, signature)
        # 轉換內容為json格式
        # json_data = json.loads(body)
        # # 取得回傳訊息的Token (reply mseeage 使用)
        # reply_token = json_data['events'][0]['replyToken']
        # # 取得使用者 ID (push message 使用)
        # user_id = json_data['events'][0]['source']['userId']
        # print(json_data)
        # if 'message' in json_data['events'][0]:
        #     if json_data['events'][0]['message']['type'] == 'text':
        #         # 取出文字
        #         text = json_data['events'][0]['message']['text']
        #         # 如果是雷達回波圖相關的文字
        #         if text == '雷達回波圖' or text == '雷達回波':
        #             #傳送雷達回波圖
        #             reply_image(f'https://cwbopendata.s3.ap-northeast-1.amazonaws.com/MSC/O-A0058-003.png?{time.time_ns()}',reply_token,access_token)
    except InvalidSignatureError:    
        abort(400)
        # print('error')
    return 'OK'



# 處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # message = TextSendMessage(text=event.message.text)
    # line_bot_api.reply_message(event.reply_token, message)
    msg = str(event.message.text).upper().strip() # 使用者輸入的內容
    original_msg = str(event.message.text).strip() # 保留原始大小寫
    profile = line_bot_api.get_profile(event.source.user_id)

    uid = profile.user_id #使用者ID
    user_name = profile.display_name #使用者名稱

    # 取得自己的 LINE userID（任何人可用，方便取得 ID 給管理員設定 ADMIN_UID）
    if original_msg in ('我的id', '我的ID', '我的Id'):
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"您的 LINE userID：\n{uid}\n\n（請完整複製，包含開頭的 U）")
        )
        return 0

    # 管理員查阿生地圖每日檢查報告（回覆訊息不計推播額度 → 想看就問，不必每天推給你）
    if original_msg in ('檢查', '每日檢查', '報告'):
        ADMIN_UIDS = ('U60ff9aa248221639d7717bf54d1db609',)
        if uid not in ADMIN_UIDS:
            return 0  # 非管理員：靜默不回（報告含監控地號，不可外洩，也不讓人知道有這功能）
        # 直接讀雲端推過來存在 MongoDB 的那份（不主動連雲端：機房 IP 會被 Cloudflare 擋）
        try:
            data_b64, _updated = mongodb.get_app_file('landmap_daily_report')   # ★回傳 tuple,不是 dict
            if not data_b64:
                body = '還沒有收到任何檢查報告（今晚 22:30 跑完後，雲端就會把報告送過來存著）。'
            else:
                d = json.loads(base64.b64decode(data_b64).decode('utf-8'))
                txt = (d.get('text') or '').strip() or '（報告是空的）'
                if len(txt) > 4800:
                    txt = txt[:4780] + '\n…（太長截斷）'
                body = f"{txt}\n\n—— 這是最近一次的檢查（{d.get('at', '')}）"
        except Exception as e:
            body = f"讀取失敗：{str(e)[:100]}"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=body))
        return 0

    # 管理員查推播用量
    if original_msg in ('用量', '額度', '配額'):
        # 管理員白名單；若想多加管理員直接附在 tuple 內即可
        ADMIN_UIDS = ('U60ff9aa248221639d7717bf54d1db609',)
        if uid not in ADMIN_UIDS:
            return 0  # 非管理員：靜默不回，避免洩漏 bot 額度資訊
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            quota = requests.get('https://api.line.me/v2/bot/message/quota', headers=headers, timeout=8).json()
            usage = requests.get('https://api.line.me/v2/bot/message/quota/consumption', headers=headers, timeout=8).json()
            total = int(quota.get('value', 0)) if quota.get('type') == 'limited' else 0
            used = int(usage.get('totalUsage', 0))
            remaining = total - used if total else None
            pct = (used / total * 100) if total else 0
            # 進度條 20 格
            filled = int(pct / 5)
            bar = '█' * filled + '░' * (20 - filled)
            now_tw = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
            # 預估月底用量（線性外推）
            day = now_tw.day
            from calendar import monthrange
            days_in_month = monthrange(now_tw.year, now_tw.month)[1]
            projected = int(used / day * days_in_month) if day else used
            color = "#1DB446" if pct < 70 else ("#FF9800" if pct < 90 else "#FF5252")
            flex = FlexSendMessage(
                alt_text=f"推播用量 {used}/{total}",
                contents={
                    "type": "bubble",
                    "header": {
                        "type": "box", "layout": "vertical",
                        "contents": [
                            {"type": "text", "text": "📊 LINE 推播用量", "weight": "bold", "size": "lg", "color": color},
                            {"type": "text", "text": now_tw.strftime('%Y-%m 第 %d 天'), "size": "xs", "color": "#888888", "margin": "sm"}
                        ], "paddingAll": "15px"
                    },
                    "body": {
                        "type": "box", "layout": "vertical", "spacing": "md",
                        "contents": [
                            {"type": "text", "text": f"{used} / {total if total else '∞'}", "weight": "bold", "size": "xxl", "align": "center", "color": color},
                            {"type": "text", "text": f"已用 {pct:.1f}%", "size": "sm", "align": "center", "color": "#888888"},
                            {"type": "text", "text": bar, "size": "xs", "align": "center", "color": color},
                            {"type": "separator", "margin": "md"},
                            {"type": "box", "layout": "horizontal", "contents": [
                                {"type": "text", "text": "剩餘額度", "size": "sm", "color": "#555555", "flex": 2},
                                {"type": "text", "text": f"{remaining}" if remaining is not None else "∞", "size": "sm", "weight": "bold", "align": "end", "flex": 2}
                            ]},
                            {"type": "box", "layout": "horizontal", "contents": [
                                {"type": "text", "text": "月底預估", "size": "sm", "color": "#555555", "flex": 2},
                                {"type": "text", "text": f"{projected}", "size": "sm", "weight": "bold", "align": "end", "flex": 2,
                                 "color": "#FF5252" if total and projected > total else "#333333"}
                            ]},
                            {"type": "box", "layout": "horizontal", "contents": [
                                {"type": "text", "text": "今日第幾天", "size": "sm", "color": "#555555", "flex": 2},
                                {"type": "text", "text": f"{day}/{days_in_month}", "size": "sm", "align": "end", "flex": 2}
                            ]},
                        ], "paddingAll": "15px"
                    }
                }
            )
            line_bot_api.reply_message(event.reply_token, flex)
        except Exception as e:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"查詢用量失敗：{e}"))
        return 0

    # 中文幣別名稱對照表
    currency_alias = {
        '美元': 'USD', '美金': 'USD', '日圓': 'JPY', '日幣': 'JPY', '日元': 'JPY',
        '港幣': 'HKD', '英鎊': 'GBP', '澳幣': 'AUD', '加幣': 'CAD', '加拿大幣': 'CAD',
        '瑞士法郎': 'CHF', '瑞郎': 'CHF', '新加坡幣': 'SGD', '星幣': 'SGD',
        '南非幣': 'ZAR', '瑞典幣': 'SEK', '紐元': 'NZD', '紐幣': 'NZD',
        '泰銖': 'THB', '泰幣': 'THB', '菲國比索': 'PHP', '菲律賓比索': 'PHP',
        '印尼幣': 'IDR', '韓元': 'KRW', '韓幣': 'KRW', '馬來幣': 'MYR',
        '越南盾': 'VND', '人民幣': 'CNY', '陸幣': 'CNY'
    }

    # 指令容錯：中文幣別 → 轉換為外幣查詢
    if original_msg in currency_alias:
        code = currency_alias[original_msg]
        content = EXRate.showCurrency(code)
        line_bot_api.reply_message(event.reply_token, [
            TextSendMessage(f'您要查詢的外幣是: {original_msg}'),
            TextSendMessage(content)
        ])
        return 0

    # 用戶輸入數字 → 接續自訂換匯/關注外幣/關注股票（優先於股票查詢）
    if uid in mat_d and re.match(r'^[\d,.]+$', msg):
        state = mat_d[uid]
        amount_str = msg.replace(',', '')
        try:
            float(amount_str)
            if state.startswith('換匯'):
                msg = f"{state}/{amount_str}".upper()
                del mat_d[uid]
            elif state.startswith('關注股'):
                # 例：state='關注股1784<' → msg='關注1784<31.5'
                msg = f"關注{state[3:]}{amount_str}"
                del mat_d[uid]
            elif state.startswith('關注'):
                # 例：state='關注USD<' → msg='新增外幣USD<31.5'
                msg = f"新增外幣{state[2:]}{amount_str}"
                del mat_d[uid]
        except ValueError:
            del mat_d[uid]

    # 指令容錯：純4位數字 → 當作股票查詢
    if re.match('^[0-9]{4,6}$', msg):
        msg = '#' + msg

    ######################## 匯率區 ##############################################
    if re.match("匯率大小事|匯率查詢", msg):
        btn_msg = Msg_Template.stock_reply_rate()
        line_bot_api.reply_message(event.reply_token, btn_msg)
        return 0
    if re.match(r"自訂換匯[A-Z]{3}/[A-Z]{3}", msg):
        parts = msg[4:].split("/")
        mat_d[uid] = f"換匯{parts[0]}/{parts[1]}"
        hint_buttons = [
            QuickReplyButton(action=MessageAction(label="100", text="100")),
            QuickReplyButton(action=MessageAction(label="1000", text="1000")),
            QuickReplyButton(action=MessageAction(label="10000", text="10000")),
            QuickReplyButton(action=MessageAction(label="↩ 返回匯率兌換", text="匯率兌換")),
        ]
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=f"請輸入要兌換的 {parts[0]} 金額（數字），例如：1000",
                quick_reply=QuickReply(items=hint_buttons)
            )
        )
        return 0
    if re.match("匯率兌換$", msg):
        pairs = [
            ("美元→台幣", "換匯USD/TWD"), ("日圓→台幣", "換匯JPY/TWD"),
            ("港幣→台幣", "換匯HKD/TWD"), ("英鎊→台幣", "換匯GBP/TWD"),
            ("澳幣→台幣", "換匯AUD/TWD"), ("人民幣→台幣", "換匯CNY/TWD"),
            ("加幣→台幣", "換匯CAD/TWD"), ("新加坡幣→台幣", "換匯SGD/TWD"),
            ("韓元→台幣", "換匯KRW/TWD"), ("泰銖→台幣", "換匯THB/TWD"),
            ("瑞士法郎→台幣", "換匯CHF/TWD"), ("瑞典幣→台幣", "換匯SEK/TWD"),
        ]
        buttons = [QuickReplyButton(action=MessageAction(label=label, text=cmd)) for label, cmd in pairs]
        buttons.append(QuickReplyButton(action=MessageAction(label="更多幣別▸", text="匯率兌換更多")))
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請選擇要兌換的幣別：", quick_reply=QuickReply(items=buttons))
        )
        return 0
    if re.match("匯率兌換更多", msg):
        pairs = [
            ("紐元→台幣", "換匯NZD/TWD"), ("菲國比索→台幣", "換匯PHP/TWD"),
            ("印尼幣→台幣", "換匯IDR/TWD"), ("馬來幣→台幣", "換匯MYR/TWD"),
            ("越南盾→台幣", "換匯VND/TWD"), ("南非幣→台幣", "換匯ZAR/TWD"),
        ]
        buttons = [QuickReplyButton(action=MessageAction(label=label, text=cmd)) for label, cmd in pairs]
        buttons.append(QuickReplyButton(action=MessageAction(label="◂常用幣別", text="匯率兌換")))
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="更多幣別：", quick_reply=QuickReply(items=buttons))
        )
        return 0
    if re.match("換匯[A-Z]{3}/[A-Z]{3}", msg):
        try:
            parts = msg[2:].split("/")
            from_cur = parts[0]
            to_cur = parts[1]
            amount = float(parts[2]) if len(parts) > 2 else 1
            from_name = EXRate.getCurrencyName(from_cur)
            if from_name == "無可支援的外幣":
                from_name = from_cur
            # 取得匯率
            url_coinbase = f'https://api.coinbase.com/v2/exchange-rates?currency={from_cur}'
            res_api = requests.get(url_coinbase)
            rate_data = res_api.json()
            rate = float(rate_data['data']['rates'][to_cur])
            result = rate * amount
            # 常用金額按鈕
            amounts = [1, 100, 1000, 10000]
            amount_btns = [
                QuickReplyButton(action=MessageAction(
                    label=f"{a:,} {from_cur}", text=f"換匯{from_cur}/{to_cur}/{a}"
                )) for a in amounts if a != amount
            ]
            amount_btns.append(QuickReplyButton(action=MessageAction(
                label="✏️ 自訂金額", text=f"自訂換匯{from_cur}/{to_cur}"
            )))
            amount_btns.append(QuickReplyButton(action=MessageAction(
                label="↩ 匯率查詢", text="匯率查詢"
            )))
            amount_btns.append(QuickReplyButton(action=MessageAction(
                label="🏠 主選單", text="開始玩"
            )))
            flex = FlexSendMessage(
                alt_text=f"匯率兌換 {from_cur}→{to_cur}",
                contents={
                    "type": "bubble",
                    "header": {
                        "type": "box", "layout": "vertical",
                        "contents": [
                            {"type": "text", "text": f"💱 {from_name} → {to_cur}", "weight": "bold", "size": "lg", "color": "#2196F3"},
                            {"type": "text", "text": f"匯率：1 {from_cur} = {rate:.4f} {to_cur}", "size": "xs", "color": "#888888", "margin": "sm"}
                        ], "paddingAll": "15px"
                    },
                    "body": {
                        "type": "box", "layout": "vertical",
                        "contents": [
                            {"type": "box", "layout": "horizontal", "contents": [
                                {"type": "text", "text": "兌換金額", "size": "sm", "color": "#555555", "flex": 2},
                                {"type": "text", "text": f"{amount:,.2f} {from_cur}", "size": "sm", "weight": "bold", "align": "end", "flex": 3}
                            ]},
                            {"type": "box", "layout": "horizontal", "margin": "md", "contents": [
                                {"type": "text", "text": "兌換結果", "size": "sm", "color": "#555555", "flex": 2},
                                {"type": "text", "text": f"{result:,.2f} {to_cur}", "size": "lg", "weight": "bold", "align": "end", "flex": 3, "color": "#FF6600"}
                            ]}
                        ], "paddingAll": "15px"
                    }
                }
            )
            if amount_btns:
                # 設定換匯狀態，讓使用者直接輸入數字就能換匯（不用先按「自訂金額」）
                mat_d[uid] = f"換匯{from_cur}/{to_cur}"
                reply_msg = TextSendMessage(
                    text="換其他金額：",
                    quick_reply=QuickReply(items=amount_btns)
                )
                line_bot_api.reply_message(event.reply_token, [flex, reply_msg])
            else:
                line_bot_api.reply_message(event.reply_token, flex)
        except Exception as e:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"匯率兌換失敗: {str(e)}"))
        return 0
    if re.match(r'關注外幣[A-Z]{3}$', msg):
        currency = msg[4:7]
        currency_name = EXRate.getCurrencyName(currency)
        if currency_name == "無可支援的外幣":
            line_bot_api.reply_message(event.reply_token, TextSendMessage("無可支援的外幣"))
            return 0
        rate_val, rate_type = get_sell_rate(currency)
        current = float(rate_val) if rate_val is not None else 0
        rate_label = f"{rate_type}賣出" if rate_type else "即期賣出"
        buttons = [
            QuickReplyButton(action=MessageAction(label="不設條件，直接關注", text=f"新增外幣{currency}")),
        ]
        if current > 0:
            buttons += [
                QuickReplyButton(action=MessageAction(label=f"低於 {current:.2f} 通知", text=f"新增外幣{currency}<{current:.2f}")),
                QuickReplyButton(action=MessageAction(label=f"高於 {current:.2f} 通知", text=f"新增外幣{currency}>{current:.2f}")),
            ]
        buttons += [
            QuickReplyButton(action=MessageAction(label="✏️ 自訂 低於", text=f"自訂關注{currency}<")),
            QuickReplyButton(action=MessageAction(label="✏️ 自訂 高於", text=f"自訂關注{currency}>")),
        ]
        current_text = f"{current:.4f}" if rate_type == '現金' and current < 1 else f"{current:.2f}"
        info_line = f"目前{rate_label}：{current_text}" if current > 0 else "目前無即期/現金報價"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=f"要關注 {currency_name}({currency})\n{info_line}\n請選擇通知條件：",
                quick_reply=QuickReply(items=buttons)
            )
        )
        return 0
    if re.match(r'自訂關注[A-Z]{3}[<>]', msg):
        currency = msg[4:7]
        op = msg[7]
        currency_name = EXRate.getCurrencyName(currency)
        if currency_name == "無可支援的外幣":
            currency_name = currency
        mat_d[uid] = f"關注{currency}{op}"
        cond_word = "低於" if op == "<" else "高於"
        hint_buttons = [
            QuickReplyButton(action=MessageAction(label="↩ 返回選擇條件", text=f"關注外幣{currency}")),
        ]
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=f"請輸入 {currency_name}({currency}) 要{cond_word}多少時通知（數字），例如 31.50",
                quick_reply=QuickReply(items=hint_buttons)
            )
        )
        return 0
    if re.match('幣別種類',msg):
        message = Msg_Template.show_Button()
        line_bot_api.reply_message(event.reply_token,message)
        return 0
    if re.match('新增外幣[A-Z]{3}', msg):
        currency = msg[4:7]
        currency_name = EXRate.getCurrencyName(currency)
        if currency_name == "無可支援的外幣":
            line_bot_api.reply_message(event.reply_token, TextSendMessage("無可支援的外幣"))
        else:
            if re.match('新增外幣[A-Z]{3}[<>][0-9]', msg):
                result = mongodb.write_my_currency(uid, user_name, currency, msg[7:8], msg[8:])
            else:
                result = mongodb.write_my_currency(uid, user_name, currency, "未設定", "未設定")
            # 上限訊息以 ❌ 開頭，直接回給使用者
            if isinstance(result, str) and result.startswith('❌'):
                line_bot_api.reply_message(event.reply_token, TextSendMessage(result))
                return 0
            reply_msgs = [TextSendMessage(f"✓ 已關注 {currency_name}({currency})")]
            my_flex = build_my_currency_flex(uid, user_name)
            if my_flex:
                reply_msgs.append(my_flex)
            line_bot_api.reply_message(event.reply_token, reply_msgs)
        return 0
    if re.match('我的外幣', msg):
        my_flex = build_my_currency_flex(uid, user_name)
        if my_flex:
            line_bot_api.reply_message(event.reply_token, [
                TextSendMessage('稍等一下, 匯率查詢中...'),
                my_flex
            ])
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("您的外幣清單為空，請先透過外幣查詢頁面加入關注"))
        return 0
    if re.match('刪除外幣[A-Z]{3}', msg):
        cur_code = msg[4:7]
        mongodb.delete_my_currency(user_name, cur_code)
        cur_name = mongodb.currency_list.get(cur_code, cur_code)
        my_flex = build_my_currency_flex(uid, user_name)
        if my_flex:
            line_bot_api.reply_message(event.reply_token, [
                TextSendMessage(f"✓ 已刪除 {cur_name}"),
                my_flex
            ])
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("外幣清單已清空"))
        return 0
    if re.match('清空外幣', msg):
        mongodb.delete_my_allcurrency(user_name, uid)
        line_bot_api.reply_message(event.reply_token, TextSendMessage("✓ 外幣清單已全部清空"))
        return 0
    if re.match("匯率走勢|走勢圖", msg):
        pairs = [
            ("美元", "CTUSD"), ("日圓", "CTJPY"), ("港幣", "CTHKD"),
            ("英鎊", "CTGBP"), ("澳幣", "CTAUD"), ("人民幣", "CTCNY"),
            ("加幣", "CTCAD"), ("新加坡幣", "CTSGD"), ("韓元", "CTKRW"),
            ("泰銖", "CTTHB"), ("瑞士法郎", "CTCHF"), ("瑞典幣", "CTSEK"),
        ]
        buttons = [QuickReplyButton(action=MessageAction(label=label, text=cmd)) for label, cmd in pairs]
        buttons.append(QuickReplyButton(action=MessageAction(label="更多幣別▸", text="匯率走勢更多")))
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請選擇要查看走勢的幣別：", quick_reply=QuickReply(items=buttons))
        )
        return 0
    if re.match("匯率走勢更多", msg):
        pairs = [
            ("紐元", "CTNZD"), ("菲國比索", "CTPHP"), ("印尼幣", "CTIDR"),
            ("馬來幣", "CTMYR"), ("越南盾", "CTVND"), ("南非幣", "CTZAR"),
        ]
        buttons = [QuickReplyButton(action=MessageAction(label=label, text=cmd)) for label, cmd in pairs]
        buttons.append(QuickReplyButton(action=MessageAction(label="◂常用幣別", text="匯率走勢")))
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="更多幣別：", quick_reply=QuickReply(items=buttons))
        )
        return 0
    if re.match("CT[A-Z]{3}", msg):
        currency = msg[2:5] # 外幣代號
        if EXRate.getCurrencyName(currency) == "無可支援的外幣":
            line_bot_api.reply_message(event.reply_token, TextSendMessage('無可支援的外幣'))
            return 0
        currency_name = EXRate.getCurrencyName(currency)
        reply_msgs = []
        cash_imgurl = EXRate.cash_exrate_sixMonth(currency)
        if cash_imgurl == "現金匯率無資料可分析":
            reply_msgs.append(TextSendMessage('現金匯率無資料可分析'))
        else:
            reply_msgs.append(TextSendMessage(f'📊 {currency_name} 現金匯率走勢（近6個月）'))
            reply_msgs.append(ImageSendMessage(original_content_url=cash_imgurl, preview_image_url=cash_imgurl))

        spot_imgurl = EXRate.spot_exrate_sixMonth(currency)
        if spot_imgurl == "即期匯率無資料可分析":
            reply_msgs.append(TextSendMessage('即期匯率無資料可分析'))
        else:
            reply_msgs.append(TextSendMessage(f'📊 {currency_name} 即期匯率走勢（近6個月）'))
            reply_msgs.append(ImageSendMessage(original_content_url=spot_imgurl, preview_image_url=spot_imgurl))
        btn_msg = Msg_Template.realtime_currency_other(currency)
        reply_msgs.append(btn_msg)
        line_bot_api.reply_message(event.reply_token, reply_msgs[:5])
        return 0
    if re.match('外幣[A-Z]{3}',msg):
        currency = msg[2:5]
        currency_name = EXRate.getCurrencyName(currency)
        if currency_name == "無可支援的外幣":
            line_bot_api.reply_message(event.reply_token, TextSendMessage("無可支援的外幣"))
        else:
            try:
                rate, upd = EXRate.now_rate(currency)   # 臺銀反爬蟲擋 twder→改用 open.er-api.com 中價
                if not rate:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"{currency_name}（{currency}）匯率暫時查不到，請稍後再試 🙏"))
                    return 0
                inv = (1.0 / rate) if rate else 0
                rows = [
                    {"type": "box", "layout": "horizontal", "margin": "md", "contents": [
                        {"type": "text", "text": f"1 {currency}", "size": "sm", "color": "#555555", "flex": 3},
                        {"type": "text", "text": f"{rate:.4g} 台幣", "size": "md", "weight": "bold", "align": "end", "flex": 4, "color": "#2196F3"}]},
                    {"type": "box", "layout": "horizontal", "margin": "md", "contents": [
                        {"type": "text", "text": "1 台幣", "size": "sm", "color": "#555555", "flex": 3},
                        {"type": "text", "text": f"{inv:.4g} {currency}", "size": "md", "weight": "bold", "align": "end", "flex": 4, "color": "#2196F3"}]},
                    {"type": "text", "text": "中價參考，實際買賣以各銀行牌告為準", "size": "xs", "color": "#aaaaaa", "margin": "md", "wrap": True},
                ]
                currency_flex = FlexSendMessage(
                    alt_text=f"{currency_name}匯率查詢",
                    contents={
                        "type": "bubble",
                        "header": {
                            "type": "box", "layout": "vertical",
                            "contents": [
                                {"type": "text", "text": f"💱 {currency_name} ({currency})", "weight": "bold", "size": "lg", "color": "#2196F3"},
                                {"type": "text", "text": f"更新：{upd}", "size": "xs", "color": "#888888", "margin": "sm"}
                            ], "paddingAll": "15px"
                        },
                        "body": {"type": "box", "layout": "vertical", "contents": rows, "paddingAll": "15px"},
                        "footer": {
                            "type": "box", "layout": "vertical",
                            "contents": [
                                {"type": "box", "layout": "horizontal", "contents": [
                                    {"type": "button", "style": "primary", "color": "#FF9800", "height": "sm", "flex": 1,
                                     "action": {"type": "message", "label": "兌換台幣", "text": f"換匯{currency}/TWD"}},
                                    {"type": "button", "style": "primary", "color": "#FF5252", "height": "sm", "flex": 1,
                                     "action": {"type": "message", "label": "加入關注", "text": f"關注外幣{currency}"}}
                                ], "spacing": "sm"},
                                {"type": "button", "style": "link", "height": "sm",
                                 "action": {"type": "message", "label": "↩ 返回匯率查詢", "text": "匯率查詢"}}
                            ], "paddingAll": "10px", "spacing": "sm"
                        }
                    }
                )
                line_bot_api.reply_message(event.reply_token, currency_flex)
            except Exception as e:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"匯率查詢失敗: {str(e)}"))
        return 0
    ######################## 使用說明 選單 油價報你知################################
    if event.message.text in ("加油折扣", "加油站折扣", "折扣速覽"):
        try:
            data = oil_price()
            cpc = data.get('cpc') or {}
            # fallback：若 transmit/moea 失敗，goodlife 只給 prices dict（也是中油牌價）
            if not cpc:
                for k, v in (data.get('prices') or {}).items():
                    try:
                        cpc[k] = float(str(v).strip())
                    except (ValueError, TypeError):
                        pass
            cpc92 = cpc.get('92')
            cpcD = cpc.get('柴油')
            gd_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gas_discount.json')
            with open(gd_path, 'r', encoding='utf-8') as f:
                gd = json.load(f)

            def _price(base, off):
                if base is None:
                    return "—"
                return f"{base - off:.2f}" + (f" (-{off})" if off > 0 else "")

            def _section(title, base, off_key):
                rows = [{"type": "text", "text": title, "size": "sm", "color": "#333333", "weight": "bold", "margin": "md"}]
                for st in gd['stations']:
                    off = st.get(off_key, 0)
                    rows.append({
                        "type": "box", "layout": "horizontal", "margin": "sm",
                        "contents": [
                            {"type": "text", "text": st['name'], "size": "sm", "color": "#555555", "flex": 5},
                            {"type": "text", "text": _price(base, off), "size": "sm", "weight": "bold", "align": "end", "flex": 4,
                             "color": "#1DB446" if off > 0 else "#333333"},
                        ]
                    })
                return rows

            body = []
            base_line = f"以中油 92={cpc92:.2f}／柴油={cpcD:.2f} 換算" if cpc92 and cpcD else "無法取得中油牌價做基準"
            body.append({"type": "text", "text": base_line, "size": "xs", "color": "#888888", "margin": "sm"})
            body.extend(_section("💧 自助 92 無鉛", cpc92, 'self_gas_off'))
            body.extend(_section("💧 自助 超級柴油", cpcD, 'self_diesel_off'))
            body.append({"type": "separator", "margin": "lg"})
            body.extend(_section("🧑 人工 92 無鉛", cpc92, 'manual_gas_off'))
            body.extend(_section("🧑 人工 超級柴油", cpcD, 'manual_diesel_off'))
            body.append({"type": "separator", "margin": "lg"})
            body.append({"type": "text", "text": "💡 額外優惠", "size": "sm", "color": "#333333", "weight": "bold", "margin": "md"})
            for line in gd.get('extras', []):
                body.append({"type": "text", "text": f"· {line}", "size": "xs", "color": "#555555", "wrap": True, "margin": "sm"})
            body.append({"type": "separator", "margin": "lg"})
            body.append({"type": "text", "text": f"⚠️ 折扣為 {gd['updated']} 整理，實際以各站現場為準",
                         "size": "xs", "color": "#FF9800", "wrap": True, "margin": "md"})

            discount_flex = FlexSendMessage(
                alt_text="加油站折扣速覽",
                contents={
                    "type": "bubble", "size": "mega",
                    "header": {
                        "type": "box", "layout": "vertical",
                        "contents": [
                            {"type": "text", "text": "🎫 加油站折扣速覽", "weight": "bold", "size": "xl", "color": "#FF6600"},
                            {"type": "text", "text": "各家自助/人工預估價", "size": "sm", "color": "#888888", "margin": "sm"}
                        ], "paddingAll": "16px"
                    },
                    "body": {
                        "type": "box", "layout": "vertical",
                        "contents": body,
                        "paddingAll": "16px"
                    }
                }
            )
            line_bot_api.reply_message(event.reply_token, discount_flex)
        except Exception as e:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"加油折扣查詢失敗: {e}"))
        return 0
    if event.message.text == "油價查詢":
        try:
            data = oil_price()
            cpc = data.get('cpc') or {}
            # fallback：若 transmit/moea 都失敗，goodlife 的 prices dict 也是中油牌價
            if not cpc:
                for k, v in (data.get('prices') or {}).items():
                    try:
                        cpc[k] = float(str(v).strip())
                    except (ValueError, TypeError):
                        pass
            fpc = data.get('fpc') or {}
            cpc_next = data.get('cpc_next') or {}
            fpc_next = data.get('fpc_next') or {}
            deltas = data.get('deltas') or {}
            eff_date = data.get('effective_date') or ''
            has_fpc = bool(fpc)
            has_change = any(abs(d) > 0.001 for d in deltas.values())

            def _delta_text(d):
                if d is None:
                    return "—", "#888888"
                if abs(d) < 0.001:
                    return "持平", "#888888"
                return (f"▼ {abs(d):.1f}", "#1DB446") if d < 0 else (f"▲ {abs(d):.1f}", "#FF3B30")

            # 表頭
            header_cols = [
                {"type": "text", "text": "油品", "size": "md", "color": "#888888", "weight": "bold", "flex": 3},
                {"type": "text", "text": "中油", "size": "md", "color": "#FF6600", "weight": "bold", "align": "end", "flex": 2},
            ]
            if has_fpc:
                header_cols.append({"type": "text", "text": "台塑", "size": "md", "color": "#2196F3", "weight": "bold", "align": "end", "flex": 2})
            if has_change:
                header_cols.append({"type": "text", "text": "下週", "size": "md", "color": "#888888", "weight": "bold", "align": "end", "flex": 2})
            rows = [{"type": "box", "layout": "horizontal", "contents": header_cols, "margin": "sm"}]
            rows.append({"type": "separator", "margin": "md"})

            fuels = [('92', '92無鉛'), ('95', '95無鉛'), ('98', '98無鉛'), ('柴油', '柴油')]
            for key, label in fuels:
                cpc_price = cpc.get(key)
                fpc_price = fpc.get(key) if has_fpc else None
                d = deltas.get(key)
                cols = [
                    {"type": "text", "text": label, "size": "lg", "color": "#333333", "weight": "bold", "flex": 3},
                    {"type": "text", "text": f"{cpc_price:.2f}" if cpc_price is not None else "—",
                     "size": "lg", "color": "#FF6600", "align": "end", "weight": "bold", "flex": 2},
                ]
                if has_fpc:
                    cols.append({"type": "text", "text": f"{fpc_price:.2f}" if fpc_price is not None else "—",
                                 "size": "lg", "color": "#2196F3", "align": "end", "weight": "bold", "flex": 2})
                if has_change:
                    txt, color = _delta_text(d)
                    cols.append({"type": "text", "text": txt, "size": "lg", "color": color, "align": "end", "weight": "bold", "flex": 2})
                rows.append({"type": "box", "layout": "horizontal", "contents": cols, "margin": "lg"})

            # 下週生效日期提示（有變動才顯示）
            if has_change and eff_date:
                rows.append({"type": "separator", "margin": "md"})
                rows.append({"type": "text", "text": f"📅 下週 {eff_date} 起生效", "size": "sm", "color": "#888888", "align": "center", "margin": "md"})
            elif eff_date:
                rows.append({"type": "separator", "margin": "md"})
                rows.append({"type": "text", "text": f"下週 {eff_date} 起 不調整", "size": "sm", "color": "#1DB446", "align": "center", "margin": "md", "weight": "bold"})

            subtitle = "本週生效｜元/公升"
            oil_flex = FlexSendMessage(
                alt_text="油價查詢",
                contents={
                    "type": "bubble",
                    "size": "mega",
                    "header": {
                        "type": "box", "layout": "vertical",
                        "contents": [
                            {"type": "text", "text": "⛽ 加油站現價比較", "weight": "bold", "size": "xl", "color": "#FF6600"},
                            {"type": "text", "text": subtitle, "size": "md", "color": "#888888", "margin": "sm"}
                        ],
                        "paddingAll": "16px"
                    },
                    "body": {
                        "type": "box", "layout": "vertical",
                        "contents": rows,
                        "paddingAll": "16px",
                        "spacing": "sm"
                    },
                    "footer": {
                        "type": "box", "layout": "vertical", "spacing": "sm",
                        "contents": [
                            {"type": "button", "style": "primary", "color": "#FF9800", "height": "sm",
                             "action": {"type": "message", "label": "🎫 看其他加油站折扣", "text": "加油折扣"}},
                            {"type": "text", "text": "資料來源：中油官方公告", "size": "xs", "color": "#aaaaaa", "align": "center"}
                        ],
                        "paddingAll": "10px"
                    }
                }
            )
            line_bot_api.reply_message(event.reply_token, oil_flex)
        except Exception as e:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"油價查詢失敗: {str(e)}"))
        return 0
    if event.message.text == "使用說明":
        def make_desc(text):
            return {"type": "text", "text": text, "size": "sm", "color": "#555555", "wrap": True, "margin": "sm"}
        def make_subtitle(text):
            return {"type": "text", "text": text, "weight": "bold", "size": "sm", "color": "#333333", "margin": "lg"}
        def make_bubble(title, color, rows):
            return {
                "type": "bubble", "size": "mega",
                "header": {"type": "box", "layout": "vertical", "contents": [
                    {"type": "text", "text": title, "weight": "bold", "size": "lg", "color": color, "align": "center"}
                ], "paddingAll": "15px"},
                "body": {"type": "box", "layout": "vertical", "contents": rows, "paddingAll": "15px", "spacing": "sm"}
            }
        stock_bubble = make_bubble("📈 股票功能", "#1DB446", [
            make_subtitle("查詢股價"),
            make_desc("在主選單點「股價查詢」，會顯示 12 檔熱門股票讓你直接點選。也可以在輸入框打股票代號（如 2330）或公司名稱（如 台積電），系統會自動搜尋。"),
            make_desc("查詢結果會顯示即時股價、漲跌幅、開盤、最高、最低、成交量，以及近一週的收盤價走勢。"),
            {"type": "separator", "margin": "lg"},
            make_subtitle("K線圖"),
            make_desc("股價查詢結果的卡片底部有四個按鈕：3個月、半年、1年、2年，點擊後會繪製該期間的 K 線圖（含 5日線、20日線與成交量）。"),
            {"type": "separator", "margin": "lg"},
            make_subtitle("關注股票與自動通知"),
            make_desc("查詢股價時，卡片右上角有「☆關注」按鈕，點擊即可關注該股票。關注後可設定條件（如高於或低於某個價格）。"),
            make_desc("輸入「股票清單」可查看所有已關注的股票。輸入「股價提醒」可手動檢查是否達標。"),
            make_desc("系統會在每個交易日下午 1:35（收盤後）自動檢查，符合條件時主動推播通知給你。"),
        ])
        currency_bubble = make_bubble("💱 匯率功能", "#2196F3", [
            make_subtitle("查詢匯率"),
            make_desc("在主選單點「匯率查詢」，會顯示功能選單。也可以直接輸入幣別名稱（如美元、日圓）或輸入「外幣USD」來查詢。"),
            make_desc("查詢結果會顯示台灣銀行的現金買入/賣出、即期買入/賣出匯率，卡片底部有「走勢圖」、「兌換台幣」、「加入關注」三個快捷按鈕。"),
            make_desc("點「幣別種類」可以看到全部 18 種支援的外幣按鈕選單。"),
            {"type": "separator", "margin": "lg"},
            make_subtitle("匯率兌換"),
            make_desc("在匯率查詢選單中選「匯率兌換」，選擇想兌換的幣別後，會顯示兌換結果。底部有常用金額按鈕（100、1000、10000），也可以點「自訂金額」輸入任意數字，全程不需記指令。"),
            {"type": "separator", "margin": "lg"},
            make_subtitle("匯率走勢圖"),
            make_desc("在匯率查詢選單中選「匯率走勢圖」，選擇幣別後，會產生近 6 個月的現金匯率和即期匯率兩張走勢圖。查詢匯率後卡片底部也有「走勢圖」按鈕可直接查看。"),
        ])
        follow_bubble = make_bubble("🔔 關注與自動通知", "#9C27B0", [
            make_subtitle("關注外幣"),
            make_desc("查詢匯率後，卡片底部有「加入關注」按鈕。點擊後可選擇：不設條件直接關注、低於某匯率時通知、或高於某匯率時通知。系統會以當前匯率作為參考值。"),
            make_desc("輸入「我的外幣」可查看已關注的外幣清單、即時匯率與通知條件。每個幣別旁有「刪除」按鈕可移除，未設定條件的幣別有「設定條件」按鈕可補設。"),
            {"type": "separator", "margin": "lg"},
            make_subtitle("自動通知時間"),
            make_desc("匯率：每天早上 9 點自動檢查所有關注的外幣，匯率符合您設定的條件時會主動推播通知。"),
            make_desc("股票：每個交易日（週一至週五）下午 1:35 收盤後自動檢查，符合條件時主動推播。"),
            make_desc("油價週報：每週六、日中午 12 點自動推播本週油價與下週預測，所有用戶都會收到，不需額外設定。"),
        ])
        life_bubble = make_bubble("⛽ 生活資訊", "#FF6600", [
            make_subtitle("油價查詢"),
            make_desc("在主選單點「油價查詢」，會顯示中油最新油價（92無鉛、95無鉛、98無鉛、超級柴油），同時顯示下週預計調整幅度與變動百分比。"),
            {"type": "separator", "margin": "lg"},
            make_subtitle("天氣查詢"),
            make_desc("在主選單點「最新氣象」，會顯示天氣功能圖片選單，包含雷達回波和即時天氣等。也可以直接輸入「雷達回波」查看中央氣象署即時雷達回波圖。"),
            {"type": "separator", "margin": "lg"},
            make_subtitle("更多功能"),
            make_desc("輸入「開始玩」可顯示完整功能選單，包含投資工具、財經資訊、房地產、生活資訊、AI 工具等五個分類，每個分類有三個外部連結或功能按鈕可使用。"),
        ])
        sticker_bubble = {
            "type": "bubble", "size": "mega",
            "header": {"type": "box", "layout": "vertical", "contents": [
                {"type": "text", "text": "🐱 阿生生貼圖", "weight": "bold", "size": "lg", "color": "#FF6600", "align": "center"}
            ], "paddingAll": "15px"},
            "hero": {
                "type": "image",
                "url": "https://stickershop.line-scdn.net/stickershop/v1/product/26305076/LINEStorePC/main.png?v=1",
                "size": "full", "aspectRatio": "1.51:1", "aspectMode": "fit"
            },
            "body": {"type": "box", "layout": "vertical", "contents": [
                make_desc("阿生生是我家的橘貓，現在也是你的財經小幫手！快來下載阿生生的可愛貼圖，讓聊天更有趣！"),
            ], "paddingAll": "15px"},
            "footer": {"type": "box", "layout": "vertical", "contents": [
                {"type": "button", "style": "primary", "color": "#FF6600", "height": "sm",
                 "action": {"type": "uri", "label": "前往下載貼圖", "uri": "https://line.me/S/sticker/26305076/?lang=zh-Hant"}}
            ], "paddingAll": "10px"}
        }
        usage_flex = FlexSendMessage(
            alt_text="使用說明",
            contents={"type": "carousel", "contents": [stock_bubble, currency_bubble, follow_bubble, life_bubble, sticker_bubble]}
        )
        line_bot_api.reply_message(event.reply_token, usage_flex)
        return 0
    if re.match("理財YOUTUBER推薦", msg):
        content = Msg_Template.youtube_channel()
        line_bot_api.reply_message(event.reply_token, content)
        return 0
    if re.match('分析趨勢',msg):
        line_bot_api.reply_message(event.reply_token,
            TextSendMessage(text="此功能暫待推出，敬請見諒～～"))
        return 0
    if re.match('房地資訊|房地產|地籍',msg):
        def house_bubble(title, links):
            btns = []
            colors = ["#4CAF50", "#2196F3", "#FF9800", "#9C27B0", "#E91E63"]
            for i, (label, url) in enumerate(links):
                btns.append({"type": "button", "style": "primary", "color": colors[i % len(colors)], "height": "sm",
                             "action": {"type": "uri", "label": label, "uri": url}})
            return {
                "type": "bubble", "size": "mega",
                "header": {"type": "box", "layout": "vertical", "contents": [
                    {"type": "text", "text": title, "weight": "bold", "size": "md", "color": "#4CAF50", "align": "center"}
                ], "paddingAll": "12px"},
                "body": {"type": "box", "layout": "vertical", "contents": btns, "spacing": "sm", "paddingAll": "12px"}
            }
        b1 = house_bubble("🏠 房屋交易", [
            ("🐱 阿生地圖", "https://map.windsky-sky.com"),
            ("內政部實價登錄", "https://lvr.land.moi.gov.tw/"),
            ("591 房屋交易", "https://www.591.com.tw/"),
            ("Google 地圖", "https://www.google.com.tw/maps"),
        ])
        b2 = house_bubble("🗺️ 地籍圖資", [
            ("國土測繪圖資(電腦版)", "https://maps.nlsc.gov.tw/T09/mapshow.action?In_type=web"),
            ("國土測繪圖資(手機版)", "https://maps.nlsc.gov.tw/T09/mobilemap.action"),
            ("地籍圖資便民(新版)", "https://easymap.moi.gov.tw/Z10Web/Normal"),
            ("地籍圖資便民(舊版)", "https://easymap.moi.gov.tw/Index"),
        ])
        b3 = house_bubble("🏙️ 高雄地政", [
            ("高雄地籍圖資(新版)", "https://gisdawh.kcg.gov.tw/landeasy2"),
            ("高雄地籍圖資(舊版)", "https://gisdawh.kcg.gov.tw/landeasy/page.cfm?major=12"),
            ("高雄都市計畫", "https://urbangis.kcg.gov.tw/UBA/web_page/UBA010100.jsp"),
            ("高雄地政綜合查詢", "https://eqs-landp.kcg.gov.tw/KCG_SYN_QUERY/SynthesisQuery?captchaCode=GISDAWH,C,18,2229,05450000&postWindowType=SYN"),
        ])
        b4 = house_bubble("🏗️ 建築 / 國土", [
            ("全國建築執照查詢", "https://cloudbm.nlma.gov.tw/CPTL/cpt0407m.do?"),
            ("國土規劃圖台", "https://nsp.nlma.gov.tw/ngis/"),
            ("水庫集水區查詢", "https://web.wra.gov.tw/wratppr/sencad/"),
        ])
        b5 = house_bubble("🔍 生活查詢", [
            ("重要設施查詢", "https://service.map.com.tw/houseol/AnalysisObject.aspx"),
            ("工商登記查詢", "https://findbiz.nat.gov.tw/fts/query/QueryBar/queryInit.do"),
            ("捷運離你多遠", "https://mrtexit.com/"),
        ])
        b6 = house_bubble("📋 地籍資料查詢系統（軟體）", [
            ("📦 完整安裝包(首次/含模組)", "https://www.dropbox.com/scl/fi/cc4cfo3gufikbjtsotx66/v1.1.7a.rar?rlkey=fk9r4typfo31flfx2q31z1mue&dl=0"),
            ("🔄 程式更新檔(GitHub)", "https://github.com/windskyshao/tw-land-tools/releases/latest"),
            ("📖 使用說明 / 教學", "https://fyy-l8a3.onrender.com/help"),
        ])
        house_flex = FlexSendMessage(
            alt_text="房地資訊",
            contents={"type": "carousel", "contents": [b1, b2, b3, b4, b5, b6]}
        )
        line_bot_api.reply_message(event.reply_token, house_flex)
        return 0
    ############################### 股票區 ################################
    
    if re.match(r'關注[0-9]{4,6}[<>][0-9]' ,msg):
        m = re.match(r'關注([0-9]{4,6})([<>])(.*)', msg)
        stockNumber = m.group(1)
        content = mongodb.write_my_stock(uid, user_name, stockNumber, m.group(2), m.group(3))
        # 上限訊息以 ❌ 開頭，只回文字
        if isinstance(content, str) and content.startswith('❌'):
            line_bot_api.reply_message(event.reply_token, TextSendMessage(content))
            return 0
        # 一般情況：回文字 + 重發詳情頁 flex，讓使用者立刻看到「目前條件」更新
        msgs = [TextSendMessage(content)]
        detail = build_stock_detail_flex(stockNumber, user_name)
        if detail is not None:
            msgs.append(detail)
        line_bot_api.reply_message(event.reply_token, msgs)
        return 0
    if re.match(r'自訂股條[0-9]{4,6}[<>]', msg):
        m = re.match(r'自訂股條([0-9]{4,6})([<>])', msg)
        stock_code = m.group(1)
        op = m.group(2)
        stock_name = get_stock_name(stock_code)
        mat_d[uid] = f"關注股{stock_code}{op}"
        cond_word = "低於" if op == '<' else "高於"
        hint_buttons = [
            QuickReplyButton(action=MessageAction(label="↩ 返回詳情", text=f"#{stock_code}")),
        ]
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=f"請輸入 {stock_name}({stock_code}) 要{cond_word}多少時通知（數字），例如 100",
                quick_reply=QuickReply(items=hint_buttons)
            )
        )
        return 0
    # 查詢股票篩選條件清單
    if re.match('股票清單',msg):
        my_flex = build_my_stock_flex(uid, user_name)
        if my_flex:
            line_bot_api.reply_message(event.reply_token, [
                TextSendMessage('稍等一下, 股票查詢中...'),
                my_flex
            ])
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("您的股票清單為空，請先透過「關注」按鈕加入"))
        return 0
    if re.match('股價查詢|查股票|查股價', msg):
        popular_stocks = [
            ("2330", "台積電"), ("2317", "鴻海"),
            ("2454", "聯發科"), ("2303", "聯電"),
            ("2881", "富邦金"), ("2882", "國泰金"),
            ("2412", "中華電"), ("2886", "兆豐金"),
            ("0050", "元大50"), ("0056", "高股息"),
            ("3711", "日月光"), ("00878","國泰永續"),
        ]
        col1 = []
        col2 = []
        for i, (code, name) in enumerate(popular_stocks):
            btn = {
                "type": "button", "style": "secondary", "height": "sm",
                "action": {"type": "message", "label": f"{name}({code})", "text": f"#{code}"}
            }
            if i % 2 == 0:
                col1.append(btn)
            else:
                col2.append(btn)
        stock_menu = FlexSendMessage(
            alt_text="股價查詢 - 熱門股票",
            contents={
                "type": "bubble", "size": "mega",
                "header": {
                    "type": "box", "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "📈 熱門股票", "weight": "bold", "size": "lg", "color": "#1DB446"},
                        {"type": "text", "text": "點選查詢，或直接輸入代號 / 公司名稱", "size": "xs", "color": "#888888", "margin": "sm"}
                    ], "paddingAll": "15px"
                },
                "body": {
                    "type": "box", "layout": "horizontal",
                    "contents": [
                        {"type": "box", "layout": "vertical", "contents": col1, "spacing": "sm", "flex": 1},
                        {"type": "box", "layout": "vertical", "contents": col2, "spacing": "sm", "flex": 1, "margin": "sm"}
                    ], "paddingAll": "10px"
                },
                "footer": {
                    "type": "box", "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "💡 也可以直接輸入公司名稱搜尋", "size": "xs", "color": "#888888", "align": "center"},
                        {"type": "text", "text": "例如：台積電、鴻海、富邦", "size": "xs", "color": "#aaaaaa", "align": "center", "margin": "sm"}
                    ], "paddingAll": "10px"
                }
            }
        )
        line_bot_api.reply_message(event.reply_token, stock_menu)
        return 0
    if(msg.startswith('#')):
        text = msg[1:]
        # 支援 #代碼@關鍵字 格式：從中文搜尋點進來時，把關鍵字帶著，詳情頁才能再列出其他搜尋結果
        search_keyword = None
        if '@' in text:
            text, search_keyword = text.split('@', 1)
        try:
            stock_flex = build_stock_detail_flex(text, user_name, search_keyword)
            if stock_flex is None:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f'股票 {text} 查無資料，請確認代號是否正確')
                )
                return 0
            line_bot_api.reply_message(event.reply_token, stock_flex)
        except Exception as e:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f'股票查詢發生錯誤: {str(e)}'))
        return 0
    # 刪除存在資料庫裡面的股票
    if re.match(r'刪除[0-9]{4,6}',msg):
        stock_code = msg[2:]
        stock_name = get_stock_name(stock_code)
        mongodb.delete_my_stock(user_name, stock_code)
        my_flex = build_my_stock_flex(uid, user_name)
        if my_flex:
            line_bot_api.reply_message(event.reply_token, [
                TextSendMessage(f"✓ 已刪除 {stock_name}({stock_code})"),
                my_flex
            ])
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("股票清單已清空"))
        return 0
    # 清空存在資料庫裡面的股票
    if re.match('清空股票',msg):
        content = mongodb.delete_my_allstock( user_name, uid)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(content))
        return 0
    if event.message.text[:2].upper() == "@K": #這段主要在畫k線圖
        input_word = event.message.text.strip()
        parts = input_word[2:].strip().split()
        stock_name = parts[0] if parts else ''
        period_str = parts[1] if len(parts) > 1 else '1y'
        if not stock_name:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="請使用格式：@K股票代號 期間，例如：@K2330 6m")
            )
            return 0

        # 支援期間簡寫：3m=3個月, 6m=半年, 1y=1年, 3y=3年
        from dateutil.relativedelta import relativedelta
        period_map = {
            '3m': relativedelta(months=3),
            '6m': relativedelta(months=6),
            '1y': relativedelta(years=1),
            '2y': relativedelta(years=2),
            '3y': relativedelta(years=3),
            '5y': relativedelta(years=5),
        }
        if period_str in period_map:
            start_date = (datetime.datetime.now() - period_map[period_str]).strftime('%Y-%m-%d')
        elif re.match(r'\d{4}-\d{2}-\d{2}', period_str):
            start_date = period_str
        else:
            start_date = (datetime.datetime.now() - relativedelta(years=1)).strftime('%Y-%m-%d')
        try:
            k_stock_name = get_stock_name(stock_name)
            img_url = plot_stock_k_chart(IMGUR_CLIENT_ID, stock_name, start_date)
            if img_url:
                line_bot_api.reply_message(event.reply_token, [
                    TextSendMessage(text=f"{k_stock_name}({stock_name}) K線圖"),
                    ImageSendMessage(original_content_url=img_url, preview_image_url=img_url)
                ])
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"股票 {stock_name} K線圖繪製失敗，請確認代號是否正確")
                )
        except Exception as e:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"K線圖發生錯誤: {str(e)}"))
        return 0
    ################################ 目錄區 ##########################################
    if event.message.text == "開始玩":
        def card(title, subtitle, color, buttons):
            return {
                "type": "bubble", "size": "kilo",
                "header": {"type": "box", "layout": "vertical", "contents": [
                    {"type": "text", "text": title, "weight": "bold", "size": "lg", "color": color, "align": "center"},
                    {"type": "text", "text": subtitle, "size": "xs", "color": "#888888", "align": "center", "margin": "sm"}
                ], "paddingAll": "12px", "backgroundColor": "#FAFAFA"},
                "body": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": buttons, "paddingAll": "10px"}
            }
        def btn(label, text_or_uri, color, is_uri=False):
            action = {"type": "uri", "label": label, "uri": text_or_uri} if is_uri else {"type": "message", "label": label, "text": text_or_uri}
            return {"type": "button", "style": "primary", "height": "sm", "color": color, "action": action}

        card1 = card("🏠 主選單", "快捷功能入口", "#FF6600", [
            btn("股價查詢", "股價查詢", "#1976D2"),
            btn("油價查詢", "油價查詢", "#FF7043"),
            btn("匯率查詢", "匯率查詢", "#26A69A"),
            btn("房地資訊", "房地資訊", "#8D6E63"),
            btn("最新氣象", "最新氣象", "#00ACC1"),
            btn("使用說明", "使用說明", "#78909C"),
        ])
        card2 = card("📈 投資理財", "股票 / 匯率 / 財經", "#1DB446", [
            btn("關注的股票", "股票清單", "#43A047"),
            btn("我的外幣", "我的外幣", "#00897B"),
            btn("財經新聞", "https://tw.stock.yahoo.com/news/", "#1565C0", True),
            btn("奇摩股市", "https://tw.stock.yahoo.com/", "#1976D2", True),
            btn("財經PTT", "https://www.ptt.cc/bbs/Finance/index.html", "#5C6BC0", True),
            btn("理財YouTube(柴鼠兄弟)", "https://www.youtube.com/channel/UC45i13dEfEVac2IEJT_Nr5Q", "#E53935", True),
        ])
        card3 = card("🌤 生活資訊", "天氣 / 新聞 / 實用工具", "#FF9800", [
            btn("最新氣象", "最新氣象", "#00ACC1"),
            btn("雷達回波", "雷達回波", "#0288D1"),
            btn("時事新聞(聯合)", "https://udn.com/news/breaknews/1", "#E64A19", True),
            btn("台灣電力即時資訊", "https://www.taipower.com.tw/tc/page.aspx?mid=206", "#F9A825", True),
            btn("高鐵時刻查詢", "https://www.thsrc.com.tw/ArticleContent/a3b630bb-070c-4f76-b26a-2cc257efa001", "#6D4C41", True),
            btn("台鐵時刻查詢", "https://tip.railway.gov.tw/tra-tip-web/tip/tip001/tip112/querybytrainno", "#00695C", True),
        ])
        card4 = card("🤖 AI 工具", "人工智慧 / 學習資源", "#9C27B0", [
            btn("ChatGPT", "https://chat.openai.com/", "#10A37F", True),
            btn("Claude AI", "https://claude.ai/", "#D97706", True),
            btn("Perplexity AI搜尋", "https://www.perplexity.ai/", "#1E88E5", True),
            btn("Google Gemini", "https://gemini.google.com/", "#4285F4", True),
            btn("程式教學YouTube", "https://www.youtube.com/channel/UCPhn2rCqhu0HdktsFjixahA", "#E53935", True),
            btn("AI新聞(The Verge)", "https://www.theverge.com/ai-artificial-intelligence", "#7B1FA2", True),
        ])
        card5 = card("🐱 阿生生貼圖", "下載可愛的阿生生！", "#FF6600", [
            btn("前往下載貼圖", "https://line.me/S/sticker/26305076/?lang=zh-Hant", "#FF6600", True),
            btn("更多作者貼圖", "https://store.line.me/stickershop/author/4668996/zh-Hant", "#FF8A65", True),
        ])
        message = FlexSendMessage(
            alt_text='目錄選單',
            contents={"type": "carousel", "contents": [card1, card2, card3, card4, card5]}
        )
        line_bot_api.reply_message(event.reply_token, message)
        return 0
    if re.match("股價提醒", msg):
        try:
            my_flex = build_my_stock_flex(uid, user_name)
            if my_flex:
                line_bot_api.reply_message(event.reply_token, [
                    TextSendMessage('稍等一下, 條件檢查中...'),
                    my_flex
                ])
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="您的股票清單為空，請先透過「關注」按鈕加入"))
        except Exception as e:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"股價查詢發生錯誤: {str(e)}"))
        return 0
    ################################################匯率推播#######################################
    if re.match("匯率推播", msg):
        try:
            dataList = cache_users_currency()
            rows = []
            for user_currencies in dataList:
                for entry in user_currencies:
                    if entry['userID'] != uid:
                        continue
                    currency = entry['favorite_currency']
                    condition = entry.get('condition', '未設定')
                    price = entry.get('price', '未設定')
                    currency_name = mongodb.currency_list.get(currency, currency)
                    try:
                        rate_val, rate_type = get_sell_rate(currency)
                        if rate_val is None:
                            rate = 0
                            rate_text = '無資料'
                        else:
                            rate = float(rate_val)
                            rate_text = f"{rate} (現金)" if rate_type == '現金' else str(rate)
                    except:
                        rate_text = '查詢失敗'
                        rate = 0
                    # 判斷狀態
                    if condition == '未設定':
                        status_text = "未設定條件"
                        status_color = "#888888"
                    elif condition == '<' and rate and rate < float(price):
                        status_text = f"✅ 已低於 {price}"
                        status_color = "#1DB446"
                    elif condition == '>' and rate and rate > float(price):
                        status_text = f"✅ 已高於 {price}"
                        status_color = "#1DB446"
                    else:
                        status_text = f"條件：{condition}{price}（未達）"
                        status_color = "#FF9800"
                    # 主行
                    rows.append({
                        "type": "box", "layout": "horizontal", "margin": "lg",
                        "contents": [
                            {"type": "text", "text": f"{currency_name}", "size": "sm", "color": "#333333", "flex": 2},
                            {"type": "text", "text": rate_text, "size": "sm", "weight": "bold", "align": "end", "flex": 2, "color": "#2196F3"},
                        ]
                    })
                    # 狀態行 + 設定按鈕
                    status_contents = [
                        {"type": "text", "text": status_text, "size": "xxs", "color": status_color, "flex": 4}
                    ]
                    if condition == '未設定':
                        status_contents.append({
                            "type": "box", "layout": "vertical", "flex": 0, "width": "60px", "height": "22px",
                            "contents": [{"type": "text", "text": "設定條件", "size": "xxs", "color": "#FFFFFF", "align": "center", "gravity": "center"}],
                            "backgroundColor": "#2196F3", "cornerRadius": "11px", "justifyContent": "center",
                            "action": {"type": "message", "label": "設定", "text": f"關注外幣{currency}"}
                        })
                    rows.append({
                        "type": "box", "layout": "horizontal", "margin": "sm",
                        "contents": status_contents
                    })
                    rows.append({"type": "separator", "margin": "md"})
            if rows:
                if rows[-1].get('type') == 'separator':
                    rows.pop()
                flex = FlexSendMessage(
                    alt_text="匯率推播結果",
                    contents={
                        "type": "bubble",
                        "header": {
                            "type": "box", "layout": "vertical",
                            "contents": [
                                {"type": "text", "text": "📢 匯率推播", "weight": "bold", "size": "lg", "color": "#2196F3"},
                                {"type": "text", "text": "即期賣出匯率 vs 您的通知條件", "size": "xs", "color": "#888888", "margin": "sm"}
                            ], "paddingAll": "15px"
                        },
                        "body": {
                            "type": "box", "layout": "vertical",
                            "contents": rows,
                            "paddingAll": "15px"
                        },
                        "footer": {
                            "type": "box", "layout": "horizontal",
                            "contents": [
                                {"type": "button", "style": "link", "height": "sm",
                                 "action": {"type": "message", "label": "↩ 我的外幣", "text": "我的外幣"}},
                                {"type": "button", "style": "link", "height": "sm",
                                 "action": {"type": "message", "label": "↩ 匯率查詢", "text": "匯率查詢"}}
                            ], "spacing": "sm", "paddingAll": "10px"
                        }
                    }
                )
                line_bot_api.reply_message(event.reply_token, flex)
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="您的外幣清單為空，請先透過外幣查詢頁面加入關注"))
        except Exception as e:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"匯率查詢發生錯誤: {str(e)}"))
        return 0

    #＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊weather＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊
    if re.match('最新氣象|查詢天氣|天氣查詢|weather|Weather|即時天氣預報|即時天氣|即時氣象|天氣預報|預報天氣', msg):
        line_bot_api.reply_message(event.reply_token, place.select_city_direct_links('weather'))
        return 0

    if re.match('潮汐預報', msg):
        line_bot_api.reply_message(event.reply_token, place.select_city_direct_links('tide'))
        return 0

    if re.match('港口天氣', msg):
        line_bot_api.reply_message(event.reply_token, place.select_city_direct_links('harbor'))
        return 0

    if re.match('雷達回波', msg):
        url = 'https://www.cwa.gov.tw/Data/radar/CV1_3600.png'
        radar_img = ImageSendMessage(
            original_content_url=url,
            preview_image_url=url
        )
        line_bot_api.reply_message(event.reply_token, radar_img)
        return 0
    ######################## 房地查詢（直接打地址/地號 → 地籍＋周邊實價）########
    # 放在中文股票搜尋之前，但條件很嚴（要像「…路N號」或「X區X段地號」）才觸發，不會誤撞一般詞/股票名。
    if realestate.looks_like_realestate(original_msg):
        show_loading(getattr(event.source, "user_id", None))   # 先顯示「…」查詢中(此查詢會連地籍/實價，較久)
        err = False
        try:
            res = realestate.query(original_msg)
        except Exception:
            res = None; err = True
        # 段名缺行政區 → 使用者從候選挑
        if isinstance(res, dict) and res.get("type") == "section_picker":
            matches = res.get("matches", [])
            sect = res.get("sect", "")
            no = res.get("no", "")
            city_names = {"E": "高雄市", "D": "台南市", "T": "屏東縣"}
            items = []
            # LINE quick reply 最多 13 顆
            for m in matches[:13]:
                area_disp = f"{city_names.get(m['city'], '')}{m['area_name']}"
                # 送出時帶完整前綴，重新觸發查詢
                send_text = f"{area_disp}{m['sect_name']}{no}"
                label = f"{area_disp}{m['sect_name']}"[:20]
                items.append(QuickReplyButton(action=MessageAction(label=label, text=send_text)))
            tip = f"「{sect}{no}」在多處都有 ({len(matches)} 筆)，請選擇："
            if len(matches) > 13:
                tip += f"\n(僅列前 13 筆，或請直接打縣市+區+段+號)"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=tip, quick_reply=QuickReply(items=items))
            )
            return 0
        if res:
            alt, contents = res
            line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text=alt[:60], contents=contents))
            return 0
        if err:
            msg = "查詢時連線出了點問題 😥 請稍等幾秒再試一次。"
        else:
            msg = ("查不到這個地址／地號 😅 可能原因：\n"
                   "① 打錯或不完整 → 地址例：高雄市鼓山區美術館路187號；地號可直接打「段名+號」讓系統反查\n"
                   "② 目前實價只有【高雄／台南／屏東】三縣市\n"
                   "③ 太新的門牌可能還查不到")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        return 0

    ######################## 中文搜尋股票 ################################
    if len(original_msg) >= 2 and not re.match('^[A-Za-z0-9#@]', original_msg):
        results = search_stock_by_name(original_msg)
        if results:
            buttons = []
            for code, name in results[:8]:
                buttons.append(
                    QuickReplyButton(action=MessageAction(label=f"{name} {code}", text=f"#{code}@{original_msg}"))
                )
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"找到以下與「{original_msg}」相關的股票：",
                    quick_reply=QuickReply(items=buttons)
                )
            )
            return 0

    ######################## 社區名／公寓大廈名（放最後：前面指令都沒中，才試當作名稱查詢）########
    if len(original_msg) >= 2 and not re.match(r'^[A-Za-z0-9#@／/\s]+$', original_msg):
        show_loading(getattr(event.source, "user_id", None), 20)
        try:
            res = realestate.name_query(original_msg)
        except Exception:
            res = None
        if res:
            alt, contents = res
            line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text=alt[:60], contents=contents))
            return 0

    ######################## 未知指令預設回覆 ################################
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(
            text="抱歉，我不太懂您的意思 😅\n\n可以試試以下指令：\n📈 #2330（股價查詢）\n💱 外幣USD（匯率查詢）\n⛽ 油價查詢\n🌤 最新氣象\n🏠 直接打地址/地號/社區名\n\n或輸入「使用說明」查看所有功能",
            quick_reply=QuickReply(
                items=[
                    QuickReplyButton(action=MessageAction(label="使用說明", text="使用說明")),
                    QuickReplyButton(action=MessageAction(label="開始玩", text="開始玩")),
                    QuickReplyButton(action=MessageAction(label="油價查詢", text="油價查詢")),
                    QuickReplyButton(action=MessageAction(label="查美元匯率", text="外幣USD")),
                ]
            )
        )
    )

@handler.add(PostbackEvent)
def handle_postback(event):
    data = dict(x.split('=') for x in event.postback.data.split('&'))
    uid = event.source.user_id
    profile = line_bot_api.get_profile(uid)
    user_name = profile.display_name
    action = data.get('action', '')
    stock = data.get('stock', '')
    if action == 'follow' and stock:
        result = mongodb.write_my_stock(uid, user_name, stock, '>', '0')
        if isinstance(result, str) and result.startswith('❌'):
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=result))
        else:
            # 重新組詳情頁 flex，按鈕狀態會變成「★已關注」
            msgs = [TextSendMessage(text=f"✓ 已關注 {stock}")]
            detail = build_stock_detail_flex(stock, user_name)
            if detail is not None:
                msgs.append(detail)
            line_bot_api.reply_message(event.reply_token, msgs)
    elif action == 'unfollow' and stock:
        mongodb.delete_my_stock(user_name, stock)
        msgs = [TextSendMessage(text=f"✓ 已取消關注 {stock}")]
        detail = build_stock_detail_flex(stock, user_name)
        if detail is not None:
            msgs.append(detail)
        line_bot_api.reply_message(event.reply_token, msgs)

@handler.add(FollowEvent)
def handle_follow(event):
    try:
        profile = line_bot_api.get_profile(event.source.user_id)
        mongodb.save_follower(event.source.user_id, profile.display_name)
    except:
        mongodb.save_follower(event.source.user_id)
    welcome_flex = FlexSendMessage(
        alt_text="歡迎加入阿生生！",
        contents={
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "阿生生 財經小幫手",
                        "weight": "bold",
                        "size": "xl",
                        "color": "#1DB446",
                        "align": "center"
                    },
                    {
                        "type": "text",
                        "text": "歡迎您的加入！以下是我的功能介紹",
                        "size": "sm",
                        "color": "#888888",
                        "align": "center",
                        "margin": "md"
                    }
                ],
                "paddingAll": "20px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": "📈", "flex": 0, "size": "lg"},
                            {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {"type": "text", "text": "股票查詢", "weight": "bold", "size": "md"},
                                    {"type": "text", "text": "輸入 #股票代號 查即時股價\n例如：#2330", "size": "xs", "color": "#888888", "wrap": True}
                                ],
                                "margin": "lg"
                            }
                        ],
                        "margin": "lg"
                    },
                    {"type": "separator", "margin": "lg"},
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": "💱", "flex": 0, "size": "lg"},
                            {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {"type": "text", "text": "匯率查詢", "weight": "bold", "size": "md"},
                                    {"type": "text", "text": "輸入 外幣USD 查匯率\n輸入 換匯USD/TWD/100 換算", "size": "xs", "color": "#888888", "wrap": True}
                                ],
                                "margin": "lg"
                            }
                        ],
                        "margin": "lg"
                    },
                    {"type": "separator", "margin": "lg"},
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": "⛽", "flex": 0, "size": "lg"},
                            {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {"type": "text", "text": "油價查詢", "weight": "bold", "size": "md"},
                                    {"type": "text", "text": "輸入 油價查詢 查看最新油價", "size": "xs", "color": "#888888", "wrap": True}
                                ],
                                "margin": "lg"
                            }
                        ],
                        "margin": "lg"
                    },
                    {"type": "separator", "margin": "lg"},
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": "🌤", "flex": 0, "size": "lg"},
                            {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                    {"type": "text", "text": "天氣查詢", "weight": "bold", "size": "md"},
                                    {"type": "text", "text": "輸入 最新氣象 或 雷達回波", "size": "xs", "color": "#888888", "wrap": True}
                                ],
                                "margin": "lg"
                            }
                        ],
                        "margin": "lg"
                    }
                ],
                "paddingAll": "20px",
                "spacing": "sm"
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#1DB446",
                        "action": {
                            "type": "message",
                            "label": "開始使用",
                            "text": "開始玩"
                        },
                        "height": "sm"
                    },
                    {
                        "type": "button",
                        "style": "link",
                        "action": {
                            "type": "message",
                            "label": "查看更多功能",
                            "text": "使用說明"
                        },
                        "height": "sm"
                    },
                    {
                        "type": "button",
                        "style": "link",
                        "color": "#FF6600",
                        "action": {
                            "type": "uri",
                            "label": "🐱 下載阿生生貼圖",
                            "uri": "https://line.me/S/sticker/26305076/?lang=zh-Hant"
                        },
                        "height": "sm"
                    }
                ],
                "paddingAll": "15px",
                "spacing": "sm"
            }
        }
    )
    line_bot_api.reply_message(event.reply_token, welcome_flex)

@handler.add(UnfollowEvent)
def handle_unfollow(event):
    mongodb.remove_follower(event.source.user_id)
    print(f"User unfollowed: {event.source.user_id}")

if __name__ == "__main__":
    app.run()









