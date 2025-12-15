# Bot Telegram Sinyal Saham Uptrend

Bot Telegram yang mengirimkan sinyal saham uptrend setiap hari jam 9 pagi dan 13:30 WIB, dengan analisis entry point dan take profit menggunakan indikator teknikal terbaik.

## ✨ Fitur

- 🔍 **Deteksi Uptrend Cerdas**: Menggunakan kombinasi multiple indikator (SMA, RSI, MACD, Volume, ATR)
- 📊 **Entry & Take Profit**: Menghitung entry point dan target profit secara otomatis
- ⚠️ **Peringatan ARA**: Memberikan notifikasi jika ada potensi Auto Rejection Atas
- 📈 **Profit Analysis**: Memberikan catatan khusus jika profit target hanya 2-3%
- ⏰ **Auto Scheduler**: Mengirim sinyal otomatis setiap hari jam 9 pagi dan 13:30 WIB (2 sesi)
- 📱 **Telegram Integration**: Terintegrasi dengan Telegram untuk notifikasi real-time

## 🔧 Instalasi

### 1. Clone atau Download Repository

```bash
git clone <repository-url>
cd Saham-UPTREN
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Catatan**: Untuk library `ta-lib`, jika mengalami masalah instalasi di Windows, ikuti langkah berikut:

1. Download whl file dari: https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
2. Install dengan: `pip install TA_Lib‑0.4.28‑cp39‑cp39‑win_amd64.whl` (sesuaikan versi Python Anda)

Alternatif: Jika `ta-lib` bermasalah, library ini opsional. Kode sudah menggunakan implementasi manual.

### 3. Setup Telegram Bot

1. **Buat Bot Telegram**:
   - Buka Telegram dan cari `@BotFather`
   - Kirim perintah `/newbot`
   - Ikuti instruksi untuk membuat bot baru
   - Simpan **Token** yang diberikan BotFather

2. **Dapatkan Chat ID**:
   - Buka Telegram dan cari `@userinfobot`
   - Kirim pesan ke bot tersebut
   - Bot akan memberikan Chat ID Anda (angka)
   - Simpan **Chat ID** tersebut

3. **Konfigurasi Bot**:
   - Buka file `config.py`
   - Isi `TELEGRAM_TOKEN` dengan token dari BotFather
   - Isi `TELEGRAM_CHAT_ID` dengan Chat ID Anda
   - Edit `STOCK_TICKERS` sesuai saham yang ingin di-scan

### 4. Test Bot

```bash
python telegram_bot.py
```

Jika berhasil, Anda akan menerima pesan test dari bot di Telegram.

## 🚀 Penggunaan

### Menjalankan Scheduler (Auto Daily)

```bash
python scheduler.py
```

Bot akan berjalan dan mengirim sinyal setiap hari jam 9 pagi dan 13:30 WIB (2 sesi).

**Untuk menjalankan di background (Linux/Mac)**:
```bash
nohup python scheduler.py > bot.log 2>&1 &
```

**Untuk Windows (gunakan Task Scheduler)**:
- Buat task baru di Task Scheduler
- Set trigger: Daily at 9:00 AM
- Action: Start program dengan path ke `python scheduler.py`

### Test Analisis Satu Saham

```bash
python stock_analyzer.py
```

Atau edit file `telegram_bot.py` untuk test satu saham tertentu.

## 📊 Metodologi Analisis

Bot menggunakan kombinasi indikator teknikal berikut:

### 1. **Simple Moving Average (SMA)**
   - SMA 20 hari dan SMA 50 hari
   - Deteksi trend direction
   - Golden cross confirmation

### 2. **Relative Strength Index (RSI)**
   - Periode 14 hari
   - Deteksi momentum (50-70 = healthy uptrend)
   - Menghindari overbought condition

### 3. **MACD (Moving Average Convergence Divergence)**
   - EMA 12, EMA 26, Signal 9
   - Konfirmasi trend bullish
   - Histogram untuk momentum

### 4. **Volume Analysis**
   - Volume Moving Average (20 hari)
   - Konfirmasi dengan volume di atas average

### 5. **ATR (Average True Range)**
   - Periode 14 hari
   - Menghitung volatilitas untuk menentukan TP realistis

### 6. **Support & Resistance**
   - Level support dan resistance dari 20 hari terakhir
   - Digunakan untuk menentukan TP

### Scoring System

Bot menggunakan scoring system:
- Score ≥ 6: Saham dianggap uptrend
- Multiple confirmation untuk mengurangi false signal

### Take Profit Calculation

TP dihitung menggunakan 3 metode dan dipilih yang paling realistis:
1. Berdasarkan ATR (1.8x ATR dari entry)
2. Berdasarkan Resistance Level
3. Berdasarkan persentase (3-5%)

## 📝 Format Pesan

Bot akan mengirim pesan dengan format:

```
🚀 SINYAL UPTREND DITEMUKAN

📊 BBCA.JK - Bank Central Asia
⏰ 2024-01-15 09:00:00

💰 Harga Saat Ini: Rp 10.500
🎯 Entry Point: Rp 10.500
🎯 Take Profit: Rp 10.950
📈 Potensi Profit: 4.29%

Konfirmasi Indikator:
✓ Harga di atas SMA20
✓ Golden Cross (SMA20 > SMA50)
✓ RSI sehat (65.2)
✓ MACD bullish
✓ Volume konfirmasi

🔻 Support: Rp 10.200
🔺 Resistance: Rp 11.000

⚠️ PERINGATAN: Potensi ARA (jika ada)

📌 Risk Management:
🛑 Stop Loss: Rp 10.185
⚖️ Risk/Reward: 1:1.43

⚠️ Disclaimer: Ini bukan saran investasi.
```

## ⚙️ Konfigurasi Lanjutan

Edit file `config.py` untuk:
- Mengubah periode data (`period`)
- Mengatur minimum profit percentage
- Mengaktifkan/menonaktifkan warning ARA
- Menambah/mengurangi list saham

## ⚠️ Disclaimer

**PENTING**: Bot ini hanya untuk membantu analisis teknikal. Bukan saran investasi profesional. Selalu lakukan:
- Analisis fundamental sendiri
- Risk management yang tepat
- Stop loss yang disiplin
- Jangan investasi lebih dari yang bisa Anda tanggung kerugiannya

## 🐛 Troubleshooting

### Bot tidak mengirim pesan
- Cek token dan chat ID di `config.py`
- Test koneksi dengan `python telegram_bot.py`
- Pastikan bot sudah di-start di Telegram (kirim `/start` ke bot Anda)

### Error instalasi ta-lib
- Library ini opsional, kode sudah menggunakan implementasi manual
- Hapus `ta-lib` dari requirements.txt jika bermasalah

### Data tidak mencukupi
- Beberapa saham baru mungkin belum memiliki data cukup
- Pastikan ticker menggunakan format yang benar (misal: `BBCA.JK`)

### Scheduler tidak jalan
- Pastikan timezone sudah benar (WIB)
- Cek apakah ada error di log
- Pastikan komputer/server tidak sleep/hibernate

## 📞 Support

Jika ada pertanyaan atau issue, silakan buat issue di repository ini.

## 📄 License

MIT License - Gunakan dengan risiko Anda sendiri.

---

**Happy Trading! 📈🚀**

python scheduler.py

/start: Welcomes and explains features.
/analisa [KODE]: Analyzes stock with Chart Image & Bollinger Bands narrative.
/setalert: Registers your Group for automatic daily signals (08:30 & 13:00).
/id: Checks Chat ID.


//mengonlinekan project
Railway.app (Free Tier)

Cocok untuk bot Telegram 24 jam tanpa terminal lokal.

Cara singkat:

Push project ke GitHub

git init
git add .
git commit -m "telegram bot"
git branch -M main
git remote add origin https://github.com/USERNAME/REPO.git
git push -u origin main


Daftar Railway

https://railway.app

Login pakai GitHub

New Project → Deploy from GitHub Repo

Set Start Command

python telegram_bot.py


Set Environment Variables
(isi dari config.py)

BOT_TOKEN=xxxx
CHAT_ID=xxxx


Done ✅
Bot akan online 24 jam (selama free quota belum habis).

📌 Catatan Free Tier

±500 jam / bulan

Cukup untuk bot Telegram non-heavy