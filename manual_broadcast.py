
import asyncio
import config
from stock_analyzer import StockAnalyzer
from telegram import Bot
import yfinance as yf

# Logic copied from telegram_bot.py for consistency
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
    msg += f"📅 Sesi: Manual Test\n"
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

async def main():
    print("🚀 Memulai Manual Broadcast Sesi 2...")
    analyzer = StockAnalyzer()
    
    # Ambil tickers (Scan cepat 50 saham top cap/liquid agar tidak terlalu lama untuk test)
    # Gunakan data hardcoded atau load sedikit dari file
    tickers = ["BBRI.JK", "BMRI.JK", "BBCA.JK", "BBNI.JK", "TLKM.JK", 
               "ASII.JK", "UNTR.JK", "ADRO.JK", "PTBA.JK", "BUMI.JK", 
               "BRMS.JK", "GOTO.JK", "ANTM.JK", "MDKA.JK", "INKP.JK"]
               
    print(f"Menganalisa {len(tickers)} saham sampel...")
    
    # Analyze
    results = analyzer.analyze_multiple_stocks(tickers, session=2)
    
    # Filter Uptrend
    uptrend_results = [r for r in results if r.get("is_uptrend")]
    uptrend_results.sort(key=lambda x: x.get('analysis', {}).get('score', 0), reverse=True)
    
    top_picks = uptrend_results[:5] # Ambil 5 teratas
    
    if not top_picks:
        print("Tidak ada saham uptrend terdeteksi dari sampel.")
        return

    print(f"Ditemukan {len(top_picks)} saham uptrend.")
    
    # Init Bot
    bot = Bot(token=config.TELEGRAM_TOKEN)
    target_chat_id = config.TELEGRAM_CHAT_ID
    
    summary = "🔥 *TEST MANUAL - SINYAL MARKET SESI 2*\n\n"
    
    # Enrichment
    for r in top_picks:
         r['session'] = 2
         try:
             stock_obj = yf.Ticker(r['ticker'])
             r['news'] = analyzer.get_stock_news(stock_obj)
         except Exception as e:
             r['news'] = "-"
         summary += f"• {r['ticker']} (Score: {r['analysis']['score']})\n"

    print("Sending Summary...")
    await bot.send_message(chat_id=target_chat_id, text=summary, parse_mode='Markdown')
    
    print("Sending Details...")
    for pick in top_picks:
        msg = format_daily_signal(pick)
        await bot.send_message(chat_id=target_chat_id, text=msg, parse_mode='Markdown')
        await asyncio.sleep(1)
        
    print("✅ Selesai!")

if __name__ == "__main__":
    asyncio.run(main())
