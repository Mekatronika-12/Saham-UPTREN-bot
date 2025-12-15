"""
Bot Telegram untuk Sinyal Saham Uptrend
Mengirim sinyal setiap hari jam 9 pagi WIB dan Merespon Command Analisa
"""

import asyncio
import logging
from datetime import datetime, time
import pytz
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from stock_analyzer import StockAnalyzer
from idx_ticker_fetcher import load_tickers_from_file, get_all_idx_tickers, save_tickers_to_file
import config
from chart_generator import generate_stock_chart
import os
from telegram import constants
import yfinance as yf

# ... [Setup logging] ...

# ... [Other handlers] ...

async def analyze_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pesan text user"""
    text = update.message.text.upper().strip()
    
    # Check trigger pattern
    if text.startswith("ANALISA SAHAM") or text.startswith("ANALISA"):
        parts = text.split()
        if len(parts) < 2:
            await update.message.reply_text("⚠️ Format salah. Gunakan: `ANALISA SAHAM [KODE]`\nContoh: `ANALISA SAHAM BBCA`", parse_mode='Markdown')
            return
            
        ticker_code = parts[-1].replace("$", "")
        if not ticker_code.endswith(".JK"):
            ticker_code += ".JK"
            
        # 1. Loading Animation / Status
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
        processing_msg = await update.message.reply_text(f"⏳ Sedang menganalisa pasar untuk *{ticker_code}*...", parse_mode='Markdown')
        
        try:
            # Run Analysis
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, analyzer.analyze_stock_detailed, ticker_code)
            
            if not result.get("success"):
                await processing_msg.edit_text(f"❌ Gagal menganalisa saham {ticker_code}.\nError: {result.get('error')}")
                return
            
            # Format Text
            message = format_detailed_message(result)
            
            # 2. Generate Chart
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.UPLOAD_PHOTO)
            
            # Need history for chart
            stock = yf.Ticker(ticker_code)
            hist = stock.history(period="1y")
            
            chart_filename = f"chart_{ticker_code.replace('.','_')}"
            chart_path = await loop.run_in_executor(None, generate_stock_chart, hist, ticker_code, chart_filename)
            
            # Delete "Analysing..." message
            await processing_msg.delete()
            
            # Send Photo + Caption
            if chart_path and os.path.exists(chart_path):
                await update.message.reply_photo(
                    photo=open(chart_path, 'rb'),
                    caption=message,
                    parse_mode='Markdown'
                )
                # Cleanup
                try:
                    os.remove(chart_path)
                except:
                    pass
            else:
                # Fallback text only
                await update.message.reply_text(message, parse_mode='Markdown', disable_web_page_preview=True)
            
        except Exception as e:
            logger.error(f"Error analyzing {ticker_code}: {e}")
            await processing_msg.edit_text("❌ Terjadi kesalahan internal saat analisis.")


# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global Analyzer
analyzer = StockAnalyzer()
WIB = pytz.timezone('Asia/Jakarta')

# === HELPER FUNCTIONS ===

def format_detailed_message(result: dict) -> str:
    """Format pesan analisis detail"""
    if not result.get("success"):
        return f"❌ Error: {result.get('error')}"
        
    ticker = result['ticker'].replace(".JK", "")
    prices = result
    fund = result['fundamentals']
    
    # Emojis
    e_ent = "🚪" 
    e_sup = "🔻"
    e_res = "🚀"
    e_tp1 = "💴"
    e_tp2 = "💵"
    e_tp3 = "💸"
    e_warn = "🔴 ‼"
    
    msg = f"📊 *Analisis Saham ${ticker}*\n\n"
    
    # Status Narrative
    msg += f"{result['narrative']}\n\n"
    
    # Fundamental
    msg += "Kondisi Fundamental:\n"
    msg += f"• EPS (Earnings Per Share): {fund['eps']}\n"
    msg += f"• Net Income (TTM): {fund['net_income']}\n"
    msg += f"• Total Aset: {fund['total_assets']}\n\n"
    
    # Entry & Levels
    msg += f"{e_ent} Entry: {prices['entry']}\n"
    msg += f"Support: {prices['support']}\n"
    msg += f"{e_res} Resistance: {prices['resistance']}\n\n"
    
    # TP
    msg += f"{e_tp1} TP 1: {prices['tp1']}\n"
    msg += f"{e_tp2} TP 2: {prices['tp2']}\n"
    msg += f"{e_tp3} TP 3: {prices['tp3']}\n\n"
    
    msg += f"Cutloss: {prices['cutloss']}\n\n"
    
    msg += f"{e_warn} Peringatan: {prices['risk_warning']}\n\n"
    
    return msg

def format_daily_signal(result: dict) -> str:
    """Format legacy daily signal (simple version)"""
    ticker = result["ticker"].replace(".JK", "")
    entry = result["entry"]
    tp = result["tp"]
    profit_pct = result["profit_pct"]
    current_price = result["current_price"]
    
    profit_emoji = "🔥" if profit_pct > 10 else "⚡"
    
    msg = f"{profit_emoji} *SINYAL UPTREND* - {ticker}\n"
    msg += f"Harga: {current_price}\n"
    msg += f"Entry: {entry}\n"
    msg += f"TP: {tp} (+{profit_pct:.1f}%)\n"
    msg += f"⏳ Est. Hit: {result.get('est_hit_days', '3-7 Hari')}\n"
    msg += f"Status: {result.get('recommended_option')}\n"
    return msg

# ... [Imports]
import json

# File storage for broadcast groups
BROADCAST_FILE = "broadcast_groups.json"

def load_broadcast_groups():
    if not os.path.exists(BROADCAST_FILE):
        return []
    try:
        with open(BROADCAST_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_broadcast_group(chat_id):
    groups = load_broadcast_groups()
    if chat_id not in groups:
        groups.append(chat_id)
        with open(BROADCAST_FILE, 'w') as f:
            json.dump(groups, f)
        return True
    return False

# ...

    return False

# === HANDLERS ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Halo Trader!*\n\n"
        "Saya adalah *Bot Sinyal Uptrend* yang siap membantu analisa pasar saham Indonesia (IDX).\n\n"
        "📜 *Daftar Perintah (Bisa di Group/Private):*\n\n"
        "1️⃣ *Analisa Saham*\n"
        "   👉 Ketik: `/analisa [KODE]`\n"
        "   Contoh: `/analisa BBCA`\n"
        "   _Bot akan mengirim chart + analisa lengkap._\n\n"
        "2️⃣ *Daftarkan Group (Khusus Admin)*\n"
        "   👉 Ketik: `/setalert`\n"
        "   _Agar group ini menerima sinyal harian otomatis._\n\n"
        "3️⃣ *Cek ID*\n"
        "   👉 Ketik: `/id`\n"
        "   _Untuk melihat ID Chat/Group ini._\n\n"
        "⏰ *Jadwal Sinyal Otomatis:*\n"
        "• Sesi 1: 08:30 WIB\n"
        "• Sesi 2: 13:00 WIB\n\n"
        "🚀 _Happy Trading & Good Luck!_",
        parse_mode='Markdown'
    )

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /analisa [KODE] (Lebih reliabel di group)"""
    # Combine args
    if not context.args:
        await update.message.reply_text("⚠️ Gunakan format: `/analisa [KODE]`\nContoh: `/analisa BBCA`", parse_mode='Markdown')
        return
        
    ticker_code = context.args[0].upper().replace("$", "")
    if not ticker_code.endswith(".JK"):
        ticker_code += ".JK"
        
    await process_analysis(update, context, ticker_code)

async def set_alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set group ini untuk menerima sinyal otomatis"""
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title or "Chat ini"
    
    if save_broadcast_group(chat_id):
        await update.message.reply_text(f"✅ Berhasil! Sinyal harian akan dikirim ke *{chat_title}* (ID: {chat_id}).", parse_mode='Markdown')
        # Send test
        await context.bot.send_message(chat_id, "🔔 Test Notifikasi Sinyal Uptrend aktif!")
    else:
        await update.message.reply_text(f"ℹ️ *{chat_title}* sudah terdaftar untuk notifikasi.", parse_mode='Markdown')

async def check_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cek Chat ID"""
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"🆔 Chat ID: `{chat_id}`", parse_mode='Markdown')

async def process_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE, ticker_code: str):
    """Reused Logic for Analysis"""
    # 1. Loading Animation
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    msg = await update.message.reply_text(f"⏳ Sedang menganalisa pasar untuk *{ticker_code}*...", parse_mode='Markdown')
    
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, analyzer.analyze_stock_detailed, ticker_code)
        
        if not result.get("success"):
            await msg.edit_text(f"❌ Gagal menganalisa saham {ticker_code}.\nError: {result.get('error')}")
            return
            
        # Use the formatted message directly from analyzer to avoid key errors
        message = result.get("message", "Analisis selesai.")
        
        # 2. Chart
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.UPLOAD_PHOTO)
        stock = yf.Ticker(ticker_code)
        hist = await loop.run_in_executor(None, stock.history, "1y")
        chart_filename = f"chart_{ticker_code.replace('.','_')}"
        chart_path = await loop.run_in_executor(None, generate_stock_chart, hist, ticker_code, chart_filename)
        
        # 3. Send Result
        # We delete the loading message first.
        try:
            await msg.delete()
        except:
            pass # Ignore if already deleted
        
        if chart_path and os.path.exists(chart_path):
            try:
                await update.message.reply_photo(photo=open(chart_path, 'rb'), caption=message, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Failed to send photo: {e}")
                await update.message.reply_text(message, parse_mode='Markdown', disable_web_page_preview=True)
            
            # Cleanup
            try: os.remove(chart_path)
            except: pass
        else:
            await update.message.reply_text(message, parse_mode='Markdown', disable_web_page_preview=True)
            
    except Exception as e:
        logger.error(f"Error processing {ticker_code}: {e}")
        # If msg still exists (error happened before delete), try edit
        try:
            await msg.edit_text("❌ Terjadi kesalahan internal saat analisis. Coba lagi.")
        except:
            # If edit fails (msg deleted), send new message
            await update.message.reply_text("❌ Terjadi kesalahan internal saat analisis.")

async def analyze_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pesan text user (Legacy)"""
    text = update.message.text.upper().strip()
    if text.startswith("ANALISA SAHAM") or text.startswith("ANALISA"):
        parts = text.split()
        if len(parts) < 2: return
        ticker = parts[-1].replace("$", "")
        if not ticker.endswith(".JK"): ticker += ".JK"
        await process_analysis(update, context, ticker)

# ...

async def daily_scan_job(context: ContextTypes.DEFAULT_TYPE):
    """Job untuk scanning harian"""
    logger.info("Running Daily Scan Job...")
    
    current_hour = datetime.now(WIB).hour
    session_id = 1 if current_hour < 12 else 2
    
    tickers = load_tickers_from_file("idx_tickers.txt")
    if not tickers or len(tickers) < 500:
         tickers = get_all_idx_tickers()
         save_tickers_to_file(tickers, "idx_tickers.txt")
    
    if not tickers: return
    
    logger.info(f"Scanning {len(tickers)} tickers...")
    
    loop = asyncio.get_running_loop()
    results = await loop.run_in_executor(None, analyzer.analyze_tickers_parallel, tickers, "6mo", 20, session_id)
    
    uptrend_results = [r for r in results if r.get("success") and r.get("is_uptrend")]
    uptrend_results.sort(key=lambda x: x.get('analysis', {}).get('score', 0), reverse=True)
    
    top_picks = uptrend_results[:10]
    if not top_picks: return
        
    summary = f"🔥 *SINYAL MARKET - SESI {session_id}*\n\n"
    for r in top_picks:
        summary += f"• {r['ticker']} (Score: {r['analysis']['score']})\n"
        
    # BROADCAST TO ALL REGISTERED GROUPS AND CONFIG ID
    # Use set to avoid duplicates and normalize to string
    raw_groups = load_broadcast_groups()
    targets = {str(gid) for gid in raw_groups}
    
    # Ensure config ID is added safely
    if config.TELEGRAM_CHAT_ID:
        targets.add(str(config.TELEGRAM_CHAT_ID))
    
    # Filter out empty or None
    targets = {tid for tid in targets if tid}
    
    for chat_id in targets:
        try:
            # 1. Send Summary List
            await context.bot.send_message(chat_id=chat_id, text=summary, parse_mode='Markdown')
            
            # 2. Send Details (ALL picks as requested)
            for pick in top_picks:
                msg = format_daily_signal(pick)
                await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
                await asyncio.sleep(1) # Prevent flood limit
                
        except Exception as e:
            logger.error(f"Failed to send to {chat_id}: {e}")


async def bsjp_scan_job(context: ContextTypes.DEFAULT_TYPE):
    """Job khusus untuk Sinyal BSJP (Beli Sore Jual Pagi) - 15:40 WIB"""
    logger.info("Running BSJP Scan Job...")
    
    tickers = load_tickers_from_file("idx_tickers.txt")
    if not tickers or len(tickers) < 500:
         tickers = get_all_idx_tickers()
    
    if not tickers: return
    
    # Run BSJP Screening Parallel
    loop = asyncio.get_running_loop()
    
    # Helper for batch processing
    def batch_bsjp(ticker_list):
        matches = []
        for t in ticker_list:
            if analyzer.analyze_bsjp_ticker(t):
                 matches.append(t)
        return matches

    chunk_size = 50
    chunks = [tickers[i:i + chunk_size] for i in range(0, len(tickers), chunk_size)]
    
    bsjp_matches = []
    
    for chunk in chunks:
        # Run chunk in executor
        chunk_matches = await loop.run_in_executor(None, batch_bsjp, chunk)
        bsjp_matches.extend(chunk_matches)
    
    if not bsjp_matches:
        logger.info("No BSJP matches found today.")
        return
        
    # Format Message EXACTLY as requested (With Aesthetic Emojis)
    # Header
    msg = "🌙 *BOT BSJP WATCHLIST* 🌙\n\n"
    
    # List Tickers
    for m in bsjp_matches[:10]: 
        msg += f"💎 ${m.replace('.JK', '')}\n"
    
    msg += "\n"
    msg += "📢 *Instruksi:*\n"
    msg += "Beli diharga IEP sebelum closing, HAKA diatas harga sekarang.\n\n"
    msg += "🎯 TP : 2-5%\n"
    msg += "🛡 SL : -2%\n\n"
    msg += "⏰ *Jual:* Jam 09:00 - 10:00 pagi besok.\n\n"
    msg += "⚠️ *Disclaimer:* Hanya sebatas rekomendasi, bukan ajakan jual beli.\n"
    msg += "#DYOR Semoga cuan. 🚀"
    
    # Broadcast
    raw_groups = load_broadcast_groups()
    targets = {str(gid) for gid in raw_groups}
    
    if config.TELEGRAM_CHAT_ID:
        targets.add(str(config.TELEGRAM_CHAT_ID))
    
    targets = {tid for tid in targets if tid}
    
    logger.info(f"Broadcasting BSJP to {len(targets)} targets. Matches: {len(bsjp_matches)}")
    
    for chat_id in targets:
        try:
            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Failed to send BSJP to {chat_id}: {e}")

def main():
    """Run the bot"""
    print("Starting Bot...")
    application = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("analisa", analyze_command))
    application.add_handler(CommandHandler("setalert", set_alert_command))
    application.add_handler(CommandHandler("id", check_id_command))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), analyze_message_handler))
    
    # Job Queue
    job_queue = application.job_queue
    t1 = time(8, 30, tzinfo=WIB)
    t2 = time(13, 0, tzinfo=WIB)
    t3 = time(15, 30, tzinfo=WIB) # BSJP Job time (Safe start, internal job handles 15:40 limit or just run at 15:40?) Request says 15:40.
    # Actually user said "kirimkan ... pada jam 3.40 sore"
    t_bsjp = time(15, 40, tzinfo=WIB)
    
    job_queue.run_daily(daily_scan_job, t1, days=(0, 1, 2, 3, 4))
    job_queue.run_daily(daily_scan_job, t2, days=(0, 1, 2, 3, 4))
    job_queue.run_daily(bsjp_scan_job, t_bsjp, days=(0, 1, 2, 3, 4))
    
    print("Bot is polling...")
    application.run_polling()

if __name__ == "__main__":
    main()
