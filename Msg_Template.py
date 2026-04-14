
from linebot.models import *
def stock_reply_rate():
    content_text = "想知道匯率？"
    text_message = TextSendMessage(
                                 text = content_text ,
                               quick_reply=QuickReply(
                                   items=[
                                       QuickReplyButton(
                                                action=MessageAction(
                                                    label="💜💜查詢單一幣別匯率", 
                                                    text="幣別種類",
                                                )
                                       ),
                                       QuickReplyButton(
                                                action=MessageAction(
                                                    label="💜💜匯率兌換",
                                                    text="匯率兌換",
                                                )
                                       ),
                                       QuickReplyButton(
                                                action=MessageAction(
                                                    label="💜💜關注的匯率", 
                                                    text="我的外幣",
                                                )
                                       ),
                                   ]           
                                ))
    return text_message
def stock_reply_trend():
    content_text = "分析趨勢"
    text_message = TextSendMessage(
                                 text = content_text ,
                               quick_reply=QuickReply(
                                   items=[
                                       QuickReplyButton(
                                                action=MessageAction(
                                                    label="💜即時股價💜",
                                                    text="股價查詢",
                                                )
                                       ),
                                       QuickReplyButton(
                                                action=MessageAction(
                                                    label="💜匯率走勢圖💜",
                                                    text="CTUSD",
                                                )
                                       ),
                                       QuickReplyButton(
                                                action=MessageAction(
                                                    label="💜K線圖(台積電)💜",
                                                    text="@K2330 1y",
                                                )
                                       ),
                                   ]           
                                ))
    return text_message
# #測試的BUTTON
# def test_Button():
#     flex_message = FlexSendMessage(
#             alt_text="Test",
#             contents={
# 幣別種類Button
def show_Button():
    flex_message = FlexSendMessage(
            alt_text="幣別種類",
            contents={
                "type": "bubble",
                "hero": {
                    "type": "image",
                    "url": "https://i.imgur.com/HFD1Kuv.png",
                    "size": "full",
                    "aspectRatio": "20:13",
                    "aspectMode": "cover",
                    "action": {
                    "type": "uri",
                    "uri": "https://line.me/"
                    }
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                    {
                        "type": "text",
                        "text": "幣別種類",
                        "weight": "bold",
                        "style": "normal",
                        "align": "center",
                        "size": "xl"
                    }
                    ]
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                        {
                            "type": "button",
                            "action": {
                            "type": "message",
                            "label": "美金",
                            "text": "外幣USD"
                            },
                            "style": "secondary",
                            "color": "#ffed00",
                            "margin": "none"
                        },
                        {
                            "type": "button",
                            "action": {
                            "type": "message",
                            "label": "日圓",
                            "text": "外幣JPY"
                            },
                            "style": "secondary",
                            "color": "#ff828f",
                            "margin": "md",
                            "height": "md"
                        },
                        {
                            "type": "button",
                            "action": {
                            "type": "message",
                            "label": "港幣",
                            "text": "外幣HKD"
                            },
                            "style": "secondary",
                            "color": "#66ffe6"
                        },
                        {
                            "type": "separator",
                            "margin": "none"
                        }
                        ],
                        "backgroundColor": "#dcffff",
                        "spacing": "md",
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                        {
                            "type": "button",
                            "action": {
                            "type": "message",
                            "label": "英鎊",
                            "text": "外幣GBP"
                            },
                            "style": "secondary",
                            "color": "#ffed00",
                            "margin": "none"
                        },
                        {
                            "type": "button",
                            "action": {
                            "type": "message",
                            "label": "澳幣",
                            "text": "外幣AUD"
                            },
                            "style": "secondary",
                            "color": "#ff828f",
                            "margin": "md",
                            "height": "md"
                        },
                        {
                            "type": "button",
                            "action": {
                            "type": "message",
                            "label": "加拿大幣",
                            "text": "外幣CAD"
                            },
                            "style": "secondary",
                            "color": "#66ffe6"
                        },
                        {
                            "type": "separator",
                            "margin": "none"
                        }
                        ],
                        "backgroundColor": "#dcffff",
                        "spacing": "md",
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                        {
                            "type": "button",
                            "action": {
                            "type": "message",
                            "label": "瑞士幣",
                            "text": "外幣CHF"
                            },
                            "style": "secondary",
                            "color": "#ffed00",
                            "margin": "none"
                        },
                        {
                            "type": "button",
                            "action": {
                            "type": "message",
                            "label": "新加坡幣",
                            "text": "外幣SGD"
                            },
                            "style": "secondary",
                            "color": "#ff828f",
                            "margin": "md",
                            "height": "md"
                        },
                        {
                            "type": "button",
                            "action": {
                            "type": "message",
                            "label": "南非幣",
                            "text": "外幣ZAR"
                            },
                            "style": "secondary",
                            "color": "#66ffe6"
                        },
                        {
                            "type": "separator",
                            "margin": "none"
                        }
                        ],
                        "backgroundColor": "#dcffff",
                        "spacing": "md",
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                        {
                            "type": "button",
                            "action": {
                            "type": "message",
                            "label": "瑞典幣",
                            "text": "外幣SEK"
                            },
                            "style": "secondary",
                            "color": "#ffed00",
                            "margin": "none"
                        },
                        {
                            "type": "button",
                            "action": {
                            "type": "message",
                            "label": "泰幣",
                            "text": "外幣THB"
                            },
                            "style": "secondary",
                            "color": "#ff828f",
                            "margin": "md",
                            "height": "md"
                        },
                        {
                            "type": "button",
                            "action": {
                            "type": "message",
                            "label": "菲比索",
                            "text": "外幣PHP"
                            },
                            "style": "secondary",
                            "color": "#66ffe6"
                        },
                        {
                            "type": "separator",
                            "margin": "none"
                        }
                        ],
                        "backgroundColor": "#dcffff",
                        "spacing": "md",
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                        {
                            "type": "button",
                            "action": {
                            "type": "message",
                            "label": "印尼幣",
                            "text": "外幣IDR"
                            },
                            "style": "secondary",
                            "color": "#ffed00",
                            "margin": "none"
                        },
                        {
                            "type": "button",
                            "action": {
                            "type": "message",
                            "label": "韓元",
                            "text": "外幣KRW"
                            },
                            "style": "secondary",
                            "color": "#ff828f",
                            "margin": "md",
                            "height": "md"
                        },
                        {
                            "type": "button",
                            "action": {
                            "type": "message",
                            "label": "馬來幣",
                            "text": "外幣MYR"
                            },
                            "style": "secondary",
                            "color": "#66ffe6"
                        },
                        {
                            "type": "separator",
                            "margin": "none"
                        }
                        ],
                        "backgroundColor": "#dcffff",
                        "spacing": "md",
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                        {
                            "type": "button",
                            "action": {
                            "type": "message",
                            "label": "越南盾",
                            "text": "外幣VND"
                            },
                            "style": "secondary",
                            "color": "#ffed00",
                            "margin": "none"
                        },
                        {
                            "type": "button",
                            "action": {
                            "type": "message",
                            "label": "人民幣",
                            "text": "外幣CNY"
                            },
                            "style": "secondary",
                            "color": "#ff828f",
                            "margin": "md",
                            "height": "md"
                        },
                        {
                            "type": "button",
                            "action": {
                            "type": "message",
                            "label": "紐元",
                            "text": "外幣NZD"
                            },
                            "style": "secondary",
                            "color": "#66ffe6"
                        },
                        {
                            "type": "separator",
                            "margin": "none"
                        }
                        ],
                        "backgroundColor": "#dcffff",
                        "spacing": "md",
                        "margin": "md"
                    }
                    ],
                    "spacing": "sm"
                }
                }                                  
    )
    return flex_message
# # 幣別種類Button
# def show_Button():
#     flex_message = FlexSendMessage(
#             alt_text="幣別種類",
#             contents={
#                 "type": "bubble",
#                 "body": {
#                     "type": "box",
#                     "layout": "vertical",
#                     "contents": [
#                     {
#                         "type": "text",
#                         "text": "幣別種類",
#                         "weight": "bold",
#                         "size": "xl",
#                         "color": "#AA2B1D"
#                     }
#                     ]
#                 },
#                 "footer": {
#                     "type": "box",
#                     "layout": "vertical",
#                     "contents": [
#                     {
#                         "type": "box",
#                         "layout": "horizontal",
#                         "contents": [
#                         {
#                             "type": "button",
#                             "action": {
#                             "type": "message",
#                             "label": "美金",
#                             "text": "外幣USD"
#                             },
#                             "gravity": "center",
#                             "style": "primary",
#                             "color": "#CC561E",
#                             "margin": "sm"
#                         },
#                         {
#                             "type": "button",
#                             "action": {
#                             "type": "message",
#                             "label": "日圓",
#                             "text": "外幣JPY"
#                             },
#                             "gravity": "center",
#                             "style": "primary",
#                             "color": "#CC561E",
#                             "margin": "sm"
#                         },
#                         {
#                             "type": "button",
#                             "action": {
#                             "type": "message",
#                             "label": "港幣",
#                             "text": "外幣HKD"
#                             },
#                             "gravity": "center",
#                             "style": "primary",
#                             "color": "#CC561E",
#                             "margin": "sm"
#                         }
#                         ]
#                     },
#                     {
#                         "type": "separator",
#                         "margin": "md"
#                     },
#                     {
#                         "type": "box",
#                         "layout": "horizontal",
#                         "contents": [
#                         {
#                             "type": "button",
#                             "action": {
#                             "type": "message",
#                             "label": "英鎊",
#                             "text": "外幣GBP"
#                             },
#                             "gravity": "center",
#                             "style": "primary",
#                             "color": "#CC561E",
#                             "margin": "sm"
#                         },
#                         {
#                             "type": "button",
#                             "action": {
#                             "type": "message",
#                             "label": "澳幣",
#                             "text": "外幣AUD"
#                             },
#                             "gravity": "center",
#                             "style": "primary",
#                             "color": "#CC561E",
#                             "margin": "sm"
#                         },
#                         {
#                             "type": "button",
#                             "action": {
#                             "type": "message",
#                             "label": "加拿大幣",
#                             "text": "外幣CAD"
#                             },
#                             "gravity": "center",
#                             "style": "primary",
#                             "color": "#CC561E",
#                             "margin": "sm"
#                         }
#                         ]
#                     },
#                     {
#                         "type": "separator",
#                         "margin": "md"
#                     },
#                     {
#                         "type": "box",
#                         "layout": "horizontal",
#                         "contents": [
#                         {
#                             "type": "button",
#                             "action": {
#                             "type": "message",
#                             "label": "瑞士法郎",
#                             "text": "外幣CHF"
#                             },
#                             "gravity": "center",
#                             "style": "primary",
#                             "color": "#CC561E",
#                             "margin": "sm"
#                         },
#                         {
#                             "type": "button",
#                             "action": {
#                             "type": "message",
#                             "label": "新加坡",
#                             "text": "外幣SGD"
#                             },
#                             "gravity": "center",
#                             "style": "primary",
#                             "color": "#CC561E",
#                             "margin": "sm"
#                         },
#                         {
#                             "type": "button",
#                             "action": {
#                             "type": "message",
#                             "label": "南非幣",
#                             "text": "外幣ZAR"
#                             },
#                             "gravity": "center",
#                             "style": "primary",
#                             "color": "#CC561E",
#                             "margin": "sm"
#                         }
#                         ]
#                     },
#                     {
#                         "type": "separator",
#                         "margin": "md"
#                     },
#                     {
#                         "type": "box",
#                         "layout": "horizontal",
#                         "contents": [
#                         {
#                             "type": "button",
#                             "action": {
#                             "type": "message",
#                             "label": "瑞典幣",
#                             "text": "外幣SEK"
#                             },
#                             "gravity": "center",
#                             "style": "primary",
#                             "color": "#CC561E",
#                             "margin": "sm"
#                         },
#                         {
#                             "type": "button",
#                             "action": {
#                             "type": "message",
#                             "label": "泰幣",
#                             "text": "外幣THB"
#                             },
#                             "gravity": "center",
#                             "style": "primary",
#                             "color": "#CC561E",
#                             "margin": "sm"
#                         },
#                         {
#                             "type": "button",
#                             "action": {
#                             "type": "message",
#                             "label": "菲比索",
#                             "text": "外幣PHP"
#                             },
#                             "gravity": "center",
#                             "style": "primary",
#                             "color": "#CC561E",
#                             "margin": "sm"
#                         }
#                         ]
#                     },
#                     {
#                         "type": "separator",
#                         "margin": "md"
#                     },
#                     {
#                         "type": "box",
#                         "layout": "horizontal",
#                         "contents": [
#                         {
#                             "type": "button",
#                             "action": {
#                             "type": "message",
#                             "label": "印尼幣",
#                             "text": "外幣IDR"
#                             },
#                             "gravity": "center",
#                             "style": "primary",
#                             "color": "#CC561E",
#                             "margin": "sm"
#                         },
#                         {
#                             "type": "button",
#                             "action": {
#                             "type": "message",
#                             "label": "韓元",
#                             "text": "外幣KRW"
#                             },
#                             "gravity": "center",
#                             "style": "primary",
#                             "color": "#CC561E",
#                             "margin": "sm"
#                         },
#                         {
#                             "type": "button",
#                             "action": {
#                             "type": "message",
#                             "label": "馬來幣",
#                             "text": "外幣MYR"
#                             },
#                             "gravity": "center",
#                             "style": "primary",
#                             "color": "#CC561E",
#                             "margin": "sm"
#                         }
#                         ]
#                     },
#                     {
#                         "type": "separator",
#                         "margin": "md"
#                     },
#                     {
#                         "type": "box",
#                         "layout": "horizontal",
#                         "contents": [
#                         {
#                             "type": "button",
#                             "action": {
#                             "type": "message",
#                             "label": "越南盾",
#                             "text": "外幣VND"
#                             },
#                             "gravity": "center",
#                             "style": "primary",
#                             "color": "#CC561E",
#                             "margin": "sm"
#                         },
#                         {
#                             "type": "button",
#                             "action": {
#                             "type": "message",
#                             "label": "人民幣",
#                             "text": "外幣CNY"
#                             },
#                             "gravity": "center",
#                             "style": "primary",
#                             "color": "#CC561E",
#                             "margin": "sm"
#                         },
#                         {
#                             "type": "button",
#                             "action": {
#                             "type": "message",
#                             "label": "紐元",
#                             "text": "外幣NZD"
#                             },
#                             "gravity": "center",
#                             "style": "primary",
#                             "color": "#CC561E",
#                             "margin": "sm"
#                         }
#                         ]
#                     }
#                     ]
#                 }
#         }
                    
#     )
#     return flex_message
# 理財頻道
def youtube_channel():
    flex_message = FlexSendMessage(
            alt_text="youtube_channel",
            contents=
            {
                "type": "carousel",
                "contents": [
                    {
                    "type": "bubble",
                    "size": "micro",
                    "hero": {
                        "type": "image",
                        "url": "https://imgur.com/SJPH542.jpg",
                        "aspectMode": "fit",
                        "aspectRatio": "320:213",
                        "size": "full",
                        "backgroundColor": "#000000"
                    },
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                        {
                            "type": "text",
                            "text": "理財達人秀",
                            "weight": "bold",
                            "size": "lg",
                            "wrap": True,
                            "align": "center"
                        },
                        {
                            "type": "box",
                            "layout": "baseline",
                            "contents": [
                            {
                                "type": "icon",
                                "url": "https://scdn.line-apps.com/n/channel_devcenter/img/fx/review_gold_star_28.png"
                            },
                            {
                                "type": "text",
                                "text": "最精彩最好懂",
                                "size": "xs",
                                "color": "#8c8c8c",
                                "margin": "md",
                                "flex": 0,
                                "weight": "bold"
                            }
                            ]
                        },
                        {
                            "type": "button",
                            "style": "link",
                            "height": "sm",
                            "action": {
                            "type": "uri",
                            "label": "點我觀看",
                            "uri": "https://www.youtube.com/channel/UCQvsuaih5lE0n_Ne54nNezg"
                            }
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                {
                                    "type": "text",
                                    "text": "理財youtuber",
                                    "wrap": True,
                                    "color": "#8c8c8c",
                                    "size": "xxs",
                                    "flex": 5
                                }
                                ]
                            }
                            ]
                        }
                        ],
                        "spacing": "sm",
                        "paddingAll": "13px"
                    }
                    },
                    {
                    "type": "bubble",
                    "size": "micro",
                    "hero": {
                        "type": "image",
                        "url": "https://imgur.com/dPW0jcC.jpg",
                        "size": "full",
                        "aspectMode": "fit",
                        "aspectRatio": "320:213",
                        "backgroundColor": "#AA0000"
                    },
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                        {
                            "type": "text",
                            "text": "CMoney理財寶",
                            "weight": "bold",
                            "size": "lg",
                            "wrap": True,
                            "align": "center"
                        },
                        {
                            "type": "box",
                            "layout": "baseline",
                            "contents": [
                            {
                                "type": "icon",
                                "url": "https://scdn.line-apps.com/n/channel_devcenter/img/fx/review_gold_star_28.png"
                            },
                            {
                                "type": "text",
                                "text": "基本理財知識",
                                "size": "xs",
                                "color": "#8c8c8c",
                                "margin": "md",
                                "flex": 0,
                                "weight": "bold"
                            }
                            ]
                        },
                        {
                            "type": "button",
                            "style": "link",
                            "height": "sm",
                            "action": {
                            "type": "uri",
                            "label": "點我觀看",
                            "uri": "https://www.youtube.com/user/CMoneySchool"
                            }
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                {
                                    "type": "text",
                                    "text": "理財youtuber",
                                    "wrap": True,
                                    "color": "#8c8c8c",
                                    "size": "xxs",
                                    "flex": 5
                                }
                                ]
                            }
                            ]
                        }
                        ],
                        "spacing": "sm",
                        "paddingAll": "13px"
                    }
                    },
                    {
                    "type": "bubble",
                    "size": "micro",
                    "hero": {
                        "type": "image",
                        "url": "https://imgur.com/zkUZrCj.jpg",
                        "size": "full",
                        "aspectMode": "fit",
                        "aspectRatio": "320:213",
                        "backgroundColor": "#444444"
                    },
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                        {
                            "type": "text",
                            "text": "我要做富翁",
                            "weight": "bold",
                            "size": "lg",
                            "wrap": True,
                            "align": "center"
                        },
                        {
                            "type": "box",
                            "layout": "baseline",
                            "contents": [
                            {
                                "type": "icon",
                                "url": "https://scdn.line-apps.com/n/channel_devcenter/img/fx/review_gold_star_28.png"
                            },
                            {
                                "type": "text",
                                "text": "平民化&分享形式",
                                "size": "xs",
                                "color": "#8c8c8c",
                                "margin": "md",
                                "flex": 0,
                                "weight": "bold"
                            }
                            ]
                        },
                        {
                            "type": "button",
                            "style": "link",
                            "height": "sm",
                            "action": {
                            "type": "uri",
                            "label": "點我觀看",
                            "uri": "https://www.youtube.com/user/SyLingHim"
                            }
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                {
                                    "type": "text",
                                    "text": "理財youtuber",
                                    "wrap": True,
                                    "color": "#8c8c8c",
                                    "size": "xxs",
                                    "flex": 5
                                }
                                ]
                            }
                            ]
                        }
                        ],
                        "spacing": "sm",
                        "paddingAll": "13px"
                    }
                    }
                ]
            }
        )
    return flex_message

def realtime_currency_other(currency):
    content_text = f"還想查詢 {currency} 的其他資訊嗎？"
    text_message = TextSendMessage(
        text=content_text,
        quick_reply=QuickReply(
            items=[
                QuickReplyButton(
                    action=MessageAction(
                        label="查詢即時匯率",
                        text=f"外幣{currency}",
                    )
                ),
                QuickReplyButton(
                    action=MessageAction(
                        label="查看匯率走勢圖",
                        text=f"CT{currency}",
                    )
                ),
                QuickReplyButton(
                    action=MessageAction(
                        label="加入外幣關注",
                        text=f"新增外幣{currency}",
                    )
                ),
            ]
        )
    )
    return text_message