# 📊 Scan Semua Saham IDX

Bot sekarang mendukung scan **semua saham** yang terdaftar di Bursa Efek Indonesia (IDX)!

**✅ Menggunakan yfinance 100%** - Semua data dan validasi menggunakan yfinance (gratis, tidak perlu API key)

## 🎯 Mode Scan

Bot memiliki 2 mode scan:

### 1. Mode Manual (Default)
- Scan hanya saham yang ada di list `STOCK_TICKERS` di `config.py`
- Cocok untuk fokus ke saham tertentu (blue chip, watchlist, dll)
- Lebih cepat dan hemat resources

### 2. Mode All IDX
- Scan **semua saham** yang terdaftar di IDX
- Menggunakan **yfinance** untuk validasi dan analisis (100% gratis)
- List ticker IDX lengkap dengan validasi menggunakan yfinance
- Cocok untuk menemukan peluang di seluruh pasar

## ⚙️ Cara Mengaktifkan Scan Semua Saham IDX

1. **Buka file `config.py`**

2. **Ubah `SCAN_MODE` menjadi `"all_idx"`:**
```python
SCAN_MODE = "all_idx"  # Ubah dari "manual" ke "all_idx"
```

3. **(Opsional) Konfigurasi tambahan:**
```python
SCAN_ALL_CONFIG = {
    "max_tickers_per_session": 100,  # Limit jumlah ticker per sesi (0 = unlimited)
    "use_cached_tickers": True,      # Gunakan cache untuk lebih cepat
    "cache_file": "idx_tickers.txt", # File cache
}
```

4. **Jalankan scheduler seperti biasa:**
```bash
python scheduler.py
```

## 📝 Catatan Penten

### Performa
- Scan semua saham IDX akan memakan waktu lebih lama (bisa 30-60 menit atau lebih)
- Bot akan otomatis membatasi jumlah ticker per sesi sesuai konfigurasi
- Untuk performa terbaik, gunakan `use_cached_tickers: True`

### Cache Ticker
- Bot akan menyimpan list ticker ke file `idx_tickers.txt`
- Cache akan di-refresh otomatis jika validasi dengan yfinance berhasil
- Jika cache tidak ada, bot akan menggunakan list ticker IDX lengkap dan memvalidasi dengan yfinance

### Rate Limiting
- Bot sudah memiliki delay 2 detik antar saham untuk menghindari rate limit
- Jika masih terjadi error, kurangi `max_tickers_per_session`

### Telegram Message Limit
- Telegram memiliki limit pengiriman pesan
- Jika terlalu banyak sinyal, bot mungkin akan di-rate limit oleh Telegram
- Gunakan `max_tickers_per_session` untuk mengontrol jumlah

## 🔄 Update List Ticker Manual

Jika ingin update list ticker secara manual:

```bash
python idx_ticker_fetcher.py
```

Ini akan:
1. Menggunakan list ticker IDX lengkap yang sudah ada
2. Memvalidasi semua ticker menggunakan yfinance (cek data 5 hari terakhir)
3. Menyimpan ticker yang valid ke `idx_tickers.txt`
4. Bot akan menggunakan file ini untuk scan

**Catatan**: Proses validasi menggunakan yfinance mungkin memakan waktu beberapa menit karena harus cek setiap ticker.

## 💡 Tips

1. **Untuk testing**: Gunakan mode manual dulu dengan beberapa saham
2. **Untuk production**: Aktifkan mode all_idx tapi set limit yang wajar (50-100 per sesi)
3. **Untuk fokus**: Gunakan mode manual dengan list saham pilihan Anda

## ⚠️ Warning

- Scan semua saham akan mengirim **banyak pesan** ke Telegram jika banyak yang uptrend
- Pastikan Anda siap menerima banyak notifikasi
- Pertimbangkan untuk menggunakan group/channel Telegram terpisah untuk sinyal

---

**Selamat mencoba scan semua saham IDX! 🚀**

