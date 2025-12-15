# 🚀 Quick Start Guide

Panduan cepat untuk menjalankan bot dalam 5 menit!

## Langkah 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Langkah 2: Setup Telegram

1. Buka Telegram, cari **@BotFather**
2. Kirim: `/newbot`
3. Ikuti instruksi, simpan **TOKEN** yang diberikan
4. Cari **@userinfobot** di Telegram
5. Kirim pesan ke bot tersebut, dapatkan **CHAT ID** (angka)

## Langkah 3: Konfigurasi

Buka file `config.py` dan isi:

```python
TELEGRAM_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"  # Token dari BotFather
TELEGRAM_CHAT_ID = "123456789"  # Chat ID dari @userinfobot
```

## Langkah 4: Test Bot

```bash
python telegram_bot.py
```

Jika berhasil, Anda akan menerima pesan dari bot di Telegram!

## Langkah 5: Jalankan Scheduler

```bash
python scheduler.py
```

Bot akan otomatis mengirim sinyal setiap hari:
- Jam 09:00 WIB (Sesi 1 - Pagi)
- Jam 13:30 WIB (Sesi 2 - Siang)

---

## 📝 Catatan Penting

- Pastikan komputer/server tidak sleep/hibernate agar scheduler tetap jalan
- Untuk production, gunakan VPS atau cloud server
- Bot akan scan semua saham di list `STOCK_TICKERS` di `config.py`

## 🔧 Troubleshooting

**Bot tidak mengirim pesan?**
- Pastikan token dan chat ID benar
- Pastikan bot sudah di-start (kirim `/start` ke bot Anda di Telegram)

**Error instalasi?**
- Pastikan Python versi 3.8 atau lebih baru
- Gunakan virtual environment: `python -m venv venv`

---

**Selamat! Bot Anda sudah siap digunakan! 🎉**

