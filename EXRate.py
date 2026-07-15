import twder
import pandas as pd
import requests
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import Imgur
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

from matplotlib.font_manager import FontProperties # 設定字體
chinese_font = matplotlib.font_manager.FontProperties(fname='msjh.ttf') # 引入同個資料夾下支援中文字檔

def getCurrencyName(currency):
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
        "THB" : "泰幣", 
        "PHP" : "菲國比索", 
        "IDR" : "印尼幣", 
        "KRW" : "韓元",   
        "MYR" : "馬來幣", 
        "VND" : "越南盾", 
        "CNY" : "人民幣",
      }
    try: currency_name = currency_list[currency]
    except: return "無可支援的外幣"
    return currency_name
def now_rate(code):
    """回 (1 code = ? 台幣 的匯率 float, 更新時間str) 或 (None, None)。
    來源 open.er-api.com(免金鑰、中價)。取代已被臺銀反爬蟲擋掉的 twder。"""
    try:
        r = requests.get(f"https://open.er-api.com/v6/latest/{code}", timeout=10).json()
        rates = r.get("rates") or {}
        if r.get("result") == "success" and "TWD" in rates:
            return float(rates["TWD"]), (r.get("time_last_update_utc") or "")[:16]
    except Exception:
        pass
    return None, None


# 查詢匯率
def showCurrency(code) -> "JPY": # code 為外幣代碼
    # 註：原本用 twder 抓臺灣銀行牌告，臺銀已加反爬蟲(回傳挑戰頁)導致 twder 解析失敗；
    #     改用 open.er-api.com 免金鑰參考匯率(中價)，穩定不被擋。實際交易仍以銀行牌告為準。
    currency_name = getCurrencyName(code)
    if currency_name == "無可支援的外幣": return "無可支援的外幣"
    try:
        r = requests.get(f"https://open.er-api.com/v6/latest/{code}", timeout=10).json()
        rates = r.get("rates") or {}
        if r.get("result") != "success" or "TWD" not in rates:
            return f"{currency_name}（{code}）匯率暫時查不到，請稍後再試 🙏"
        twd = float(rates["TWD"])
        upd = (r.get("time_last_update_utc") or "")[:16]
        inv = (1.0 / twd) if twd else 0.0
        return (
            f"{currency_name}（{code}）參考匯率\n"
            f" ---------- \n"
            f" 1 {code} ≈ {twd:.4g} 台幣\n"
            f" 1 台幣 ≈ {inv:.4g} {code}\n"
            f" 更新時間: {upd}\n"
            f"（此為中價參考，實際買賣以各銀行牌告為準）\n \n"
        )
    except Exception:
        return f"{currency_name}（{code}）匯率查詢失敗，請稍後再試 🙏"

def getExchangeRate(msg): # 不同貨幣直接換算(非只限於台幣)
    """
    sample
    code = '換匯USD/TWD/100;
    code = '換匯USD/JPY/100'
    """
    currency_list = msg[2:].split("/")
    currency = currency_list[0] # 輸入想查詢的匯率
    currency1 = currency_list[1] # 輸入想兌換的匯率
    money_value = currency_list[2] # 輸入金額數值
    url_coinbase = 'https://api.coinbase.com/v2/exchange-rates?currency=' + currency
    res = requests.get(url_coinbase)
    jData = res.json()
    pd_currency = jData['data']['rates']
    content = f'目前的兌換率為:{pd_currency[currency1]} {currency1} \n查詢的金額為: '
    amount =  float(pd_currency[currency1]) 
    content += str('%.2f' % (amount * float(money_value))) + " " +currency1
    return content
#  現金匯率
def cash_exrate_sixMonth(code1) -> "USA":
    currency_name = getCurrencyName(code1)# 取得對應的貨幣名稱
    if currency_name == "無可支援的外幣": return "無可支援的外幣"
    dfs = pd.read_html(f'https://rate.bot.com.tw/xrt/quote/l6m/{code1}')
    currency = dfs[0].iloc[:, 0:6]
    # 更改欄位名稱
    currency.columns = [u'Date', u'Currency', u'現金買入', u'現金賣出', u'即期買入',  u'即期賣出']
    currency[u'Currency'] = currency[u'Currency'].str.extract('\((\w+)\)')
    currency = currency.iloc[::-1] #  row 順序反轉，因原始資料是從最新開始排
    if currency["現金買入"][0] == "-" or currency["現金買入"][0]== 0.0:
        return "現金匯率無資料可分析"
    import uuid
    fname = f"{code1}_cash_{uuid.uuid4().hex[:8]}"
    currency.plot(kind = 'line', figsize=(12, 6), x='Date', y=[u'現金買入', u'現金賣出'])
    plt.legend(prop=chinese_font) # 支援中文字
    plt.title(currency_name + " 現金匯率",  fontsize=20, fontproperties=chinese_font)
    plt.savefig(f"{fname}.png")
    plt.close()
    return Imgur.showImgur(fname)

##--------------------------------------------
#######     走勢圖
#   即期匯率
def spot_exrate_sixMonth(code2):
    currency_name = getCurrencyName(code2)# 取得對應的貨幣名稱
    if currency_name == "無可支援的外幣": return "無可支援的外幣"
    dfs = pd.read_html(f'https://rate.bot.com.tw/xrt/quote/l6m/{code2}')
    currency = dfs[0].iloc[:, 0:6] # 獲取前6個欄位
    # 更改欄位名稱
    currency.columns = [u'Date', u'Currency', u'現金買入', u'現金賣出', u'即期買入',  u'即期賣出']
    currency[u'Currency'] = currency[u'Currency'].str.extract('\((\w+)\)')
    currency = currency.iloc[::-1] #  row 順序反轉，因原始資料是從最新開始排
    if currency["即期買入"][0] == "-" or currency["即期買入"][0] == 0.0:
        return "即期匯率無資料可分析"
    import uuid
    fname = f"{code2}_spot_{uuid.uuid4().hex[:8]}"
    currency.plot(kind = 'line', figsize=(12, 6),x='Date', y=[u'即期買入', u'即期賣出'])
    plt.legend(prop=chinese_font) # 支援中文字
    plt.title(f"{currency_name} 即期匯率",  fontsize=20, fontproperties=chinese_font)
    plt.savefig(f"{fname}.png")
    plt.close()
    return Imgur.showImgur(fname)
