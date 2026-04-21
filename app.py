# -- coding: utf-8 --**
#載入LineBot所需要的套件
from flask import Flask, request, abort
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
import os
import uuid
from urllib.parse import quote_plus

def get_stock_name(code):
    """取得股票中文名稱，查不到就回傳英文或代號"""
    try:
        info = twstock.codes.get(code)
        if info:
            return info.name
    except:
        pass
    try:
        ticker = yf.Ticker(f"{code}.TW")
        return ticker.info.get('shortName', code)
    except:
        return code

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

# 圖片暫存資料夾
CHART_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'charts')
os.makedirs(CHART_DIR, exist_ok=True)
RENDER_URL = 'https://fyy-l8a3.onrender.com'

@app.route('/charts/<filename>')
def serve_chart(filename):
    return send_from_directory(CHART_DIR, filename)

@app.route('/cron/check_currency')
def cron_check_currency():
    """排程自動檢查匯率條件並推播通知"""
    try:
        db = mongodb.constructor_currency()
        nameList = db.list_collection_names()
        notified = 0
        for col_name in nameList:
            collect = db[col_name]
            entries = list(collect.find({"tag": "currency"}))
            for entry in entries:
                uid = entry.get('userID')
                currency = entry.get('favorite_currency')
                condition = entry.get('condition', '未設定')
                price = entry.get('price', '未設定')
                if condition == '未設定' or price == '未設定' or not uid:
                    continue
                try:
                    now_rate = twder.now(currency)[4]
                    if now_rate == '-':
                        continue
                    current = float(now_rate)
                    target = float(price)
                    cur_name = mongodb.currency_list.get(currency, currency)
                    triggered = False
                    if condition == '<' and current < target:
                        triggered = True
                    elif condition == '>' and current > target:
                        triggered = True
                    if triggered:
                        msg = f"📢 匯率通知\n{cur_name}({currency}) 即期賣出：{current}\n已{'低於' if condition == '<' else '高於'}您設定的 {target}！"
                        line_bot_api.push_message(uid, TextSendMessage(text=msg))
                        notified += 1
                except Exception as e:
                    print(f"[cron] Error checking {currency}: {e}")
        return f"OK, notified={notified}", 200
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/cron/check_stock')
def cron_check_stock():
    """排程自動檢查股票條件並推播通知"""
    try:
        db = mongodb.constructor_stock()
        nameList = db.list_collection_names()
        notified = 0
        for col_name in nameList:
            collect = db[col_name]
            entries = list(collect.find({"tag": "stock"}))
            for entry in entries:
                uid = entry.get('userID')
                stock_code = entry.get('favorite_stock')
                condition = entry.get('condition', '>')
                price = entry.get('price', '0')
                if not uid or not stock_code or price == '0':
                    continue
                try:
                    ticker = yf.Ticker(f"{stock_code}.TW")
                    hist = ticker.history(period="1d")
                    if hist.empty:
                        continue
                    current = hist.iloc[-1]['Close']
                    target = float(price)
                    stock_name = get_stock_name(stock_code)
                    triggered = False
                    if condition == '<' and current < target:
                        triggered = True
                    elif condition == '>' and current > target:
                        triggered = True
                    if triggered:
                        arrow = "低於" if condition == '<' else "高於"
                        msg = f"📢 股票通知\n{stock_name}({stock_code}) 現價：{current:.2f}\n已{arrow}您設定的 {target}！"
                        line_bot_api.push_message(uid, TextSendMessage(text=msg))
                        notified += 1
                except Exception as e:
                    print(f"[cron_stock] Error checking {stock_code}: {e}")
        return f"OK, notified={notified}", 200
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/cron/oil_price')
def cron_oil_price():
    """排程推播下週油價預測給所有追蹤者"""
    try:
        data = oil_price()
        prices = data['prices']
        forecast = data['forecast']
        label_map = {'92': '92無鉛', '95': '95無鉛', '98': '98無鉛', '柴油': '超級柴油', '今日中油油價': None}
        price_lines = ""
        for key, val in prices.items():
            label = label_map.get(key, key)
            if label is None:
                continue
            price_lines += f"  {label}：${val}\n"
        forecast_lines = ""
        if forecast.get('日期'):
            forecast_lines += f"{forecast['日期']}\n"
        if forecast.get('汽油調整'):
            forecast_lines += f"  汽油：{forecast['汽油調整']}\n"
        if forecast.get('柴油預計調整'):
            forecast_lines += f"  柴油：{forecast['柴油預計調整']}\n"
        if forecast.get('變動幅度'):
            forecast_lines += f"  變動幅度：{forecast['變動幅度']}\n"
        msg = f"⛽ 油價週報\n\n本週油價：\n{price_lines}\n📊 下週預測：\n{forecast_lines}"
        followers = mongodb.get_all_followers()
        sent = 0
        for uid in followers:
            try:
                line_bot_api.push_message(uid, TextSendMessage(text=msg.strip()))
                sent += 1
            except Exception as e:
                print(f"[cron_oil] Failed to push to {uid}: {e}")
        return f"OK, sent={sent}", 200
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/keep_alive')
def keep_alive():
    """保持服務清醒用，供 cron-job.org 等監控服務定期 ping"""
    return "alive", 200

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
    進行個股k線繪製。優先上傳 Imgur，失敗時改用本地圖片路由。
    """
    ticker_symbol = str(stock) + ".TW"
    try:
        print(f"正在獲取股票數據: {ticker_symbol}")
        df = yf.download(ticker_symbol, start=date_from)

        if df is None or df.empty:
            print(f"未能獲取到股票數據")
            return None

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
            now_rate = twder.now(cur)[4]
            rate_text = str(float(now_rate)) if now_rate != '-' else '無資料'
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
def oil_price():
    """回傳結構化油價資料 dict"""
    target_url = 'https://gas.goodlife.tw/'
    rs = requests.session()
    res = rs.get(target_url, verify=False)
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

    # 用戶輸入數字 → 接續自訂換匯（優先於股票查詢）
    if uid in mat_d and mat_d[uid].startswith('換匯') and re.match(r'^[\d,.]+$', msg):
        amount_str = msg.replace(',', '')
        try:
            float(amount_str)
            msg = f"{mat_d[uid]}/{amount_str}".upper()
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
        try:
            spot_sell = twder.now(currency)[4]
            current = float(spot_sell) if spot_sell != '-' else 0
        except:
            current = 0
        buttons = [
            QuickReplyButton(action=MessageAction(label="不設條件，直接關注", text=f"新增外幣{currency}")),
            QuickReplyButton(action=MessageAction(label=f"低於 {current:.2f} 通知", text=f"新增外幣{currency}<{current:.2f}")),
            QuickReplyButton(action=MessageAction(label=f"高於 {current:.2f} 通知", text=f"新增外幣{currency}>{current:.2f}")),
        ]
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=f"要關注 {currency_name}({currency})\n目前即期賣出：{current:.2f}\n請選擇通知條件：",
                quick_reply=QuickReply(items=buttons)
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
                mongodb.write_my_currency(uid, user_name, currency, msg[7:8], msg[8:])
            else:
                mongodb.write_my_currency(uid, user_name, currency, "未設定", "未設定")
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
                data = twder.now(currency)
                now_time = str(data[0])
                items = [
                    ("現金買入", data[1]), ("現金賣出", data[2]),
                    ("即期買入", data[3]), ("即期賣出", data[4])
                ]
                rows = []
                for label, val in items:
                    v = "無資料" if val == '-' else str(float(val))
                    rows.append({
                        "type": "box", "layout": "horizontal", "margin": "md",
                        "contents": [
                            {"type": "text", "text": label, "size": "sm", "color": "#555555", "flex": 3},
                            {"type": "text", "text": v, "size": "sm", "weight": "bold", "align": "end", "flex": 2, "color": "#2196F3"}
                        ]
                    })
                currency_flex = FlexSendMessage(
                    alt_text=f"{currency_name}匯率查詢",
                    contents={
                        "type": "bubble",
                        "header": {
                            "type": "box", "layout": "vertical",
                            "contents": [
                                {"type": "text", "text": f"💱 {currency_name} ({currency})", "weight": "bold", "size": "lg", "color": "#2196F3"},
                                {"type": "text", "text": f"掛牌時間：{now_time}", "size": "xs", "color": "#888888", "margin": "sm"}
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
                                        {"type": "button", "style": "primary", "color": "#2196F3", "height": "sm", "flex": 1,
                                         "action": {"type": "message", "label": "走勢圖", "text": f"CT{currency}"}},
                                        {"type": "button", "style": "primary", "color": "#FF9800", "height": "sm", "flex": 1,
                                         "action": {"type": "message", "label": "兌換台幣", "text": f"換匯{currency}/TWD"}},
                                        {"type": "button", "style": "primary", "color": "#FF5252", "height": "sm", "flex": 1,
                                         "action": {"type": "message", "label": "加入關注", "text": f"關注外幣{currency}"}}
                                    ], "spacing": "sm"
                                },
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
    if event.message.text == "油價查詢":
        try:
            data = oil_price()
            prices = data['prices']
            forecast = data['forecast']
            # 油品名稱對照
            label_map = {'92': '92無鉛', '95': '95無鉛', '98': '98無鉛', '柴油': '超級柴油',
                         '今日中油油價': None}
            price_rows = []
            for key, val in prices.items():
                label = label_map.get(key, key)
                if label is None:
                    continue
                price_rows.append({
                    "type": "box", "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": label, "size": "md", "color": "#555555", "flex": 3},
                        {"type": "text", "text": f"${val}", "size": "md", "weight": "bold", "align": "end", "flex": 2, "color": "#FF6600"}
                    ], "margin": "md"
                })
            body_contents = price_rows if price_rows else [{"type": "text", "text": "暫無資料", "wrap": True}]
            # 下週預測
            if forecast:
                body_contents.append({"type": "separator", "margin": "lg"})
                body_contents.append({"type": "text", "text": "📊 下週預測", "size": "sm", "weight": "bold", "color": "#333333", "margin": "lg"})
                if '日期' in forecast:
                    body_contents.append({"type": "text", "text": forecast['日期'], "size": "xs", "color": "#888888", "wrap": True, "margin": "sm"})
                if '汽油調整' in forecast:
                    body_contents.append({
                        "type": "box", "layout": "horizontal", "margin": "sm",
                        "contents": [
                            {"type": "text", "text": "汽油", "size": "sm", "color": "#555555", "flex": 2},
                            {"type": "text", "text": forecast['汽油調整'], "size": "sm", "weight": "bold", "align": "end", "flex": 3,
                             "color": "#1DB446" if '不調整' in forecast['汽油調整'] else "#FF3B30"}
                        ]
                    })
                if '柴油預計調整' in forecast:
                    body_contents.append({
                        "type": "box", "layout": "horizontal", "margin": "sm",
                        "contents": [
                            {"type": "text", "text": "柴油", "size": "sm", "color": "#555555", "flex": 2},
                            {"type": "text", "text": forecast['柴油預計調整'], "size": "sm", "weight": "bold", "align": "end", "flex": 3,
                             "color": "#1DB446" if '0.0' in forecast['柴油預計調整'] else "#FF3B30"}
                        ]
                    })
                if '變動幅度' in forecast:
                    body_contents.append({
                        "type": "box", "layout": "horizontal", "margin": "sm",
                        "contents": [
                            {"type": "text", "text": "變動幅度", "size": "sm", "color": "#555555", "flex": 2},
                            {"type": "text", "text": forecast['變動幅度'], "size": "sm", "weight": "bold", "align": "end", "flex": 3,
                             "color": "#FF3B30" if '-' in forecast['變動幅度'] else "#1DB446"}
                        ]
                    })
            oil_flex = FlexSendMessage(
                alt_text="油價查詢",
                contents={
                    "type": "bubble",
                    "header": {
                        "type": "box", "layout": "vertical",
                        "contents": [
                            {"type": "text", "text": "⛽ 中油最新油價", "weight": "bold", "size": "lg", "color": "#FF6600"},
                            {"type": "text", "text": "單位：元/公升", "size": "xs", "color": "#888888", "margin": "sm"}
                        ], "paddingAll": "15px"
                    },
                    "body": {
                        "type": "box", "layout": "vertical",
                        "contents": body_contents,
                        "paddingAll": "15px"
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
    if re.match('房地資訊|房地產',msg):
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
        house_flex = FlexSendMessage(
            alt_text="房地資訊",
            contents={"type": "carousel", "contents": [b1, b2, b3, b4, b5]}
        )
        line_bot_api.reply_message(event.reply_token, house_flex)
        return 0
    ############################### 股票區 ################################
    
    if re.match(r'關注[0-9]{4,6}[<>][0-9]' ,msg):
        m = re.match(r'關注([0-9]{4,6})([<>])(.*)', msg)
        stockNumber = m.group(1)
        content = mongodb.write_my_stock(uid, user_name, stockNumber, m.group(2), m.group(3))
        line_bot_api.reply_message(event.reply_token, TextSendMessage(content))
        return 0
    # 查詢股票篩選條件清單
    if re.match('股票清單',msg):
        content = mongodb.show_stock_setting(user_name, uid)
        line_bot_api.reply_message(event.reply_token, [
            TextSendMessage('稍等一下, 股票查詢中...'),
            TextSendMessage(content)
        ])
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
        try:
            # 重試機制：yfinance 首次查詢有時會失敗
            hist = pd.DataFrame()
            for attempt in range(2):
                try:
                    ticker = yf.Ticker(f"{text}.TW")
                    hist = ticker.history(period="7d")
                    if hist is not None and not hist.empty:
                        break
                except Exception:
                    pass
                if attempt == 0:
                    time.sleep(1)

            if hist.empty:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f'股票 {text} 查無資料，請確認代號是否正確')
                )
                return 0

            latest = hist.iloc[-1]
            prev_close = hist.iloc[-2]["Close"] if len(hist) >= 2 else latest["Open"]
            change = latest["Close"] - prev_close
            change_pct = (change / prev_close) * 100 if prev_close != 0 else 0
            arrow = "▲" if change >= 0 else "▼"
            change_color = "#FF3B30" if change >= 0 else "#34C759"
            stock_name = get_stock_name(text)

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
            stock_flex = FlexSendMessage(
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
                                    {"type": "text", "text": f"{latest['Close']:.2f}", "size": "xxl", "weight": "bold", "color": change_color},
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
                                    {
                                        "type": "box", "layout": "vertical",
                                        "contents": [
                                            {"type": "text", "text": "開盤", "size": "xs", "color": "#888888"},
                                            {"type": "text", "text": f"{latest['Open']:.2f}", "size": "sm", "weight": "bold"}
                                        ], "flex": 1
                                    },
                                    {
                                        "type": "box", "layout": "vertical",
                                        "contents": [
                                            {"type": "text", "text": "最高", "size": "xs", "color": "#888888"},
                                            {"type": "text", "text": f"{latest['High']:.2f}", "size": "sm", "weight": "bold", "color": "#FF3B30"}
                                        ], "flex": 1
                                    },
                                    {
                                        "type": "box", "layout": "vertical",
                                        "contents": [
                                            {"type": "text", "text": "最低", "size": "xs", "color": "#888888"},
                                            {"type": "text", "text": f"{latest['Low']:.2f}", "size": "sm", "weight": "bold", "color": "#34C759"}
                                        ], "flex": 1
                                    },
                                    {
                                        "type": "box", "layout": "vertical",
                                        "contents": [
                                            {"type": "text", "text": "成交量", "size": "xs", "color": "#888888"},
                                            {"type": "text", "text": f"{int(latest['Volume']):,}", "size": "sm", "weight": "bold"}
                                        ], "flex": 1
                                    }
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
                        "contents": [
                            {"type": "text", "text": "K線圖", "size": "xs", "color": "#888888", "align": "center", "weight": "bold"},
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
                }
            )
            line_bot_api.reply_message(event.reply_token, stock_flex)
        except Exception as e:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f'股票查詢發生錯誤: {str(e)}'))
        return 0
    # 刪除存在資料庫裡面的股票
    if re.match(r'刪除[0-9]{4,6}',msg):
        content = mongodb.delete_my_stock(user_name, msg[2:])
        line_bot_api.reply_message(event.reply_token, TextSendMessage(content))
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
            dataList = cache_users_stock()
            result = ""
            for user_stocks in dataList:
                for stock_data in user_stocks:
                    if stock_data.get('userID') != uid:
                        continue
                    stock_code = stock_data['favorite_stock']
                    condition = stock_data['condition']
                    price = stock_data['price']
                    try:
                        ticker = yf.Ticker(f"{stock_code}.TW")
                        hist = ticker.history(period="1d")
                        if not hist.empty:
                            current_price = f"{hist.iloc[-1]['Close']:.2f}"
                            result += f"{stock_code} 現價: {current_price}"
                            if condition == '<' and float(current_price) < float(price):
                                result += f" >>> 符合 < {price}"
                            elif condition == '>' and float(current_price) > float(price):
                                result += f" >>> 符合 > {price}"
                            else:
                                result += f" (條件: {condition}{price})"
                            result += "\n"
                        else:
                            result += f"{stock_code} 查無資料\n"
                    except Exception as e:
                        result += f"{stock_code} 查詢失敗\n"
            if result:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=result.strip()))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="您的股票清單為空，請先透過「關注」指令新增股票"))
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
                        realtime_currency = (twder.now(currency))[4]
                        rate = float(realtime_currency) if realtime_currency != '-' else 0
                        rate_text = str(rate) if rate else '無資料'
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
    ######################## 中文搜尋股票 ################################
    if len(original_msg) >= 2 and not re.match('^[A-Za-z0-9#@]', original_msg):
        results = search_stock_by_name(original_msg)
        if results:
            buttons = []
            for code, name in results[:8]:
                buttons.append(
                    QuickReplyButton(action=MessageAction(label=f"{name} {code}", text=f"#{code}"))
                )
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"找到以下與「{original_msg}」相關的股票：",
                    quick_reply=QuickReply(items=buttons)
                )
            )
            return 0

    ######################## 未知指令預設回覆 ################################
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(
            text="抱歉，我不太懂您的意思 😅\n\n可以試試以下指令：\n📈 #2330（股價查詢）\n💱 外幣USD（匯率查詢）\n⛽ 油價查詢\n🌤 最新氣象\n\n或輸入「使用說明」查看所有功能",
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
        mongodb.write_my_stock(uid, user_name, stock, '>', '0')
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"✓ 已關注 {stock}"))
    elif action == 'unfollow' and stock:
        mongodb.delete_my_stock(user_name, stock)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"✓ 已取消關注 {stock}"))

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









