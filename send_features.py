
import asyncio
import config
from telegram import Bot

async def send_features():
    bot = Bot(token=config.TELEGRAM_TOKEN)
    
    msg = (
        "🤖 *FITUR & KEMAMPUAN BOT SAHAM 2.0* 🤖\n\n"
        
        "1️⃣ *ANALISA SAHAM LENGKAP*\n"
        "Gunakan perintah: `/analisa [KODE]` (Contoh: `/analisa BUMI`)\n"
        "✅ *Smart Entry System:* Otomatis mendeteksi market lagi Rame (HAKA) atau Sepi (Nunggu Bawah).\n"
        "   - 🔹 *Best Buy:* Entry paling optimal.\n"
        "   - 🔸 *Aggressive:* Untuk market breakout/rally.\n"
        "   - 🛡 *Conservative:* Untuk antri aman (pullback).\n"
        "✅ *Target Profit Bertingkat:* TP1 (Scalp), TP2 (Swing), TP3 (Jackpot).\n"
        "✅ *Berita & Sentimen:* Menampilkan berita terbaru emiten + sentimennya.\n"
        "✅ *Fundamental:* EPS, Net Income, Aset.\n"
        "✅ *Chart:* Gambar grafik harga 1 tahun terakhir.\n\n"
        
        "2️⃣ *BROADCAST SINYAL OTOMATIS*\n"
        "Bot otomatis scan pasar & kirim sinyal ke grup ini pada:\n"
        "⏰ *08:30 WIB (Sesi 1)* - Persiapan market buka.\n"
        "⏰ *13:00 WIB (Sesi 2)* - Update sesi siang.\n"
        "📌 *Keunggulan:* Sinyal UPTREND pilihan (Score > 70), dilengkapi Alasan Entry & Berita.\n\n"
        
        "3️⃣ *FITUR BSJP (Beli Sore Jual Pagi)*\n"
        "⏰ *15:40 WIB (Jelang Tutup)*\n"
        "🔍 Screening saham momentum penutupan untuk dijual besok pagi (Cuan cepat).\n\n"
        
        "4️⃣ *SISTEM PINTAR (AI-Logic)*\n"
        "🧠 *Market Narrative:* Penjelasan kondisi market dengan bahasa manusia (bukan cuma angka).\n"
        "🧠 *Anti-Jebakan:* Deteksi False Breakout & peringatan jika market volatile.\n"
        "🧠 *Real-time Price:* Menggunakan harga detik ini, bukan harga kemarin.\n\n"
        
        "🚀 _Bot ini didesain untuk membantu Anda cuan lebih cerdas & objektif._"
    )
    
    print(f"Sending features to {config.TELEGRAM_CHAT_ID}...")
    await bot.send_message(chat_id=config.TELEGRAM_CHAT_ID, text=msg, parse_mode='Markdown')
    print("Sent!")

if __name__ == "__main__":
    asyncio.run(send_features())
