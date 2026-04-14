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
    """用中文名稱搜尋股票代號"""
    results = []
    try:
        for code, info in twstock.codes.items():
            if keyword in info.name and info.market == '上市':
                results.append((code, info.name))
            if len(results) >= max_results:
                break
        if len(results) < max_results:
            for code, info in twstock.codes.items():
                if keyword in info.name and info.market == '上櫃':
                    results.append((code, info.name))
                if len(results) >= max_results:
                    break
    except:
        pass
    return results
from flask import send_from_directory
#=================這裡是呼叫的內容=====================

app = Flask(__name__)
IMGUR_CLIENT_ID = '66e769b3bc72457'
access_token = 'tgQqCqIxEiMiA2KuMIUF/AgRvhFW1x/ncypXaVt1S5BMEeDFSpfqxGAJ3o13ywqsBaOLBcXr0EwFIplg7RUuxnpphqdm2XqOw9zOrK1tTLwaX7nQ272+jsvuRRXuNVJgkPe6ehImSXAXNlf30aiq2QdB04t89/1O/w1cDnyilFU='
mat_d={}

# 圖片暫存資料夾
CHART_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'charts')
os.makedirs(CHART_DIR, exist_ok=True)
RENDER_URL = 'https://fyy-l8a3.onrender.com'

@app.route('/charts/<filename>')
def serve_chart(filename):
    return send_from_directory(CHART_DIR, filename)





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

        # 優先嘗試 Imgur
        try:
            im = pyimgur.Imgur(IMGUR_CLIENT_ID)
            uploaded_image = im.upload_image(filepath, title=stock + " K chart")
            print(f"Imgur 上傳成功: {uploaded_image.link}")
            return uploaded_image.link
        except Exception as e:
            print(f"Imgur 上傳失敗: {e}，改用本地路由")

        # Imgur 失敗，用本地路由
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
    push_msg(event,"    🌟🌟 查詢方法 🌟🌟   \
                    \n\
                    \n☢本機器人可查詢油價及匯率☢\
                    \n\
                    \n⑥ 油價通知 ➦➦➦ 輸入油價報你知\
                    \n⑥ 匯率通知 ➦➦➦ 輸入查詢匯率\
                    \n⑦ 匯率兌換 ➦➦➦ 換匯USD/TWD\
                    \n⑦ 自動推播 ➦➦➦ 自動推播")
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
    target_url = 'https://gas.goodlife.tw/'
    rs = requests.session()
    res = rs.get(target_url, verify=False)
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')
    title = soup.select('#main')[0].text.replace('\n', '').split('(')[0]
    gas_price = soup.select('#gas-price')[0].text.replace('\n\n\n', '').replace(' ', '')
    cpc = soup.select('#cpc')[0].text.replace(' ', '')
    content = '{}\n{}{}'.format(title, gas_price, cpc)
    return content

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
        line_bot_api.push_message(uid, TextSendMessage(f'您要查詢的外幣是: {original_msg}'))
        content = EXRate.showCurrency(code)
        line_bot_api.push_message(uid, TextSendMessage(content))
        return 0

    # 指令容錯：純4位數字 → 當作股票查詢
    if re.match('^[0-9]{4,6}$', msg):
        msg = '#' + msg

    ######################## 匯率區 ##############################################
    if re.match("匯率大小事", msg):
        btn_msg = Msg_Template.stock_reply_rate()
        line_bot_api.push_message(uid, btn_msg)
        return 0
    if re.match("換匯[A-Z]{3}/[A-Z]{3}", msg):
        line_bot_api.push_message(uid,TextSendMessage("將為您做外匯計算....."))
        content = EXRate.getExchangeRate(msg)
        line_bot_api.push_message(uid, TextSendMessage(content))
        return 0
    if re.match('幣別種類',msg):
        message = Msg_Template.show_Button()
        line_bot_api.reply_message(event.reply_token,message)
        return 0
    if re.match('新增外幣[A-Z]{3}', msg):
        currency = msg[4:7]
        currency_name = EXRate.getCurrencyName(currency)
        if currency_name == "無可支援的外幣": content = "無可支援的外幣"
        elif re.match('新增外幣[A-Z]{3}[<>][0-9]', msg):
            content = mongodb.write_my_currency(uid , user_name, currency, msg[7:8], msg[8:])
        else:
            content = mongodb.write_my_currency(uid , user_name, currency, "未設定", "未設定")
        
        line_bot_api.push_message(uid, TextSendMessage(content))
        return 0
    if re.match('我的外幣', msg):
        line_bot_api.push_message(uid, TextSendMessage('稍等一下, 匯率查詢中...'))
        content = mongodb.show_my_currency(uid, user_name)
        line_bot_api.push_message(uid, TextSendMessage(content))
        return 0
    if re.match('刪除外幣[A-Z]{3}', msg):
        content = mongodb.delete_my_currency(user_name, msg[4:7])
        line_bot_api.push_message(uid, TextSendMessage(content))
        return 0
    
    if re.match('清空外幣', msg):
        content = mongodb.delete_my_allcurrency(user_name, uid)
        line_bot_api.push_message(uid, TextSendMessage(content))
        return 0
    if re.match("CT[A-Z]{3}", msg):
        currency = msg[2:5] # 外幣代號
        if EXRate.getCurrencyName(currency) == "無可支援的外幣":
            line_bot_api.push_message(uid, TextSendMessage('無可支援的外幣'))
            return 0
        line_bot_api.push_message(uid, TextSendMessage('稍等一下, 將會給您匯率走勢圖'))
        cash_imgurl = EXRate.cash_exrate_sixMonth(currency)            
        if cash_imgurl == "現金匯率無資料可分析":
            line_bot_api.push_message(uid, TextSendMessage('現金匯率無資料可分析'))
        else:
            line_bot_api.push_message(uid, ImageSendMessage(original_content_url=cash_imgurl, preview_image_url=cash_imgurl))
        
        spot_imgurl = EXRate.spot_exrate_sixMonth(currency)
        if spot_imgurl == "即期匯率無資料可分析":
            line_bot_api.push_message(uid, TextSendMessage('即期匯率無資料可分析'))
        else:
            line_bot_api.push_message(uid, ImageSendMessage(original_content_url=spot_imgurl, preview_image_url=spot_imgurl))
        btn_msg = Msg_Template.realtime_currency_other(currency)
        line_bot_api.push_message(uid, btn_msg)
        return 0
    if re.match('外幣[A-Z]{3}',msg):
        currency = msg[2:5] # 外幣代號
        currency_name = EXRate.getCurrencyName(currency)
        if currency_name == "無可支援的外幣": 
            content = "無可支援的外幣"
            line_bot_api.push_message(uid, TextSendMessage(content))
        else:
            line_bot_api.push_message(uid, TextSendMessage(f'您要查詢的外幣是: {currency_name}'))
            content = EXRate.showCurrency(currency)
            #content = EXRate.getExchangeRate(msg)
            line_bot_api.push_message(uid, TextSendMessage(content))
        return 0
    ######################## 使用說明 選單 油價報你知################################
    if event.message.text == "油價查詢":
        content = oil_price()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
        return 0
    if event.message.text == "使用說明":
        Usage(event)
        return 0
    if re.match("理財YOUTUBER推薦", msg):
        content = Msg_Template.youtube_channel()
        line_bot_api.push_message(uid, content)
        return 0
    if re.match('分析趨勢',msg):
        message = Msg_Template.stock_reply_trend()
        line_bot_api.reply_message(event.reply_token,message)
        return 0
    ############################### 股票區 ################################
    
    if re.match('關注[0-9]{4}[<>][0-9]' ,msg):
        stockNumber = msg[2:6]
        content = mongodb.write_my_stock(uid, user_name , stockNumber, msg[6:7], msg[7:])
        line_bot_api.push_message(uid, TextSendMessage(content))
        return 0
    # 查詢股票篩選條件清單
    if re.match('股票清單',msg): 
        line_bot_api.push_message(uid, TextSendMessage('稍等一下, 股票查詢中...'))
        content = mongodb.show_stock_setting(user_name, uid)
        line_bot_api.push_message(uid, TextSendMessage(content))
        return 0
    if re.match('股價查詢|查股票|查股價', msg):
        popular_stocks = [
            ("2330", "台積電"), ("2317", "鴻海"), ("2454", "聯發科"),
            ("2881", "富邦金"), ("2882", "國泰金"), ("2303", "聯電"),
            ("0050", "元大50"), ("0056", "高股息"), ("00878", "國泰永續"),
            ("2412", "中華電"), ("3711", "日月光"), ("2886", "兆豐金"),
        ]
        buttons = []
        for code, name in popular_stocks:
            buttons.append({
                "type": "button", "style": "secondary", "height": "sm",
                "action": {"type": "message", "label": f"{name} {code}", "text": f"#{code}"}
            })
        # 分成三欄
        col1 = buttons[0:4]
        col2 = buttons[4:8]
        col3 = buttons[8:12]
        stock_menu = FlexSendMessage(
            alt_text="股價查詢 - 熱門股票",
            contents={
                "type": "bubble", "size": "mega",
                "header": {
                    "type": "box", "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "📈 熱門股票", "weight": "bold", "size": "lg", "color": "#1DB446"},
                        {"type": "text", "text": "點選查詢，或直接輸入代號/公司名稱", "size": "xs", "color": "#888888", "margin": "sm"}
                    ], "paddingAll": "15px"
                },
                "body": {
                    "type": "box", "layout": "horizontal",
                    "contents": [
                        {"type": "box", "layout": "vertical", "contents": col1, "spacing": "sm", "flex": 1},
                        {"type": "box", "layout": "vertical", "contents": col2, "spacing": "sm", "flex": 1, "margin": "sm"},
                        {"type": "box", "layout": "vertical", "contents": col3, "spacing": "sm", "flex": 1, "margin": "sm"}
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
            ticker = yf.Ticker(f"{text}.TW")
            hist = ticker.history(period="7d")

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

            stock_flex = FlexSendMessage(
                alt_text=f"{text} 股價查詢",
                contents={
                    "type": "bubble",
                    "size": "kilo",
                    "header": {
                        "type": "box", "layout": "vertical",
                        "contents": [
                            {
                                "type": "box", "layout": "horizontal",
                                "contents": [
                                    {"type": "text", "text": stock_name, "weight": "bold", "size": "xl", "color": "#333333", "flex": 0},
                                    {"type": "text", "text": text, "size": "md", "color": "#888888", "align": "end", "gravity": "center"}
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
                        "type": "box", "layout": "horizontal",
                        "contents": [
                            {
                                "type": "button", "style": "primary", "color": "#1DB446", "height": "sm",
                                "action": {"type": "message", "label": "K線圖", "text": f"@K{text}2024-01-01"}
                            },
                            {
                                "type": "button", "style": "secondary", "height": "sm",
                                "action": {"type": "message", "label": "加入關注", "text": f"關注{text}>0"}
                            }
                        ],
                        "spacing": "sm", "paddingAll": "10px"
                    }
                }
            )
            line_bot_api.reply_message(event.reply_token, stock_flex)
        except Exception as e:
            line_bot_api.push_message(uid, TextSendMessage(text=f'股票查詢發生錯誤: {str(e)}'))
        return 0
    # 刪除存在資料庫裡面的股票
    if re.match('刪除[0-9]{4}',msg): 
        content = mongodb.delete_my_stock(user_name, msg[2:])
        line_bot_api.push_message(uid, TextSendMessage(content))
        return 0
    # 清空存在資料庫裡面的股票
    if re.match('清空股票',msg): 
        content = mongodb.delete_my_allstock( user_name, uid)
        line_bot_api.push_message(uid, TextSendMessage(content))
        return 0
    if event.message.text[:2].upper() == "@K": #這段主要在畫k線圖
        input_word = event.message.text.replace(" ","")
        stock_name = input_word[2:6]
        start_date = input_word[6:] if len(input_word) > 6 else '2024-01-01'
        try:
            k_stock_name = get_stock_name(stock_name)
            line_bot_api.push_message(uid, TextSendMessage(text=f"正在繪製 {k_stock_name}({stock_name}) K線圖，請稍候..."))
            img_url = plot_stock_k_chart(IMGUR_CLIENT_ID, stock_name, start_date)
            if img_url:
                message = ImageSendMessage(original_content_url=img_url, preview_image_url=img_url)
                line_bot_api.push_message(uid, message)
            else:
                line_bot_api.push_message(uid, TextSendMessage(text=f"股票 {stock_name} K線圖繪製失敗，請確認代號是否正確"))
        except Exception as e:
            line_bot_api.push_message(uid, TextSendMessage(text=f"K線圖發生錯誤: {str(e)}"))
        return 0

    ################################ 目錄區 ##########################################
    if event.message.text == "開始玩":
        message = TemplateSendMessage(
        alt_text='目錄 template',
        template=CarouselTemplate(
            columns=[
                CarouselColumn(
                        thumbnail_image_url='https://i.imgur.com/bGyGdb1.jpg',
                        title='選擇服務',
                        text='請選擇',
                        actions=[
                            MessageAction(
                                label='開始玩',
                                text='開始玩'
                            ),
                            URIAction(
                                label='財經新聞',
                                uri='https://tw.stock.yahoo.com/news/'
                            ),
                            URIAction(
                                label='內政部實價登錄',
                                uri='https://liff.line.me/2006134063-JojNgek2'
                            )
                        ]
                    ),
                CarouselColumn(
                        thumbnail_image_url='https://i.imgur.com/N9TKsay.jpg',
                        title='選擇服務',
                        text='請選擇',
                        actions=[
                            MessageAction(
                                label='other bot',
                                text='imgur bot'
                            ),
                            MessageAction(
                                label='油價報你知',
                                text='油價報你知'
                            ),
                            URIAction(
                                label='奇摩股市',
                                uri='https://tw.stock.yahoo.com/us/?s=NVS&tt=1'
                            )
                        ]
                    ),
                CarouselColumn(
                        thumbnail_image_url='https://i.imgur.com/rwR2yUr.jpg',
                        title='選擇服務',
                        text='請選擇',
                        actions=[
                            URIAction(
                                label='匯率分享',
                                uri='https://rate.bot.com.tw/xrt?Lang=zh-TW'
                            ),
                            URIAction(
                                label='財經PTT',
                                uri='https://www.ptt.cc/bbs/Finance/index.html'
                            ),
                            URIAction(
                                label='youtube 程式教學分享頻道',
                                uri='https://www.youtube.com/channel/UCPhn2rCqhu0HdktsFjixahA'
                            )
                        ]
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, message)
        return 0

    if re.match("股價提醒", msg):
        try:
            dataList = cache_users_stock()
            result = ""
            for user_stocks in dataList:
                for stock_data in user_stocks:
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
                line_bot_api.push_message(uid, TextSendMessage(text=result.strip()))
            else:
                line_bot_api.push_message(uid, TextSendMessage(text="您的股票清單為空，請先透過「關注」指令新增股票"))
        except Exception as e:
            line_bot_api.push_message(uid, TextSendMessage(text=f"股價查詢發生錯誤: {str(e)}"))
        return 0
    ################################################匯率推播#######################################
    if re.match("匯率推播", msg):
        try:
            dataList = cache_users_currency()
            result = ""
            for user_currencies in dataList:
                for entry in user_currencies:
                    if entry['userID'] != uid:
                        continue
                    currency = entry['favorite_currency']
                    condition = entry['condition']
                    price = entry['price']
                    try:
                        realtime_currency = (twder.now(currency))[4]
                        currency_name = mongodb.currency_list.get(currency, currency)
                        result += f"{currency_name} 即期賣出: {realtime_currency}"
                        if condition == "未設定":
                            result += " (未設定條件)"
                        elif condition == '<' and float(realtime_currency) < float(price):
                            result += f" ✅ 符合 < {price}"
                        elif condition == '>' and float(realtime_currency) > float(price):
                            result += f" ✅ 符合 > {price}"
                        else:
                            result += f" (條件: {condition}{price})"
                        result += "\n"
                    except Exception as e:
                        result += f"{currency} 查詢失敗\n"
            if result:
                line_bot_api.push_message(uid, TextSendMessage(text=result.strip()))
            else:
                line_bot_api.push_message(uid, TextSendMessage(text="您的外幣清單為空，請先透過「新增外幣」指令新增"))
        except Exception as e:
            line_bot_api.push_message(uid, TextSendMessage(text=f"匯率查詢發生錯誤: {str(e)}"))
        return 0

    #＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊weather＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊＊
    #圖文選單
    #第一層-最新氣象->4格圖片Flex Message
    if re.match('最新氣象|查詢天氣|天氣查詢|weather|Weather',msg):
        content=place.img_Carousel() #呼叫4格圖片Flex Message
        line_bot_api.reply_message(event.reply_token,content)
        return 0
    ##############################1.即時天氣##############################
    # 1.第二層-即時天氣->呼叫quick_reply
    if re.match('即時天氣|即時氣象',msg):
        mat_d[uid]='即時天氣'
        content=place.quick_reply_weather(mat_d[uid]) #呼叫quick_reply
        line_bot_api.reply_message(event.reply_token,content)
        return 0


    ##############################weather quake############################         
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

@handler.add(FollowEvent)
def handle_follow(event):
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
    print(f"User unfollowed: {event.source.user_id}")

if __name__ == "__main__":
    app.run()