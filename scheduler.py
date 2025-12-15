"""
Scheduler untuk menjalankan bot setiap hari jam 9 pagi dan 13:30 WIB
"""

import asyncio
import schedule
import time
import logging
from datetime import datetime
from telegram_bot import StockSignalBot
from config import (
    TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, STOCK_TICKERS,
    SCAN_MODE, SCAN_ALL_CONFIG
)
from idx_ticker_fetcher import (
    get_all_idx_tickers, load_tickers_from_file,
    save_tickers_to_file
)
import pytz

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def get_tickers_to_scan():
    """Mendapatkan list ticker yang akan di-scan"""
    # Force mode "all_idx" sesuai request user untuk scan 600+ saham
    # Kita mengabaikan config sementara untuk memastikan requirement user terpenuhi
    scan_mode = "all_idx" # Defaulting to all_idx as requested
    
    if scan_mode == "all_idx":
        logger.info("Mode: Scan semua saham IDX (600+ Emiten)")
        
        # Coba load dari cache dulu
        # Gunakan list yang ada di file jika tersedia
        cached_tickers = load_tickers_from_file("idx_tickers.txt")
        if cached_tickers and len(cached_tickers) > 800:
            logger.info(f"Menggunakan {len(cached_tickers)} ticker dari database")
            # Unlimited tickers (scan semua)
            return cached_tickers
        
        if cached_tickers:
             logger.warning(f"Database ticker outdated ({len(cached_tickers)} emiten). Mencoba update...")
        
        # Jika cache tidak ada, fetch baru
        logger.info("Database ticker kosong, mengambil dari yfinance...")
        all_tickers = get_all_idx_tickers()
        
        if all_tickers:
            save_tickers_to_file(all_tickers, "idx_tickers.txt")
            return all_tickers
        else:
            logger.warning("Gagal mendapatkan ticker, menggunakan default")
            return STOCK_TICKERS
    else:
        # Fallback (tidak akan tereksekusi jika kita force all_idx)
        return STOCK_TICKERS


def run_daily_signals():
    """Function yang akan dijalankan setiap hari jam 9 pagi dan 13:30"""
    current_time = datetime.now(pytz.timezone('Asia/Jakarta')).strftime('%H:%M')
    logger.info(f"Memulai scan saham pada jam {current_time} WIB...")
    
    # Dapatkan ticker yang akan di-scan
    tickers_to_scan = get_tickers_to_scan()
    
    if not tickers_to_scan:
        logger.error("Tidak ada ticker untuk di-scan!")
        return
    
    logger.info(f"Total ticker yang akan di-scan: {len(tickers_to_scan)}")
    
    bot = StockSignalBot(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    
    # Jalankan async function
    asyncio.run(bot.send_daily_signals(tickers_to_scan))
    
    logger.info(f"Scan selesai pada jam {current_time} WIB")


def main():
    """Main function untuk menjalankan scheduler"""
    wib = pytz.timezone('Asia/Jakarta')
    
    # Schedule tugas setiap hari jam 08:49 WIB (Sesi 1 - Setelah IEP keluar)
    schedule.every().day.at("08:49").do(run_daily_signals)
    
    # Schedule tugas setiap hari jam 13:00 WIB (Sesi 2)
    schedule.every().day.at("13:00").do(run_daily_signals)
    
    # === REALTIME SCANNING (SETIAP 10 MENIT) ===
    # Bot akan mengecek pasar terus menerus selama jam trading
    def run_realtime_job():
        # Cek apakah jam pasar (09:00 - 15:45 WIB)
        now = datetime.now(wib)
        if (now.hour == 9) or (now.hour > 9 and now.hour < 15) or (now.hour == 15 and now.minute < 45):
             # Skip jika ini jam jadwal utama (biar gak double)
             if not (now.hour == 8 and now.minute == 49) and not (now.hour == 13 and now.minute == 0):
                 run_daily_signals() # Panggil fungsi scan
                 
    schedule.every(10).minutes.do(run_realtime_job)
    
    # Test sekali saat startup
    logger.info("Scheduler dimulai. Bot akan mengirim sinyal:")
    logger.info("  - Jam 08:49 WIB (Start Sesi 1)")
    logger.info("  - Jam 13:00 WIB (Start Sesi 2)")
    logger.info("  - REALTIME: Setiap 10 menit saat pasar buka")
    logger.info(f"Mode scan: {SCAN_MODE}")
    
    # Preview ticker yang akan di-scan
    preview_tickers = get_tickers_to_scan()
    logger.info(f"Total ticker yang akan di-scan: {len(preview_tickers)}")
    if preview_tickers and len(preview_tickers) <= 10:
        logger.info(f"Ticker: {', '.join(preview_tickers)}")
    elif preview_tickers:
        logger.info(f"Contoh ticker: {', '.join(preview_tickers[:5])}...")
    
    logger.info("Tekan Ctrl+C untuk menghentikan")
    
    # Test run (optional - comment jika tidak ingin test)
    # logger.info("Running test scan...")
    # run_daily_signals()
    
    # Main loop
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check setiap 1 menit


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Scheduler dihentikan oleh user")
    except Exception as e:
        logger.error(f"Error: {str(e)}")

