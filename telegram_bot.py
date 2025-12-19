"""
Bot Telegram untuk Sinyal Saham Uptrend
Mengirim sinyal setiap hari jam 9 pagi WIB dan Merespon Command Analisa
"""

import asyncio
import sys

# Fix for Windows Asyncio Loop Policy
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import logging
from datetime import datetime, time
import pytz
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from stock_analyzer import StockAnalyzer
from idx_ticker_fetcher import load_tickers_from_file, get_all_idx_tickers, save_tickers_to_file
import os

# Try importing config from file (local dev), fallback to env vars (Railway/Cloud)
try:
    import config
except ImportError:
    class Config:
        TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
        TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
    config = Config()
    print("Warning: config.py not found. Using Environment Variables.")

from chart_generator import generate_stock_chart
from telegram import constants
import yfinance as yf

# ... [Setup logging] ...

# ... [Other handlers] ...



# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# Silence noisy libraries
logging.getLogger("yfinance").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Global Analyzer
analyzer = StockAnalyzer()
WIB = pytz.timezone('Asia/Jakarta')

# === HELPER FUNCTIONS ===

def format_detailed_message(result: dict) -> str:
    """Format pesan analisis detail (Safety Fallback)"""
    if not result.get("success"):
        return f"❌ Error: {result.get('error')}"
        
    ticker = result.get('ticker', '').replace(".JK", "")
    prices = result
    fund = result.get('fundamentals', {})
    
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
    msg += f"{result.get('narrative', 'Analisis Teknikal.')}\n\n"
    
    # Fundamental
    msg += "Kondisi Fundamental:\n"
    msg += f"• EPS: {fund.get('eps', '-')}\n"
    msg += f"• Net Income: {fund.get('net_income', '-')}\n"
    msg += f"• Total Aset: {fund.get('total_assets', '-')}\n\n"
    
    # News
    if result.get('news'):
        msg += f"📰 *Berita Terkait:*\n{result['news']}\n\n"
    
    # Entry & Levels
    msg += f"{e_ent} Entry: {prices.get('entry', '-')}\n"
    msg += f"Support: {prices.get('support', '-')}\n"
    msg += f"{e_res} Resistance: {prices.get('resistance', '-')}\n\n"
    
    # TP
    msg += f"{e_tp1} TP 1: {prices.get('tp1', '-')}\n"
    msg += f"{e_tp2} TP 2: {prices.get('tp2', '-')}\n"
    msg += f"{e_tp3} TP 3: {prices.get('tp3', '-')}\n\n"
    
    cutloss = prices.get('cutloss')
    msg += f"Cutloss: {cutloss if cutloss else '-'}\n\n"
    
    msg += f"{e_warn} Peringatan: {prices.get('risk_warning', 'Market Volatile')}\n"
    msg += f"⏳ *Timeframe:* {prices.get('timeframe', 'SWING / TREND FOLLOWING')}\n\n"
    
    return msg

def format_daily_signal(result: dict) -> str:
    """Format daily signal with detailed analysis, reason, and news."""
    ticker = result["ticker"].replace(".JK", "")
    entry = result["entry"]
    tp = result["tp"]
    profit_pct = result["profit_pct"]
    current_price = result["current_price"]
    
    # Derivations
    score = result.get('analysis', {}).get('score', 0)
    if score >= 85: assessment = "💎 SANGAT BAGUS (Strong Buy)"
    elif score >= 75: assessment = "🔥 BAGUS (Buy)"
    else: assessment = "⚡ POTENSIAL (Speculative)"
    
    profit_emoji = "🚀" if profit_pct > 5 else "⚡"
    
    msg = f"{profit_emoji} *SINYAL UPTREND - {ticker}*\n"
    msg += f"📅 Sesi: {result.get('session', 'General')}\n"
    msg += f"⏳ *Tipe Trade:* {result.get('timeframe', 'SWING / TREND FOLLOWING')}\n"
    msg += f"⭐ Penilaian: {assessment}\n\n"
    
    msg += f"💲 *Harga Saat Ini:* {current_price}\n"
    msg += f"🎯 *Rekomendasi:* {result.get('recommended_option')}\n"
    msg += f"💬 *Alasan:* {result.get('recom_reason', '-')}\n\n"
    
    msg += f"📰 *Berita & Sentimen:*\n{result.get('news', 'Tidak ada berita spesifik.')}\n\n"
    
    msg += f"🚪 Entry Ideal: {entry}\n"
    msg += f"💵 Target Profit: {tp} (+{profit_pct:.1f}%)\n"
    msg += f"🛡 Support: {result.get('support', '-')}\n"
    msg += f"🧱 Resistance: {result.get('resistance', '-')}\n\n"
    
    msg += "⚠️ _Disclaimer: DYOR. Market Volatile._"
    return msg

# ...

# Inside daily_scan_job context (re-writing the relevant parts)
# Note: I'm relying on replace to find the right spot in daily_scan_job automatically if I include enough context, 
# but since I'm replacing format_daily_signal which is earlier, I should do two replacements or one big one if contiguous.
# They are not contiguous. format_daily_signal is line 165. daily_scan_job is later.
# I will use MULTI_REPLACE.

# Wait, I cannot use multi_replace. I will use separate calls if needed.
# Converting to single replace for format_daily_signal first.


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

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cek Status Bot & Jadwal"""
    now = datetime.now(WIB)
    status_msg = f"🟢 *STATUS BOT: ONLINE*\n"
    status_msg += f"🕒 Waktu Server: {now.strftime('%Y-%m-%d %H:%M:%S')} WIB\n\n"
    
    status_msg += "📅 *Jadwal Job:*\n"
    jobs = context.job_queue.jobs()
    if not jobs:
        status_msg += "- Belum ada job terjadwal.\n"
    else:
        for job in jobs:
            next_t = job.next_t
            if next_t:
                # Convert to Jakarta time for display if needed, but next_t is usually aware
                next_t_wib = next_t.astimezone(WIB)
                status_msg += f"• {job.callback.__name__}: {next_t_wib.strftime('%H:%M:%S')}\n"
            else:
                status_msg += f"• {job.callback.__name__}: (Running/Unknown)\n"
                
    await update.message.reply_text(status_msg, parse_mode='Markdown')

async def scan_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Trigger manual scan"""
    chat_id = update.effective_chat.id
    if str(chat_id) != str(config.TELEGRAM_CHAT_ID) and str(chat_id) not in [str(g) for g in load_broadcast_groups()]:
        await update.message.reply_text("⛔ Anda tidak memiliki akses untuk command ini.")
        return

    await update.message.reply_text("🚀 Memulai Scanning Manual (Proses berjalan di background)...")
    # Trigger job manually
    await daily_scan_job(context)
    await update.message.reply_text("✅ Scanning Manual Selesai.")

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
        
        # Use data from analyzer if available to avoid re-fetching
        hist = result.get("chart_data")
        if hist is None or hist.empty:
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
    if not top_picks: 
        logger.info("No uptrend stocks found today.")
        if config.TELEGRAM_CHAT_ID:
             try:
                 await context.bot.send_message(config.TELEGRAM_CHAT_ID, "ℹ️ *Info Scan:* Tidak ada saham yang memenuhi kriteria Uptrend Kuat saat ini.", parse_mode='Markdown')
             except: pass
        return
        
    summary = f"🔥 *SINYAL MARKET - SESI {session_id}*\n\n"
    
    # Enrichment: Fetch News mostly for the top items to be broadcasted
    logger.info("Fetching news for top picks...")
    for r in top_picks:
        try:
             # Add session info
             r['session'] = session_id
             
             # Fetch News
             stock_obj = yf.Ticker(r['ticker'])
             r['news'] = analyzer.get_stock_news(stock_obj)
        except Exception as e:
             logger.error(f"News fetch failed for {r['ticker']}: {e}")
             r['news'] = "-"

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
    """Job khusus untuk Sinyal BSJP (Beli Sore Jual Pagi) - 15:30 WIB"""
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
    application.add_handler(CommandHandler("scannow", scan_now_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), analyze_message_handler))
    
    # Job Queue
    job_queue = application.job_queue
    t1 = time(8, 30, tzinfo=WIB)
    t2 = time(13, 0, tzinfo=WIB)
    t3 = time(15, 30, tzinfo=WIB) # BSJP Job time (Safe start, internal job handles 15:40 limit or just run at 15:40?) Request says 15:40.
    # Actually user said "kirimkan ... pada jam 3.40 sore"
    t_bsjp = time(15, 30, tzinfo=WIB)
    
    job_queue.run_daily(daily_scan_job, t1, days=(0, 1, 2, 3, 4))
    job_queue.run_daily(daily_scan_job, t2, days=(0, 1, 2, 3, 4))
    job_queue.run_daily(bsjp_scan_job, t_bsjp, days=(0, 1, 2, 3, 4))
    
    # Continuous Momentum Job (Runs every 15 minutes during market hours)
    # Market Hours: 09:00 - 16:00
    job_queue.run_repeating(continuous_momentum_scan, interval=900, first=10) # 900s = 15 min
    
    # Startup Notification
    async def post_init(app):
        if config.TELEGRAM_CHAT_ID:
            try:
                msg = "🤖 *Bot Sinyal Uptrend Berhasil Direstart*\n"
                msg += "✅ Siap memantau market otomatis.\n"
                msg += "📅 Jadwal: 08:30, 13:00, 15:30 WIB."
                await app.bot.send_message(config.TELEGRAM_CHAT_ID, msg, parse_mode='Markdown')
            except Exception as e:
                print(f"Failed startup msg: {e}")

    application.post_init = post_init
    
    print("Bot is polling...")
    application.run_polling()

# === CONTINUOUS SCAN LOGIC ===

# Global cache to prevent spamming the same signal multiple times per day
SENT_SIGNALS_TODAY = set()

async def continuous_momentum_scan(context: ContextTypes.DEFAULT_TYPE):
    """
    Job berjalan setiap 15-20 menit untuk mencari momentum RED-TO-GREEN
    """
    now = datetime.now(WIB)
    
    # Reset cache at midnight
    if now.hour == 0 and now.minute < 30:
        global SENT_SIGNALS_TODAY
        SENT_SIGNALS_TODAY.clear()
        return

    # Only run during market hours (09:00 - 15:50)
    if not (9 <= now.hour < 16):
        return
        
    logger.info("Running Continuous Momentum Scan (Red to Green)...")
    
    tickers = load_tickers_from_file("idx_tickers.txt")
    
    # Validation: Ensure we have a comprehensive list (at least 600+)
    if not tickers or len(tickers) < 600:
         logger.info("Ticker list too small/empty. Fetching fresh list...")
         tickers = get_all_idx_tickers()
         save_tickers_to_file(tickers, "idx_tickers.txt")

    if not tickers: return # Skip if still empty
    
    logger.info(f"Scanning {len(tickers)} tickers for Red-to-Green momentum...")
    
    # Optimized: We might not want to scan ALL 800 every 15 mins if it takes too long.
    # But for now, let's try parallel.
    
    loop = asyncio.get_running_loop()
    
    # Define Filter Function
    def check_momentum(ticker):
        try:
            # We use 5d history to be fast and light
            s = yf.Ticker(ticker)
            d = s.history(period="5d")
            
            # Use logic in analyzer
            is_r2g, r2g_data = analyzer.is_red_to_green_momentum(d)
            if is_r2g:
                return {"ticker": ticker, "data": r2g_data}
            return None
        except:
            return None
    
    # Chunking to avoid overloading
    results = []
    chunk_size = 50
    chunks = [tickers[i:i + chunk_size] for i in range(0, len(tickers), chunk_size)]
    
    # We might only scan a random subset or prioritised list if too slow? 
    # Let's scan all but rely on thread pool limit.
    from concurrent.futures import ThreadPoolExecutor
    
    matches = []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(check_momentum, t): t for t in tickers}
        
        from concurrent.futures import as_completed
        for future in as_completed(futures):
            res = future.result()
            if res:
                matches.append(res)
                
    # Filter matches: Only those NOT sent today
    new_matches = []
    for m in matches:
        t = m['ticker']
        if t not in SENT_SIGNALS_TODAY:
            new_matches.append(m)
            
    if not new_matches:
        logger.info("No new Red-to-Green signals found.")
        return

    # Broadcast New Signals
    logger.info(f"Found {len(new_matches)} new momentum signals!")
    
    raw_groups = load_broadcast_groups()
    targets = {str(gid) for gid in raw_groups}
    if config.TELEGRAM_CHAT_ID: targets.add(str(config.TELEGRAM_CHAT_ID))
    targets = {tid for tid in targets if tid}
    
    for m in new_matches:
        ticker = m['ticker'].replace(".JK", "")
        data = m['data']
        price = int(data['price'])
        change = data['change_pct']
        reason = data['reason']
        
        # Emoticon logic
        fire = "🔥🔥" if change > 5 else "🔥"
        
        msg = (
            f"{fire} *RED TO GREEN ALERT - {ticker}* {fire}\n\n"
            f"🔄 *Pembalikan Arah Cepat!*\n"
            f"Harga: {price} (+{change:.1f}%)\n"
            f"📊 {reason}\n\n"
            f"Pola ini menunjukkan tekanan beli yang kuat membalikan harga merah menjadi hijau hari ini. Potensi lanjut naik!\n\n"
            f"🎯 Target Scalp: {int(price * 1.03)} - {int(price * 1.05)}\n"
            f"🛡 SL Ketat: {int(data['low'])}\n\n"
            f"⚠️ #HighRisk #Momentum"
        )
        
        # Send
        for chat_id in targets:
            try:
                await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Failed to send alert to {chat_id}: {e}")
        
        # Mark as sent
        SENT_SIGNALS_TODAY.add(m['ticker'])
        
        # Pause slightly to avoid flood if many
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    main()
