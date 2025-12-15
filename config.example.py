"""
File Contoh Konfigurasi Bot
Copy file ini menjadi config.py dan isi dengan data Anda
"""

# Telegram Bot Configuration
# Dapatkan token dari @BotFather di Telegram
TELEGRAM_TOKEN = "ISI_TOKEN_BOTFATHER_DISINI"

# Dapatkan Chat ID dari @userinfobot di Telegram
TELEGRAM_CHAT_ID = "ISI_CHAT_ID_DISINI"

# ==========================================
# KONFIGURASI SCAN SAHAM
# ==========================================

# Mode scan: "manual" atau "all_idx"
# - "manual": Scan hanya saham di list STOCK_TICKERS
# - "all_idx": Scan semua saham yang terdaftar di IDX (Bursa Efek Indonesia)
SCAN_MODE = "manual"  # Ubah ke "all_idx" untuk scan semua saham IDX

# List Saham yang akan di-scan setiap hari (jika SCAN_MODE = "manual")
# Format: kode saham dengan .JK untuk saham Indonesia
STOCK_TICKERS = [
    # Saham Blue Chip
    "BBCA.JK",  # Bank Central Asia
    "BBRI.JK",  # Bank Rakyat Indonesia
    "BMRI.JK",  # Bank Mandiri
    "BBNI.JK",  # Bank Negara Indonesia
    "TLKM.JK",  # Telkom Indonesia
    "ASII.JK",  # Astra International
    "GOTO.JK",  # GoTo Gojek Tokopedia
    "ANTM.JK",  # Aneka Tambang
    "ADRO.JK",  # Adaro Energy
    "UNVR.JK",  # Unilever Indonesia
    "ICBP.JK",  # Indofood CBP
    "INDF.JK",  # Indofood Sukses Makmur
    "KLBF.JK",  # Kalbe Farma
    "MDKA.JK",  # Merdeka Copper Gold
    "PGAS.JK",  # Perusahaan Gas Negara
    "PTBA.JK",  # Bukit Asam
    "SMGR.JK",  # Semen Indonesia
    "TOWR.JK",  # Tower Bersama Infrastructure
    "BRPT.JK",  # Barito Pacific
    "CPIN.JK",  # Charoen Pokphand Indonesia
    
    # Tambahkan ticker saham lain yang ingin di-scan
    # Format: "KODE.JK"
]


# Konfigurasi Analisis (Opsional)
ANALYSIS_CONFIG = {
    "period": "3mo",  # Periode data: 1mo, 3mo, 6mo, 1y, 2y, 5y
    "min_profit_pct": 2.0,  # Minimum profit percentage untuk dikirim
    "enable_ara_warning": True,  # Aktifkan warning untuk potensi ARA
}

# Konfigurasi untuk scan semua saham IDX (jika SCAN_MODE = "all_idx")
SCAN_ALL_CONFIG = {
    "max_tickers_per_session": 100,  # Maksimal ticker yang di-scan per sesi (0 = unlimited, untuk menghindari timeout)
    "use_cached_tickers": True,  # Gunakan cache ticker dari file (lebih cepat)
    "cache_file": "idx_tickers.txt",  # File untuk menyimpan cache ticker
}

