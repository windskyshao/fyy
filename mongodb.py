import os
from pymongo import MongoClient
import urllib.parse
import datetime
import EXRate
from line_bot import *

MONGODB_URI = os.environ.get('MONGODB_URI', '')
currency_list = { 
        "USD" : "美元",
        "JPY": "日圓",
        "HKD" :"港幣",
        "GBP": "英鎊",
        "AUD": "澳幣",
        "CAD" : "加拿大幣",
        "CHF" : "瑞士法郎",  
        "SGD" : "新加坡幣",
        "ZAR" : "南非幣",
        "SEK" : "瑞典幣",
        "NZD" : "紐元", 
        "THB" : "泰銖", 
        "PHP" : "菲國比索", 
        "IDR" : "印尼幣", 
        "KRW" : "韓元",   
        "MYR" : "馬來幣", 
        "VND" : "越南盾", 
        "CNY" : "人民幣",
}

####################################################################
#股票機器人 Python基礎教學 【pymongo教學】
####################################################################
followersDB = 'followers'

def constructor_followers():
    client = MongoClient(MONGODB_URI)
    db = client[followersDB]
    return db

def save_follower(user_id, display_name=""):
    db = constructor_followers()
    collect = db['users']
    if not collect.find_one({"userID": user_id}):
        collect.insert_one({
            "userID": user_id,
            "display_name": display_name,
            "date_info": datetime.datetime.now()
        })

def remove_follower(user_id):
    db = constructor_followers()
    collect = db['users']
    collect.delete_one({"userID": user_id})

def get_all_followers():
    db = constructor_followers()
    collect = db['users']
    return [doc['userID'] for doc in collect.find({}, {"userID": 1})]

def get_cron_last_run(key):
    """取得指定 cron 任務上次成功執行的日期字串，沒紀錄回 None"""
    db = constructor_followers()
    collect = db['cron_state']
    doc = collect.find_one({"key": key})
    return doc.get('last_run_date') if doc else None

def set_cron_last_run(key, date_str):
    """記錄指定 cron 任務剛剛執行完的日期，用 upsert 避免重複新增"""
    db = constructor_followers()
    collect = db['cron_state']
    collect.update_one({"key": key}, {"$set": {"last_run_date": date_str}}, upsert=True)


def save_app_file(name, data_b64, updated_iso):
    """存放程式用檔案(如通訊錄.xlsx，base64字串)到 MongoDB，供用戶端下載同步；避免個資進公開 repo。"""
    db = constructor_followers()
    collect = db['app_files']
    collect.update_one({"name": name},
                       {"$set": {"name": name, "data": data_b64, "updated": updated_iso}},
                       upsert=True)


def get_app_file(name):
    """取回程式用檔案，回傳 (data_b64, updated)；沒有回 (None, None)。"""
    db = constructor_followers()
    collect = db['app_files']
    doc = collect.find_one({"name": name})
    if not doc:
        return None, None
    return doc.get('data'), doc.get('updated')

Authdb='test-good1'
stockDB='mydb'
currencyDB = 'users'
dbname = 'test-good1'

# 每位使用者關注上限（控制 LINE 推播免費額度 500/月 與外部 API 用量）
MAX_STOCKS_PER_USER = 5
MAX_CURRENCIES_PER_USER = 5

def constructor_stock():
    client = MongoClient(MONGODB_URI)
    db = client[stockDB]
    return db

def constructor_currency():
    client = MongoClient(MONGODB_URI)
    db = client[currencyDB]
    return db

# --------------------- 檢查使用者是否已關注某股票 ---------------------
def is_stock_followed(user_name, stockNumber):
    db = constructor_stock()
    collect = db[user_name]
    return collect.find_one({"favorite_stock": stockNumber}) is not None
# --------------------- 新增使用者的股票 ---------------------
def write_my_stock(userID, user_name, stockNumber, condition, target_price):
    db=constructor_stock()
    collect = db[user_name]
    is_exit = collect.find_one({"favorite_stock": stockNumber})
    if is_exit != None :
        content = update_my_stock(user_name, stockNumber, condition, target_price)
        return content
    # 新增前檢查上限
    current_count = collect.count_documents({"tag": "stock"})
    if current_count >= MAX_STOCKS_PER_USER:
        return f"❌ 已達上限：每人最多關注 {MAX_STOCKS_PER_USER} 檔股票，請先用「股票清單」刪除不需要的再新增"
    collect.insert_one({
        "userID": userID,
        "favorite_stock": stockNumber,
        "condition": condition,
        "price": target_price,
        "tag": "stock",
        "notified": False,
        "date_info": datetime.datetime.now()
    })
    return f"{stockNumber}已新增至您的股票清單"
# --------------------- 更新暫存的股票名稱 ---------------------
def update_my_stock(user_name, stockNumber, condition, target_price):
    db=constructor_stock()
    collect = db[user_name]
    # 條件變了就重置 notified，讓下次達標時還能發新通知
    collect.update_many(
        {"favorite_stock": stockNumber},
        {'$set': {'condition':condition, "price":target_price, "notified": False}}
    )
    content = f"股票{stockNumber}更新成功"
    return content

def update_stock_notified(user_name, stockNumber, notified):
    """更新某筆關注股票的 notified 旗標（cron 用：達標通知後標記，鬆開時清除）"""
    db = constructor_stock()
    collect = db[user_name]
    collect.update_many({"favorite_stock": stockNumber}, {'$set': {'notified': bool(notified)}})
# --------------------- 秀出使用者的股票條件 ---------------------
def show_stock_setting(user_name, userID):
    db = constructor_stock()
    collect = db[user_name]
    dataList = list(collect.find({"userID": userID}))
    if dataList == []: return "您的股票清單為空，請透過指令新增股票至清單中"
    content = "您清單中的選股條件為: \n"
    for i in range(len(dataList)):
        content += f'{dataList[i]["favorite_stock"]}{dataList[i]["condition"]}{dataList[i]["price"]}\n'
        #line_bot_api.push_message(TextSendMessage("#",dataList[i]))
    return content
# --------------------- 刪除使用者特定的股票 ---------------------
def delete_my_stock(user_name, stockNumber):
    db = constructor_stock()
    collect = db[user_name]
    collect.delete_one({'favorite_stock': stockNumber})
    return stockNumber + "刪除成功"
# --------------------- 刪除使用者清單內所有的股票 ---------------------
def delete_my_allstock(user_name, userID):
    db = constructor_stock()
    collect = db[user_name]
    collect.delete_many({'userID': userID})
    return "全部股票刪除成功"
#----------------------------  更新匯率清單的匯率  --------------------------
def update_my_currency(user_name, currency, condition , target_price):
    db=constructor_currency()
    collect = db[user_name]
    # 條件變了就重置 notified，讓下次達標時還能發新通知
    collect.update_many(
        {"favorite_currency": currency },
        {'$set': {'condition':condition , "price": target_price, "notified": False}}
    )
    return f"{currency_list[currency]}更新成功"
#----------------------------  新增匯率至雍率清單  --------------------------
def write_my_currency(userID, user_name, currency, condition, target_price):
    db = constructor_currency()
    collect = db[user_name]
    is_exit = collect.find_one({"favorite_currency": currency})
    if is_exit != None : return update_my_currency(user_name, currency,condition, target_price)
    # 新增前檢查上限
    current_count = collect.count_documents({"tag": "currency"})
    if current_count >= MAX_CURRENCIES_PER_USER:
        return f"❌ 已達上限：每人最多關注 {MAX_CURRENCIES_PER_USER} 個外幣，請先用「我的外幣」刪除不需要的再新增"
    collect.insert_one({
            "userID": userID,
            "favorite_currency": currency,
            "condition": condition,
            "price": target_price,
            "tag": "currency",
            "notified": False,
            "date_info": datetime.datetime.now()
        })
    return f"{currency_list[currency]}已新增至您的外幣清單"

def update_currency_notified(user_name, currency, notified):
    """更新某筆關注外幣的 notified 旗標（cron 用：達標通知後標記，鬆開時清除）"""
    db = constructor_currency()
    collect = db[user_name]
    collect.update_many({"favorite_currency": currency}, {'$set': {'notified': bool(notified)}})
#----------------------------  查詢資料庫中匯率清單的匯率(文字)  --------------------------
def show_my_currency(userID, user_name):
    db = constructor_currency()
    collect = db[user_name]
    dataList = list(collect.find({"userID": userID}))
    if dataList == []: return "您的外幣清單為空，請透過指令新增外幣至清單中"
    content = ""
    for i in range(len(dataList)):
        content += EXRate.showCurrency(dataList[i]["favorite_currency"])
    return content
#----------------------------  刪除使用者清單特定的匯率  --------------------------
def delete_my_currency(user_name, currency):
    db = constructor_currency()
    collect = db[user_name]
    collect.delete_one({'favorite_currency': currency})
    return currency_list[currency] +"刪除成功"

#----------------------------  除匯率清單全部匯率  --------------------------
def delete_my_allcurrency(user_name, userID):
    db = constructor_currency()
    collect = db[user_name]
    collect.delete_many({'userID': userID})
    return "外幣清單已清空"