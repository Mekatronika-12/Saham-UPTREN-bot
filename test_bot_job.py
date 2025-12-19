
import asyncio
import logging
from datetime import time
import pytz
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
import config

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello!")

async def job_func(context: ContextTypes.DEFAULT_TYPE):
    print("Job running")

def main():
    print("Starting Test Bot with JobQueue...")
    application = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    
    job_queue = application.job_queue
    t = time(12, 0, tzinfo=pytz.timezone('Asia/Jakarta'))
    job_queue.run_daily(job_func, t, days=(0, 1, 2, 3, 4))
    
    print("Polling...")
    application.run_polling()

if __name__ == "__main__":
    main()
