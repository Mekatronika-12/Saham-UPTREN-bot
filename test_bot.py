
import asyncio
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
import config

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello!")

def main():
    print("Starting Test Bot...")
    application = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    
    print("Polling...")
    application.run_polling()

if __name__ == "__main__":
    main()
