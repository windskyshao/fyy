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
    """顯示縣市按鈕，點擊後直接開啟中央氣象署頁面。"""
    county_cids = [
        ('基隆市', '10017'), ('台北市', '63'), ('新北市', '65'), ('桃園市', '68'),
        ('新竹市', '10018'), ('新竹縣', '10004'), ('苗栗縣', '10005'), ('台中市', '66'),
        ('彰化縣', '10007'), ('南投縣', '10008'), ('雲林縣', '10009'), ('嘉義市', '10020'),
        ('嘉義縣', '10010'), ('台南市', '67'), ('高雄市', '64'), ('屏東縣', '10013'),
        ('宜蘭縣', '10002'), ('花蓮縣', '10015'), ('臺東縣', '10014'), ('澎湖縣', '10016'),
        ('金門縣', '09020'), ('連江縣', '09007')
    ]

    if mode == 'tide':
        title = '潮汐預報'
        subtitle = '請選擇縣市（點擊後直接開啟）'
    elif mode == 'harbor':
        title = '港口天氣'
        subtitle = '請選擇縣市（點擊後直接開啟）'
    else:
        title = '即時天氣預報'
        subtitle = '請選擇縣市（點擊後直接開啟）'

    bubbles = []
    for i in range(0, len(county_cids), 11):
        chunk = county_cids[i:i+11]
        buttons = []
        for city, cid in chunk:
            uri = f'https://www.cwa.gov.tw/V8/C/W/County/County.html?CID={cid}'
            buttons.append({
                "type": "button",
                "style": "primary",
                "color": "#1E88E5",
                "height": "sm",
                "action": {
                    "type": "uri",
                    "label": city,
                    "uri": uri
                }
            })

        bubble = {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": title, "weight": "bold", "size": "lg", "align": "center", "color": "#1DB446"},
                    {"type": "text", "text": subtitle, "size": "xs", "align": "center", "color": "#888888", "margin": "sm"}
                ],
                "paddingAll": "14px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": buttons,
                "paddingAll": "12px"
            }
        }
        bubbles.append(bubble)

    return FlexSendMessage(
        alt_text=f'{title}縣市選單',
        contents={
            "type": "carousel",
            "contents": bubbles
        }
    )
