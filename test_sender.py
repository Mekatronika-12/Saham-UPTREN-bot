
import asyncio
import config
from telegram import Bot

async def send_hello():
    bot = Bot(token=config.TELEGRAM_TOKEN)
    print(f"Sending to {config.TELEGRAM_CHAT_ID}...")
    await bot.send_message(chat_id=config.TELEGRAM_CHAT_ID, text="👋 Halo Boss! Ini pesan tes manual dari saya.\n\nSistem Aman 100%. 🚀")
    print("Sent!")

if __name__ == "__main__":
    asyncio.run(send_hello())
