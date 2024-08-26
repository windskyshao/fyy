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
import datetime
import Msg_Template
import EXRate
import mongodb
import twder
import json
import time
import requests
import place



app = Flask(__name__)
IMGUR_CLIENT_ID = '66e769b3bc72457'
access_token = 'tgQqCqIxEiMiA2KuMIUF/AgRvhFW1x/ncypXaVt1S5BMEeDFSpfqxGAJ3o13ywqsBaOLBcXr0EwFIplg7RUuxnpphqdm2XqOw9zOrK1tTLwaX7nQ272+jsvuRRXuNVJgkPe6ehImSXAXNlf30aiq2QdB04t89/1O/w1cDnyilFU='
mat_d={} 

#這段主要在畫k線圖
#pip3 install pyimgur
import yfinance as yf
import mplfinance as mpf
import pyimgur

def plot_stock_k_chart(IMGUR_CLIENT_ID, stock="0050", date_from='2020-01-01'):
    """
    進行個股k線繪製，回傳至於雲端圖床的連結。將顯示包含5MA、20MA及量價關系，起始預設自2020-01-01起迄昨日收盤價。
    :stock "個股代碼(字串)，預設0050。
    :date_from :起始日(字串)，格式為YYYY-MM-DD，預設自2020-01-01起。
    """
    stock = str(stock) + ".TW"
    try:
        #使用yfinance萬取數據
        print(f"正在獲取股票數據:{stock}")
        df = yf.download(stock, start=date_from)

        if df is None or df.empty:
            print(f"未能獲取到股票數據，可能是因為股票代碼不正確或數據來源問題。")
            return None
        
        print("股尉數據獲取成功，盰始繪製 k 線圖...")
        mpf.plot(df, type='candle', mav=(5, 20), volume=True, ylabel=stock.upper() + ' Price',savefig='testsave.png')

        #上傳圖片到Imgur
        PATH = "testsave.png"
        im = pyimgur.Imgur(IMGUR_CLIENT_ID)
        uploaded_image = im.upload_image(PATH, title=stock + " candlestick chart")
        print(f"圖片上傳成功: {uploaded_image.link}")
        return uploaded_image.link
    
    except Exception as e:
        print(f"錯誤: {e}")
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
    app.logger.info("Request body: body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
        # 轉換內容為json格式
        json_data = json.loads(body)
        # 取得回傳訊息的Token (reply mseeage 使用)
        reply_token = json_data['events'][0]['replyToken']
        # 取得使用者 ID (push message 使用)
        user_id = json_data['events'][0]['source']['userId']
        print(json_data)
        if 'message' in json_data['events'][0]:
            if json_data['events'][0]['message']['type'] == 'text':
                # 取出文字
                text = json_data['events'][0]['message']['text']
                # 如果是雷達回波圖相關的文字
                if text == '雷達回波圖' or text == '雷達回波':
                    #傳送雷達回波圖
                    reply_image(f'https://cwbopendata.s3.ap-northeast-1.amazonaws.com/MSC/O-A0058-003.png?{time.time_ns()}',reply_token,access_token)
    except :
        print('error')
    return 'OK'



# 處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # message = TextSendMessage(text=event.message.text)
    # line_bot_api.reply_message(event.reply_token, message)
    msg = str(event.message.text).upper().strip() # 使用者輸入的內容
    profile = line_bot_api.get_profile(event.source.user_id)
   
    usespeak=str(event.message.text) #使用者講的話
    uid = profile.user_id #使用者ID
    user_name = profile.display_name #使用者名稱
    
    ######################## 匯率區 ##############################################    
    if re.match("匯率大小事", msg):
        btn_msg = Msg_Template.stock_reply_rate()
        line_bot_api.push_message(uid, btn_msg)
        return 0
    if re.match("換匯[A-Z]{3}/[A-Z{3}]", msg):
        line_bot_api.push_message(uid,TextSendMessage("將為您做外匯計算....."))
        content = EXRate.getExchangeRate(msg)
        line_bot_api.push_message(uid, TextSendMessage(content))
        return 0
    if re.match('幣別種類',msg):
        message = Msg_Template.show_Button()
        line_bot_api.reply_message(event.reply_token,message)
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
        print(user_name)
    if re.match("理財YOUTUBER推薦", msg):
        content = Msg_Template.youtube_channel()
        line_bot_api.push_message(uid, content)
        return 0
    if re.match('分析趨勢',msg):
        message = Msg_Template.stock_reply_other()
        line_bot_api.reply.message(event.reply_token,message)
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
    if event.message.text == "股價查詢":
        line_bot_api.push_message(uid,TextSendMessage("請輸入#股票代號....."))
    if(msg.startswith('#')):
            text = msg[1:]
            content = ''

            stock_rt = twstock.realtime.get(text)
            my_datetime = datetime.datetime.fromtimestamp(stock_rt['timestamp']+8*60*60)
            my_time = my_datetime.strftime('%H:%M:%S')

            content += '%s (%s) %s\n' %(
                stock_rt['info']['name'],
                stock_rt['info']['code'],
                my_time)
            content += '現價: %s / 開盤: %s\n'%(
                stock_rt['realtime']['latest_trade_price'],
                stock_rt['realtime']['open'])
            content += '最高: %s / 最低: %s\n' %(
                stock_rt['realtime']['high'],
                stock_rt['realtime']['low'])
            content += '量: %s\n' %(stock_rt['realtime']['accumulate_trade_volume'])

            stock = twstock.Stock(text)#twstock.Stock('2330')
            content += '-----\n'
            content += '最近五日價格: \n'
            price5 = stock.price[-5:][::-1]
            date5 = stock.date[-5:][::-1]
            for i in range(len(price5)):
                #content += '[%s] %s\n' %(date5[i].strftime("%Y-%m-%d %H:%M:%S"), price5[i])
                content += '[%s] %s\n' %(date5[i].strftime("%Y-%m-%d"), price5[i])
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=content)
            )
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
    if event.message.text[:2].upper() == "@K": #這段主要在畫k連圖
        input_word = event.message.text.replace(" ","")
        stock_name = input_word[2:6]
        start_date = input_word[6:]
        content = plot_stock_k_chart(IMGUR_CLIENT_ID,stock_name,start_date)
        message = ImageSendMessage(original_content_url= content,preview_image_url=content)
        line_bot_api.reply_message(event.reply_token, message)

    
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
    
    if re.match("股價提醒", msg):
        import schedule
        import time
        # 查看當前股價
        def look_stock_price(stock, condition, price, userID):
            print(userID)
            url = 'https://tw.stock.yahoo.com/q/q?s=' + stock
            list_req = requests.get(url)
            soup = BeautifulSoup(list_req.content, "html.parser")
            getstock = soup.find('span', class_='Fz(32px)').string
            content = stock + "當前股市價格為: " +  getstock
            if condition == '<':
                content += "\n篩選條件為: < "+ price
                if float(getstock) < float(price):
                    content += "\n符合" + getstock + " < " + price + "的篩選條件"
                    line_bot_api.push_message(userID, TextSendMessage(text=content))
            elif condition == '>':
                content += "\n篩選條件為: > "+ price
                if float(getstock) > float(price):
                    content += "\n符合" + getstock + " > " + price + "的篩選條件"
                    line_bot_api.push_message(userID, TextSendMessage(text=content))
            elif condition == "=":
                content += "\n篩選條件為: = "+ price
                if float(getstock) == float(price):
                    content += "\n符合" + getstock + " = " + price + "的篩選條件"
                    line_bot_api.push_message(userID, TextSendMessage(text=content))
        # look_stock_price(stock='2002', condition='>', price=31)
        def job():
            print('HH')
            dataList = cache_users_stock()
            # print(dataList)
            for i in range(len(dataList)):
                for k in range(len(dataList[i])):
                    # print(dataList[i][k])
                    look_stock_price(dataList[i][k]['favorite_stock'], dataList[i][k]['condition'], dataList[i][k]['price'], dataList[i][k]['userID'])
                    # look_stock_price(stock='2002', condition='>', price=31)
        schedule.every(30).seconds.do(job).tag('daily-tasks-stock'+uid,'second') #每10秒執行一次
        #schedule.every().hour.do(job) #每小時執行一次
        #schedule.every().day.at("17:19").do(job) #每天9點30執行一次
        #schedule.every().monday.do(job) #每週一執行一次
        #schedule.every().wednesday.at("14:45").do(job) #每週三14點45執行一次
        # 無窮迴圈
        while True: 
            schedule.run_pending()
            time.sleep(1)
    ################################################匯率推播#######################################
    if re.match("匯率推播", msg):
        import schedule
        import time
        
        def look_currency_price(currency, condition, price, userID):
            print(userID)
            try:
                realtime_currency = (twder.now(currency))[4]
                currency_name = mongodb.currency_list[currency]
                content = currency_name + "當前即期賣出價格為: " + str(realtime_currency)
                if condition == '<':
                    content += "\n篩選條件為: < "+ price
                    if float(realtime_currency) < float(price):
                        content += "\n符合" + realtime_currency + " < " + price + "的篩選條件"
                        # line_bot_api.push_message(userID, TextSendMessage(text=content))
                elif condition == '>':
                    content += "\n篩選條件為: > "+ price
                    if float(realtime_currency) > float(price):
                        content += "\n符合" + realtime_currency + " > " + price + "的篩選條件"
                        # line_bot_api.push_message(userID, TextSendMessage(text=content))
                elif condition == "=":
                    content += "\n篩選條件為: = "+ price
                elif condition == "未設定":
                    content += "\n尚未設置篩選條件, 請設定您想要的目標價格條件,如: 新增外幣"+currency+">10"
                
                else:
                    content += "\n無法判定此外幣設定的篩選條件"
                line_bot_api.push_message(userID, TextSendMessage(text=content))
                print(content)  # 打印内容用于调试
            except Exception as e:
                print(f"Error checking currency: {e}")
        print(cache_users_currency())
        # def job_currency():
        #     print('HH')
        #     dataList = cache_users_currency()
        #     print(dataList)
        #     for i in range(len(dataList)):
        #         for k in range(len(dataList[i])):
        #             look_currency_price(dataList[i][k]['favorite_currency'], dataList[i][k]['condition'], dataList[i][k]['price'], dataList[i][k]['userID'])
        def job_currency():
            print('Running currency check job')
            dataList = cache_users_currency()
            print(f"Data list: {dataList}")
            for user_data in dataList:
                for entry in user_data:
                    look_currency_price(entry['favorite_currency'], entry['condition'], entry['price'], entry['userID'])           
        schedule.every(30).seconds.do(job_currency) #每10秒執行一次
        #schedule.every(30).seconds.do(job_currency) #每10秒執行一次
        #schedule.every().hour.do(job) #每小時執行一次
        #schedule.every().day.at("20:00").do(job) #每天9點30執行一次
        #schedule.every().monday.do(job) #每週一執行一次
        #schedule.every().wednesday.at("14:45").do(job) #每週三14點45執行一次
        # 無窮迴圈
        while True: 
            schedule.run_pending()
            time.sleep(1)

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


import os
if __name__ == "__main__":
    app.run()

#https://opendata.cwb.gov.tw/index
#CWA-C07BDC7E-7138-4068-BCEC-13C15865812A