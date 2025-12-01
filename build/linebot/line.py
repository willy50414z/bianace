import json
import os
import hashlib
import hmac
import base64
from linebot import LineBotApi, WebhookParser
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError

# 從環境變數取得
CHANNEL_ACCESS_TOKEN = os.environ['CHANNEL_ACCESS_TOKEN']
CHANNEL_SECRET = os.environ['CHANNEL_SECRET']

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(CHANNEL_SECRET)


def lambda_handler(event, context):
    """AWS Lambda 主要處理函數"""
    
    # 取得 signature 和 body
    signature = event['headers'].get('X-Line-Signature') or event['headers'].get('x-line-signature')
    body = event['body']
    
    # 驗證 signature
    if not verify_signature(body, signature):
        return {
            'statusCode': 403,
            'body': json.dumps('Invalid signature')
        }
    
    # 解析事件
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        return {
            'statusCode': 403,
            'body': json.dumps('Invalid signature')
        }
    
    # 處理每個事件
    for event in events:
        if isinstance(event, MessageEvent):
            if isinstance(event.message, TextMessage):
                handle_text_message(event)
    
    return {
        'statusCode': 200,
        'body': json.dumps('OK')
    }


def verify_signature(body, signature):
    """驗證 LINE 的簽章"""
    hash_value = hmac.new(
        CHANNEL_SECRET.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    expected_signature = base64.b64encode(hash_value).decode('utf-8')
    return signature == expected_signature


def handle_text_message(event):
    """處理文字訊息"""
    user_id = event.source.user_id
    user_message = event.message.text
    
    print(f"收到訊息 - 用戶ID: {user_id}, 內容: {user_message}")
    
    # 根據訊息內容回應
    if user_message == "我的ID":
        reply_text = f"你的 LINE ID 是:\n{user_id}"
    
    elif user_message == "你好":
        reply_text = "你好！我是 LINE Bot 😊"
    
    elif user_message.startswith("echo "):
        reply_text = user_message[5:]  # 回應 "echo " 後面的文字
    
    else:
        reply_text = f"你說: {user_message}\n\n試試看輸入:\n- 我的ID\n- 你好\n- echo 你的訊息"
    
    # 回覆訊息
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )


def push_message_to_user(user_id, message):
    """主動發送訊息給用戶（可在其他 Lambda 函數中呼叫）"""
    try:
        line_bot_api.push_message(
            user_id,
            TextSendMessage(text=message)
        )
        return True
    except Exception as e:
        print(f"發送訊息失敗: {str(e)}")
        return False