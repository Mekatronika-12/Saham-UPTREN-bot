import yfinance as yf
import pandas as pd
from typing import List, Set, Optional
import logging
import time
import requests
from bs4 import BeautifulSoup
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from datetime import datetime

logger = logging.getLogger(__name__)


def validate_ticker_with_yfinance(ticker: str) -> bool:
    """
    Validasi apakah ticker valid menggunakan yfinance
    """
    try:
        stock = yf.Ticker(ticker)
        # Quick validation - coba dapatkan info dasar
        # Gunakan info.get() untuk menghindari error jika key tidak ada
        info = stock.info
        if info and ('symbol' in info or 'longName' in info or 'shortName' in info or 'currentPrice' in info):
            return True
        
        # Fallback: check history
        hist = stock.history(period="1d")
        if not hist.empty:
            return True
            
        return False
    except Exception as e:
        return False


def fetch_tickers_from_wikipedia() -> List[str]:
    """
    Scrape daftar emiten dari Wikipedia Indonesia.
    URL: https://id.wikipedia.org/wiki/Daftar_perusahaan_yang_tercatat_di_Bursa_Efek_Indonesia
    """
    url = "https://id.wikipedia.org/wiki/Daftar_perusahaan_yang_tercatat_di_Bursa_Efek_Indonesia"
    logger.info(f"Mencoba mengambil ticker dari {url}...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        tickers = set()
        
        # Cari semua tabel
        tables = soup.find_all('table', {'class': 'wikitable'})
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if not cols:
                    continue
                
                # Biasanya kode emiten ada di kolom pertama atau kedua
                # Kita cari cell yang berisi pattern 4 huruf kapital
                for col in cols[:2]: # Cek 2 kolom pertama saja cukup
                    text = col.get_text(strip=True)
                    match = re.search(r'\\b[A-Z]{4}\\b', text)
                    if match:
                        code = match.group(0)
                        tickers.add(f"{code}.JK")
                        break
        
        result = sorted(list(tickers))
        logger.info(f"Berhasil menemukan {len(result)} ticker dari Wikipedia")
        return result
        
    except Exception as e:
        logger.error(f"Gagal mengambil dari Wikipedia: {str(e)}")
        return []


def fetch_tickers_from_github() -> List[str]:
    """
    Mengambil ticker dari sumber GitHub yang terpercaya.
    """
    # URL github yang mungkin masih aktif atau reliable
    sources = [
        "https://raw.githubusercontent.com/open-finance/indonesia-stock-tickers/master/tickers.json", # Alternative source if exists
        # Menghapus source yang dead/404
    ]
    
    logger.info("Mencoba mengambil ticker dari GitHub repositories...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    found_tickers = set()

    # Jika source kosong, return empty list
    if not sources:
        return []

    for url in sources:
        try:
            logger.info(f"Mencoba fetch dari: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                text = response.text
                matches = re.findall(r'\\b[A-Z]{4}\\b', text)
                
                for match in matches:
                    found_tickers.add(f"{match}.JK")
                
                if len(found_tickers) > 500:
                    logger.info(f"Berhasil mendapatkan {len(found_tickers)} ticker dari {url}")
                    return sorted(list(found_tickers))
        except Exception as e:
            logger.warning(f"Gagal fetch dari {url}: {e}")
            continue
            
    return []


def get_recent_ipos() -> List[str]:
    """
    List manual ticker IPO terbaru (2023-2025) untuk memastikan tidak terlewat
    karena scraping source mungkin belum update.
    """
    latest_ipos = [
        # 2025 IPOs (Confirmed & Pipeline)
        "RLCO.JK", "PJHB.JK", "EMAS.JK", "BLOG.JK", "MERI.JK", 
        "CHEK.JK", "PMUI.JK", "COIN.JK", "CDIA.JK", "ASPR.JK", 
        "SUPA.JK", "PSAT.JK", "DKHH.JK", "MDLA.JK", "FORE.JK",
        
        # 2024 & Late 2023
        "ASLI.JK", "CGAS.JK", "NICE.JK", "MSJA.JK", "SMLE.JK", "ACRO.JK", "MANG.JK", "GRPH.JK", 
        "SMGA.JK", "UNTD.JK", "TOSK.JK", "MPIX.JK", "ALII.JK", "MKAP.JK", "MEJA.JK", "LIVE.JK", 
        "HYGN.JK", "BAIK.JK", "VISI.JK", "AREA.JK", "MHKI.JK", "ATLA.JK", "DATA.JK", "SOLA.JK", 
        "BATR.JK", "SPRE.JK", "PART.JK", "AADI.JK",
        
        # 2023 (Major ones)
        "BREN.JK", "CUAN.JK", "AMMN.JK", "VKTR.JK", "RAAM.JK", "BDKR.JK", "GTRA.JK", 
        "AWAN.JK", "INET.JK", "IRSX.JK", "MPXL.JK", "PPRI.JK", "SMIL.JK", "TYRE.JK", 
        "WIDI.JK", "CRSN.JK", "HUMI.JK", "LMAX.JK", "MAHA.JK", "RMKO.JK", "CNMA.JK", 
        "LOKK.JK", "MUTU.JK", "BABY.JK", "HATM.JK", "AEGS.JK", "RSCH.JK", "FUTR.JK", 
        "HILL.JK", "LAJU.JK", "PEVE.JK", "PACK.JK", "VAST.JK", "HALO.JK", "CHIP.JK", 
        "STRK.JK", "KOKA.JK", "IKPM.JK", "LOPI.JK", "UDNG.JK", "RGAS.JK"
    ]
    return latest_ipos

def get_all_idx_tickers() -> List[str]:
    """
    Mendapatkan semua ticker IDX, prioritas:
    1. Scraping Wikipedia
    2. Recent IPOs (Hardcoded)
    3. Existing File (jika ada, sebagai baseline)
    """
    all_tickers_set = set()
    
    # 1. Load existing file first to keep what we have
    existing = load_tickers_from_file()
    if existing:
        all_tickers_set.update(existing)
        
    # 2. Coba Wikipedia
    wiki_tickers = fetch_tickers_from_wikipedia()
    if wiki_tickers:
        all_tickers_set.update(wiki_tickers)
    
    # 3. Add Recent IPOs (Ensure they are present)
    recent = get_recent_ipos()
    all_tickers_set.update(recent)
    
    # 4. Fallback Comprehensive List if total is too small
    if len(all_tickers_set) < 600:
        logger.warning("Jumlah ticker sedikit, menambahkan list comprehensive manual...")
        manual = get_idx_tickers_from_yfinance_comprehensive()
        all_tickers_set.update(manual)
        
    # Final cleanup
    final_tickers = sorted(list(all_tickers_set))
    logger.info(f"Total ticker final: {len(final_tickers)}")
    
    return final_tickers


def get_idx_tickers_from_yfinance_comprehensive() -> List[str]:
    """
    List manual ticker IDX yang diperluas.
    Fallback jika scraping gagal.
    """
    tickers = [
        "BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK", "ASII.JK", "TLKM.JK", "MDKA.JK", "UNVR.JK", "KLBF.JK", "GOTO.JK",
        "AMMN.JK", "BREN.JK", "CUAN.JK", "MBMA.JK", "PGEO.JK", "NCKL.JK", "VKTR.JK", "RAAM.JK", "BDKR.JK", "GTRA.JK",
        "AWAN.JK", "INET.JK", "IRSX.JK", "MPXL.JK", "PPRI.JK", "SMIL.JK", "TYRE.JK", "WIDI.JK", "CRSN.JK", "GRPH.JK",
        "HUMI.JK", "LMAX.JK", "MAHA.JK", "RMKO.JK", "CNMA.JK", "LOKK.JK", "MUTU.JK", "BABY.JK", "HATM.JK", "AEGS.JK",
        "MSJA.JK", "RSCH.JK", "FUTR.JK", "HILL.JK", "LAJU.JK", "PEVE.JK", "PACK.JK", "VAST.JK", "HALO.JK", "CHIP.JK",
        # Tambahkan emiten umum lainnya untuk fallback
        "ADRO.JK", "APLN.JK", "ANTM.JK", "BRPT.JK", "CPIN.JK", "ELSA.JK", "EXCL.JK", "GGRM.JK", "HMSP.JK", "ICBP.JK",
        "INDF.JK", "INKP.JK", "INTP.JK", "ISAT.JK", "ITMG.JK", "JPFA.JK", "JSMR.JK", "LPPF.JK", "MEDC.JK", "MIKA.JK",
        "MNCN.JK", "PGAS.JK", "PTBA.JK", "PTPP.JK", "SCMA.JK", "SMGR.JK", "TBIG.JK", "TINS.JK", "TPIA.JK", "UNTR.JK",
        "WIKA.JK", "WSKT.JK", "ADHI.JK", "BSDE.JK", "CTRA.JK", "PWON.JK", "SMRA.JK", "ACES.JK", "AKRA.JK", "BMTR.JK"
    ]
    return tickers


def save_tickers_to_file(tickers: List[str], filename: str = "idx_tickers.txt"):
    """Menyimpan list ticker ke file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            for ticker in tickers:
                f.write(f"{ticker}\\n")
        logger.info(f"Ticker list disimpan ke {filename}")
    except Exception as e:
        logger.error(f"Error menyimpan ticker: {str(e)}")


def load_tickers_from_file(filename: str = "idx_tickers.txt") -> List[str]:
    """Load list ticker dari file"""
    try:
        if not os.path.exists(filename):
            return []
            
        with open(filename, 'r', encoding='utf-8') as f:
            tickers = [line.strip() for line in f if line.strip()]
        
        return tickers
    except Exception as e:
        logger.error(f"Error loading ticker: {str(e)}")
        return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Mengupdate database ticker IDX...")
    
    tickers = get_all_idx_tickers()
    
    print(f"Total ticker ditemukan: {len(tickers)}")
    
    if tickers:
        save_tickers_to_file(tickers)
        print(f"✅ Ticker list berhasil diupdate ({len(tickers)} emiten) ke idx_tickers.txt")
    else:
        print("❌ Gagal mendapatkan ticker.")
