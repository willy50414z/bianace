# 引入新版 V3 的類別
import logging

from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    TextMessage
)

# 假設這是您的 config_util 模組
from com.willy.binance.config.config_util import config_util

# 初始化配置
config = config_util("linebot")
channel_access_token = config.get("token")

# --- 設定 V3 API 客戶端 ---
configuration = Configuration(access_token=channel_access_token)


# 發送訊息函數 (使用新版語法)
def send_message(user_id, message_text):
    # 創建訊息物件
    message = TextMessage(text=message_text)

    # 創建 PushMessageRequest 物件
    push_request = PushMessageRequest(
        to=user_id,
        messages=[message]  # messages 必須是一個列表
    )

    api_client = ApiClient(configuration)
    try:
        line_bot_api = MessagingApi(api_client)
        # 使用新的 push_message 方法，傳入 request 物件
        line_bot_api.push_message(push_request)
    except Exception as e:
        logging.error(f"Failed to send message", e)
    finally:
        api_client.close()


if __name__ == '__main__':
    # 使用方式
    user = config.get("userid_willy")
    send_message(user, "Hello from Python!")
