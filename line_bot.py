import os
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent,TextMessage, TextSendMessage, StickerSendMessage, FollowEvent,
     TemplateSendMessage, CarouselTemplate, CarouselColumn, URIAction)

#Channel access token (從環境變數讀取)
line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN', ''))
#Channel secret
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET', ''))