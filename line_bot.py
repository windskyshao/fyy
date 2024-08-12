from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent,TextMessage, TextSendMessage, StickerSendMessage, FollowEvent,
     TemplateSendMessage, CarouselTemplate, CarouselColumn, URIAction)

#Channel access token
line_bot_api = LineBotApi('tgQqCqIxEiMiA2KuMIUF/AgRvhFW1x/ncypXaVt1S5BMEeDFSpfqxGAJ3o13ywqsBaOLBcXr0EwFIplg7RUuxnpphqdm2XqOw9zOrK1tTLwaX7nQ272+jsvuRRXuNVJgkPe6ehImSXAXNlf30aiq2QdB04t89/1O/w1cDnyilFU=')
#Channel secret
handler = WebhookHandler('473cddb51f8ae4d839bddd98e028937e')