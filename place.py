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
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                        {
                            "type": "image",
                            "url": "https://i.imgur.com/wQcsTzT.jpg",
                            "flex": 1,
                            "action": {
                            "type": "message",
                            "label": "action",
                            "text": "雷達回波"
                            },
                            "gravity": "center",
                            "aspectMode": "cover",
                            "size": "full"
                        },
                        {
                            "type": "image",
                            "url": "https://i.imgur.com/jKqO32C.jpg",
                            "aspectMode": "cover",
                            "gravity": "center",
                            "action": {
                            "type": "message",
                            "label": "action",
                            "text": "即時天氣"
                            },
                            "size": "full"
                        }
                        ],
                        "paddingAll": "0px"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                        {
                            "type": "image",
                            "url": "https://i.imgur.com/KCCL1B2.jpg",
                            "aspectMode": "cover",
                            "gravity": "center",
                            "action": {
                            "type": "message",
                            "label": "action",
                            "text": "即時天氣"
                            },
                            "size": "full"
                        },
                        {
                            "type": "image",
                            "url": "https://i.imgur.com/Iwmkr0V.jpg",
                            "size": "full",
                            "aspectMode": "cover",
                            "aspectRatio": "150:150",
                            "gravity": "center",
                            "action": {
                            "type": "message",
                            "label": "action",
                            "text": "天氣預報"
                            }
                        }
                        ],
                        "flex": 1,
                        "paddingAll": "0px"
                    }
                    ],
                    "paddingAll": "0px"
                }
                ],
                "paddingAll": "0px"
            }
        }
    )
    return flex_message

###############################1+2.quick_reply#########################
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