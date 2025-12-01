from linebot import LineBotApi
from linebot.models import TextSendMessage

from com.willy.binance.config.config_util import config_util

# 初始化
config = config_util("linebot")
line_bot_api = LineBotApi(config.get("token"))


# 發送訊息
def send_message(user_id, message):
    line_bot_api.push_message(
        user_id,
        TextSendMessage(text=message)
    )


if __name__ == '__main__':
    # 使用方式
    user_id = config.get("userid_willy")
    send_message(user_id, "Hello from Python!")
