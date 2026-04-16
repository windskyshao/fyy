from linebot.models import *
#from config import  Config

#即時天氣&預報天氣用
city_list = [
    '基隆市','宜蘭縣','花蓮縣',
    '台北市','新北市','桃園市',
    '新竹市','新竹縣','苗栗縣',
    '彰化縣','雲林縣','南投縣',
    '台中市','嘉義市','嘉義縣',
    '高雄市','台南市','屏東縣',
    '彭湖縣','金門縣','臺東縣',
    '連江縣']



####################縣市選單(即時、預報)####################
# 全台縣市選單(22個)-即時天氣+預報天氣
def select_city(mat):
    if mat=='即時天氣':
        message_1='請問要查詢'
        message_2='的那個地區'
    elif mat=='天氣預報':
        message_1='我要查詢'
        message_2='的預報天氣'
    flex_message = FlexSendMessage(
        alt_text="請選擇想查詢的縣市：",
        contents={
            "type": "bubble",
            "size": "mega",
            "hero": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                {
                    "type": "text",
                    "text": "全台縣市選單",
                    "color": "#4493A3",
                    "margin": "md",
                    "size": "xl",
                    "weight": "bold",
                    "wrap": True,
                    "adjustMode": "shrink-to-fit",
                    "offsetStart": "25px"
                }
                ],
                "paddingAll": "0px"
            },
            "body": {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                    {
                        "type": "button",
                        "adjustMode": "shrink-to-fit",
                        "color": "#7EB5A6",
                        "style": "primary",
                        "margin": "sm",
                        "height": "sm",
                        "action": {
                        "type": "message",
                        "label": city_list[0],
                        "text": message_1+city_list[0]+message_2
                        }
                    },
                    {
                        "type": "button",
                        "adjustMode": "shrink-to-fit",
                        "color": "#7EB5A6",
                        "style": "primary",
                        "margin": "sm",
                        "height": "sm",
                        "action": {
                        "type": "message",
                        "label": city_list[3],
                        "text": message_1+city_list[3]+message_2
                        }
                    },
                    {
                        "type": "button",
                        "adjustMode": "shrink-to-fit",
                        "color": "#7EB5A6",
                        "style": "primary",
                        "margin": "sm",
                        "height": "sm",
                        "action": {
                        "type": "message",
                        "label": city_list[6],
                        "text": message_1+city_list[6]+message_2
                        }
                    },
                    {
                        "type": "button",
                        "adjustMode": "shrink-to-fit",
                        "color": "#7EB5A6",
                        "style": "primary",
                        "margin": "sm",
                        "height": "sm",
                        "action": {
                        "type": "message",
                        "label": city_list[9],
                        "text": message_1+city_list[9]+message_2
                        }
                    },
                    {
                        "type": "button",
                        "adjustMode": "shrink-to-fit",
                        "color": "#7EB5A6",
                        "style": "primary",
                        "margin": "sm",
                        "height": "sm",
                        "action": {
                        "type": "message",
                        "label": city_list[12],
                        "text": message_1+city_list[12]+message_2
                        }
                    },
                    {
                        "type": "button",
                        "adjustMode": "shrink-to-fit",
                        "color": "#7EB5A6",
                        "style": "primary",
                        "margin": "sm",
                        "height": "sm",
                        "action": {
                        "type": "message",
                        "label": city_list[15],
                        "text": message_1+city_list[15]+message_2
                        }
                    },
                    {
                        "type": "button",
                        "adjustMode": "shrink-to-fit",
                        "color": "#7EB5A6",
                        "style": "primary",
                        "margin": "sm",
                        "height": "sm",
                        "action": {
                        "type": "message",
                        "label": city_list[18],
                        "text": message_1+city_list[18]+message_2
                        }
                    },
                    {
                        "type": "button",
                        "adjustMode": "shrink-to-fit",
                        "color": "#7EB5A6",
                        "style": "primary",
                        "margin": "sm",
                        "height": "sm",
                        "action": {
                        "type": "message",
                        "label": city_list[21],
                        "text": message_1+city_list[21]+message_2
                        }
                    }
                    ]
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "md",
                    "contents": [
                    {
                        "type": "button",
                        "adjustMode": "shrink-to-fit",
                        "color": "#7EB5A6",
                        "style": "primary",
                        "margin": "sm",
                        "height": "sm",
                        "action": {
                        "type": "message",
                        "label": city_list[1],
                        "text": message_1+city_list[1]+message_2
                        }
                    },
                    {
                        "type": "button",
                        "adjustMode": "shrink-to-fit",
                        "color": "#7EB5A6",
                        "style": "primary",
                        "margin": "sm",
                        "height": "sm",
                        "action": {
                        "type": "message",
                        "label": city_list[4],
                        "text": message_1+city_list[4]+message_2
                        }
                    },
                    {
                        "type": "button",
                        "adjustMode": "shrink-to-fit",
                        "color": "#7EB5A6",
                        "style": "primary",
                        "margin": "sm",
                        "height": "sm",
                        "action": {
                        "type": "message",
                        "label": city_list[7],
                        "text": message_1+city_list[7]+message_2
                        }
                    },
                    {
                        "type": "button",
                        "adjustMode": "shrink-to-fit",
                        "color": "#7EB5A6",
                        "style": "primary",
                        "margin": "sm",
                        "height": "sm",
                        "action": {
                        "type": "message",
                        "label": city_list[10],
                        "text": message_1+city_list[10]+message_2
                        }
                    },
                    {
                        "type": "button",
                        "adjustMode": "shrink-to-fit",
                        "color": "#7EB5A6",
                        "style": "primary",
                        "margin": "sm",
                        "height": "sm",
                        "action": {
                        "type": "message",
                        "label": city_list[13],
                        "text": message_1+city_list[13]+message_2
                        }
                    },
                    {
                        "type": "button",
                        "adjustMode": "shrink-to-fit",
                        "color": "#7EB5A6",
                        "style": "primary",
                        "margin": "sm",
                        "height": "sm",
                        "action": {
                        "type": "message",
                        "label": city_list[16],
                        "text": message_1+city_list[16]+message_2
                        }
                    },
                    {
                        "type": "button",
                        "adjustMode": "shrink-to-fit",
                        "color": "#7EB5A6",
                        "style": "primary",
                        "margin": "sm",
                        "height": "sm",
                        "action": {
                        "type": "message",
                        "label": city_list[19],
                        "text": message_1+city_list[19]+message_2
                        }
                    }
                    ]
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "md",
                    "contents": [
                    {
                        "type": "button",
                        "adjustMode": "shrink-to-fit",
                        "color": "#7EB5A6",
                        "style": "primary",
                        "margin": "sm",
                        "height": "sm",
                        "action": {
                        "type": "message",
                        "label": city_list[2],
                        "text": message_1+city_list[2]+message_2
                        }
                    },
                    {
                        "type": "button",
                        "adjustMode": "shrink-to-fit",
                        "color": "#7EB5A6",
                        "style": "primary",
                        "margin": "sm",
                        "height": "sm",
                        "action": {
                        "type": "message",
                        "label": city_list[5],
                        "text": message_1+city_list[5]+message_2
                        }
                    },
                    {
                        "type": "button",
                        "adjustMode": "shrink-to-fit",
                        "color": "#7EB5A6",
                        "style": "primary",
                        "margin": "sm",
                        "height": "sm",
                        "action": {
                        "type": "message",
                        "label": city_list[8],
                        "text": message_1+city_list[8]+message_2
                        }
                    },
                    {
                        "type": "button",
                        "adjustMode": "shrink-to-fit",
                        "color": "#7EB5A6",
                        "style": "primary",
                        "margin": "sm",
                        "height": "sm",
                        "action": {
                        "type": "message",
                        "label": city_list[11],
                        "text": message_1+city_list[11]+message_2
                        }
                    },
                    {
                        "type": "button",
                        "adjustMode": "shrink-to-fit",
                        "color": "#7EB5A6",
                        "style": "primary",
                        "margin": "sm",
                        "height": "sm",
                        "action": {
                        "type": "message",
                        "label": city_list[14],
                        "text": message_1+city_list[14]+message_2
                        }
                    },
                    {
                        "type": "button",
                        "adjustMode": "shrink-to-fit",
                        "color": "#7EB5A6",
                        "style": "primary",
                        "margin": "sm",
                        "height": "sm",
                        "action": {
                        "type": "message",
                        "label": city_list[17],
                        "text": message_1+city_list[17]+message_2
                        }
                    },
                    {
                        "type": "button",
                        "adjustMode": "shrink-to-fit",
                        "color": "#7EB5A6",
                        "style": "primary",
                        "margin": "sm",
                        "height": "sm",
                        "action": {
                        "type": "message",
                        "label": city_list[20],
                        "text": message_1+city_list[20]+message_2
                        }
                    }
                    ]
                }
                ],
                "paddingAll": "8px"
            }
        }
    )
    return flex_message

#######################最新氣象-圖片轉盤#######################
# 第一層-圖文選單->最新氣象->4格圖片
def img_Carousel():
    flex_message = FlexSendMessage(
        alt_text="請選擇查詢事項：",
        contents={
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "最新氣象功能",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#1DB446",
                        "align": "center"
                    },
                    {
                        "type": "text",
                        "text": "請直接點選功能",
                        "size": "xs",
                        "color": "#888888",
                        "align": "center",
                        "margin": "sm"
                    }
                ],
                "paddingAll": "16px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#00ACC1",
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": "即時天氣預報",
                            "text": "即時天氣預報"
                        }
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#2196F3",
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": "雷達回波",
                            "text": "雷達回波"
                        }
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#FB8C00",
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": "潮汐預報",
                            "text": "潮汐預報"
                        }
                    },
                    {
                        "type": "button",
                        "style": "link",
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": "港口天氣",
                            "text": "港口天氣"
                        }
                    }
                ],
                "paddingAll": "12px"
            }
        }
    )
    return flex_message
def quick_reply_weather(mat):
    content_text = '請選擇您要查詢的天氣：'
    text_message = TextSendMessage(
        text = content_text ,
        quick_reply=QuickReply(
            items=[
                QuickReplyButton(
                    action=MessageAction(
                        label="查詢其它天氣",
                        text="其它"+mat,
                    )
                ),
                QuickReplyButton(
                    action=LocationAction(
                        label="回傳地址查詢",                        
                    )
                )
            ]
        )
    )
    return text_message




def select_city_direct_links(mode='weather'):
    """顯示縣市按鈕（3欄漂亮格子），點擊後直接開啟中央氣象署頁面。"""
    # 按地理位置排列，每行3個
    county_rows = [
        [('基隆市', '10017'), ('宜蘭縣', '10002'), ('花蓮縣', '10015')],
        [('台北市', '63'),    ('新北市', '65'),    ('桃園市', '68')],
        [('新竹市', '10018'), ('新竹縣', '10004'), ('苗栗縣', '10005')],
        [('彰化縣', '10007'), ('雲林縣', '10009'), ('南投縣', '10008')],
        [('台中市', '66'),    ('嘉義市', '10020'), ('嘉義縣', '10010')],
        [('高雄市', '64'),    ('台南市', '67'),    ('屏東縣', '10013')],
        [('澎湖縣', '10016'), ('金門縣', '09020'), ('臺東縣', '10014')],
        [('連江縣', '09007')],
    ]
    # 每行不同顏色，漸層效果
    row_colors = ['#00ACC1', '#0097A7', '#00897B', '#43A047', '#558B2F', '#E65100', '#D84315', '#6D4C41']

    if mode == 'tide':
        title = '🌊 潮汐預報'
    elif mode == 'harbor':
        title = '⚓ 港口天氣'
    else:
        title = '🌤 全台縣市選單'

    base_url = 'https://www.cwa.gov.tw/V8/C/W/County/County.html?CID='

    body_rows = []
    for r, row in enumerate(county_rows):
        color = row_colors[r % len(row_colors)]
        row_btns = []
        for city, cid in row:
            row_btns.append({
                "type": "button",
                "adjustMode": "shrink-to-fit",
                "color": color,
                "style": "primary",
                "margin": "sm",
                "height": "sm",
                "action": {"type": "uri", "label": city, "uri": f"{base_url}{cid}"}
            })
        # 補齊不足3個的行
        while len(row_btns) < 3:
            row_btns.append({"type": "filler"})
        body_rows.append({
            "type": "box", "layout": "horizontal", "spacing": "sm", "margin": "sm",
            "contents": row_btns
        })

    flex_message = FlexSendMessage(
        alt_text=f'{title}',
        contents={
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box", "layout": "vertical",
                "contents": [
                    {"type": "text", "text": title, "weight": "bold", "size": "xl", "color": "#00695C", "align": "center"},
                    {"type": "text", "text": "點擊縣市直接開啟氣象署查詢", "size": "xs", "color": "#888888", "align": "center", "margin": "sm"}
                ], "paddingAll": "14px"
            },
            "body": {
                "type": "box", "layout": "vertical",
                "contents": body_rows,
                "paddingAll": "8px"
            }
        }
    )
    return flex_message
