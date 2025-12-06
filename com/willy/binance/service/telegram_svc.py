import asyncio

from telegram import Bot

from com.willy.binance.config.config_util import config_util

# 將 YOUR_BOT_TOKEN 和 YOUR_CHAT_ID 替換為您的實際值
telegram_bot_config = config_util("telegram_bot")
TOKEN = telegram_bot_config.get("token")


async def send_telegram_message(user_id, msg):
    # 建立 Bot 物件
    bot = Bot(token=TOKEN)

    # 確保在非同步環境中執行
    async with bot:
        # 使用 send_message() 方法發送訊息
        await bot.send_message(chat_id=user_id, text=msg)
        print("Message sent successfully!")


def push_message(user_id=telegram_bot_config.get("userid_willy"), message="message"):
    # 執行非同步函數
    asyncio.run(send_telegram_message(user_id, message))
