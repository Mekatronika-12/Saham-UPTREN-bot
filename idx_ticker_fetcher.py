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
        'AADI.JK', 'ABBA.JK', 'ABDA.JK', 'ABMM.JK', 'ACES.JK', 'ACRO.JK', 'ACST.JK', 'ADES.JK', 'ADHI.JK', 'ADMF.JK', 'ADMR.JK', 'ADRO.JK', 'AEGS.JK', 'AGRO.JK', 'AGRS.JK', 'AHAP.JK', 'AIMS.JK', 'AISA.JK', 'AKKU.JK', 'AKRA.JK', 'ALII.JK', 'ALKA.JK', 'ALMI.JK', 'ALTO.JK', 'AMAG.JK', 'AMAR.JK', 'AMIN.JK', 'AMMN.JK', 'AMRT.JK', 'ANDI.JK', 'ANTM.JK', 'APEX.JK', 'APLN.JK', 'AREA.JK', 'ARII.JK', 'ARNA.JK', 'ARTA.JK', 'ARTI.JK', 'ARTO.JK', 'ASBI.JK', 'ASDM.JK', 'ASII.JK', 'ASJT.JK', 'ASLI.JK', 'ASMI.JK', 'ASPR.JK', 'ASRI.JK', 'ASRM.JK', 'ASSA.JK', 'ASSY.JK', 'ATAP.JK', 'ATLA.JK', 'AWAN.JK', 'AXIO.JK', 'AYLS.JK', 'BABP.JK', 'BABY.JK', 'BACA.JK', 'BAIK.JK', 'BAPA.JK', 'BATA.JK', 'BATR.JK', 'BAYU.JK', 'BBCA.JK', 'BBHI.JK', 'BBKP.JK', 'BBLD.JK', 'BBMD.JK', 'BBNI.JK', 'BBRI.JK', 'BBTN.JK', 'BBYB.JK', 'BCIC.JK', 'BCIP.JK', 'BDKR.JK', 'BDMN.JK', 'BEKS.JK', 'BELI.JK', 'BELL.JK', 'BEST.JK', 'BFIN.JK', 'BGTG.JK', 'BIKA.JK', 'BINA.JK', 'BIRD.JK', 'BISI.JK', 'BJBR.JK', 'BJTM.JK', 'BKSL.JK', 'BKSW.JK', 'BLOG.JK', 'BLTA.JK', 'BLUE.JK', 'BMAS.JK', 'BMRI.JK', 'BMSR.JK', 'BNBA.JK', 'BNGA.JK', 'BNII.JK', 'BNLI.JK', 'BOLT.JK', 'BOSS.JK', 'BPII.JK', 'BPTR.JK', 'BRAM.JK', 'BREN.JK', 'BRIS.JK', 'BRMS.JK', 'BRNA.JK', 'BRPT.JK', 'BSDE.JK', 'BSIM.JK', 'BSSR.JK', 'BTON.JK', 'BTPN.JK', 'BTPS.JK', 'BUDI.JK', 'BUKA.JK', 'BUKK.JK', 'BULL.JK', 'BUMI.JK', 'BUVA.JK', 'BYAN.JK', 'CAMP.JK', 'CANI.JK', 'CASH.JK', 'CASS.JK', 'CBMF.JK', 'CCSI.JK', 'CDIA.JK', 'CEKA.JK', 'CFIN.JK', 'CGAS.JK', 'CHEK.JK', 'CHIP.JK', 'CITA.JK', 'CITY.JK', 'CLAY.JK', 'CLEO.JK', 'CMNP.JK', 'CMPP.JK', 'CMRY.JK', 'CNKO.JK', 'CNMA.JK', 'CNTX.JK', 'COCO.JK', 'COIN.JK', 'COWL.JK', 'CPIN.JK', 'CPRI.JK', 'CPRO.JK', 'CRSN.JK', 'CSAP.JK', 'CSIS.JK', 'CSMI.JK', 'CTBN.JK', 'CTRA.JK', 'CTTH.JK', 'CUAN.JK', 'DADA.JK', 'DART.JK', 'DATA.JK', 'DAYA.JK', 'DCII.JK', 'DEAL.JK', 'DEWA.JK', 'DGIK.JK', 'DILD.JK', 'DIVA.JK', 'DKHH.JK', 'DLTA.JK', 'DMAS.JK', 'DMMX.JK', 'DNAR.JK', 'DOID.JK', 'DPNS.JK', 'DPUM.JK', 'DSFI.JK', 'DSNG.JK', 'DSOT.JK', 'DSSA.JK', 'DUTI.JK', 'DWGL.JK', 'EAST.JK', 'ECII.JK', 'EDGE.JK', 'ELSA.JK', 'ELTY.JK', 'EMAS.JK', 'EMDE.JK', 'EMTK.JK', 'ENAK.JK', 'ENRG.JK', 'EPAC.JK', 'ESSA.JK', 'ESTA.JK', 'ESTI.JK', 'EXCL.JK', 'FAST.JK', 'FILM.JK', 'FIRE.JK', 'FKSW.JK', 'FMII.JK', 'FOOD.JK', 'FORE.JK', 'FORZ.JK', 'FREN.JK', 'FUTR.JK', 'GAMA.JK', 'GEMA.JK', 'GEMS.JK', 'GGRM.JK', 'GGRP.JK', 'GHON.JK', 'GIAA.JK', 'GJTL.JK', 'GLOB.JK', 'GLVA.JK', 'GMTD.JK', 'GOLD.JK', 'GOLF.JK', 'GOOD.JK', 'GOTO.JK', 'GPRA.JK', 'GPSO.JK', 'GRPH.JK', 'GSMF.JK', 'GTBO.JK', 'GTRA.JK', 'GWSA.JK', 'GZCO.JK', 'HAIS.JK', 'HALO.JK', 'HATM.JK', 'HDIT.JK', 'HDTX.JK', 'HEAL.JK', 'HELI.JK', 'HERO.JK', 'HEXA.JK', 'HILL.JK', 'HITS.JK', 'HKMU.JK', 'HOKI.JK', 'HOME.JK', 'HOMI.JK', 'HOTL.JK', 'HRTA.JK', 'HRUM.JK', 'HUMI.JK', 'HYGN.JK', 'IATA.JK', 'ICBP.JK', 'ICON.JK', 'IDEA.JK', 'IDPR.JK', 'IFII.JK', 'IFSH.JK', 'IIKP.JK', 'IKAI.JK', 'IKPM.JK', 'IMAS.JK', 'IMJS.JK', 'IMPC.JK', 'INAF.JK', 'INCF.JK', 'INCI.JK', 'INCO.JK', 'INDF.JK', 'INDO.JK', 'INDR.JK', 'INDS.JK', 'INDX.JK', 'INDY.JK', 'INET.JK', 'INKP.JK', 'INPP.JK', 'INTD.JK', 'INTP.JK', 'IPCC.JK', 'IPCM.JK', 'IPOL.JK', 'IPTV.JK', 'IRSX.JK', 'ITIC.JK', 'ITMA.JK', 'ITMG.JK', 'JAST.JK', 'JATI.JK', 'JAYA.JK', 'JECC.JK', 'JGLE.JK', 'JIHD.JK', 'JKON.JK', 'JKSW.JK', 'JMAS.JK', 'JPFA.JK', 'JRPT.JK', 'JSKY.JK', 'JSMR.JK', 'JSPT.JK', 'JTPE.JK', 'KAEF.JK', 'KARW.JK', 'KBAG.JK', 'KBLI.JK', 'KBLM.JK', 'KBLV.JK', 'KBRI.JK', 'KDSI.JK', 'KEJU.JK', 'KIAS.JK', 'KICI.JK', 'KIJA.JK', 'KINO.JK', 'KIOS.JK', 'KJA.JK', 'KJEN.JK', 'KKGI.JK', 'KLBF.JK', 'KMDS.JK', 'KMTR.JK', 'KOBX.JK', 'KOIN.JK', 'KOKA.JK', 'KONI.JK', 'KOPI.JK', 'KOTA.JK', 'KPAL.JK', 'KPAS.JK', 'KPIG.JK', 'KRAH.JK', 'KRAS.JK', 'KREN.JK', 'KUAS.JK', 'LABA.JK', 'LAJU.JK', 'LAND.JK', 'LCGP.JK', 'LCKM.JK', 'LEAD.JK', 'LFLO.JK', 'LIFE.JK', 'LINK.JK', 'LION.JK', 'LIVE.JK', 'LMAS.JK', 'LMAX.JK', 'LMPI.JK', 'LMSH.JK', 'LOKK.JK', 'LOPI.JK', 'LPCK.JK', 'LPKR.JK', 'LPLI.JK', 'LPPS.JK', 'LRNA.JK', 'LSIP.JK', 'LUCK.JK', 'LUCY.JK', 'MABA.JK', 'MAGP.JK', 'MAHA.JK', 'MAIN.JK', 'MAMI.JK', 'MANG.JK', 'MAPA.JK', 'MAPB.JK', 'MAPI.JK', 'MARK.JK', 'MASA.JK', 'MAYA.JK', 'MBAI.JK', 'MBMA.JK', 'MBSS.JK', 'MBTO.JK', 'MCAS.JK', 'MCOL.JK', 'MCOR.JK', 'MDKA.JK', 'MDKI.JK', 'MDLA.JK', 'MDLN.JK', 'MEDC.JK', 'MEDS.JK', 'MEGA.JK', 'MEJA.JK', 'MENN.JK', 'MERI.JK', 'MERK.JK', 'META.JK', 'MFIN.JK', 'MFMI.JK', 'MGLV.JK', 'MGNA.JK', 'MGRO.JK', 'MHKI.JK', 'MIDI.JK', 'MINA.JK', 'MIRA.JK', 'MITI.JK', 'MKAP.JK', 'MKNT.JK', 'MKPI.JK', 'MLBI.JK', 'MLIA.JK', 'MLPL.JK', 'MLPT.JK', 'MMIX.JK', 'MMLP.JK', 'MMSC.JK', 'MMSL.JK', 'MNCN.JK', 'MOLI.JK', 'MORI.JK', 'MPIX.JK', 'MPOW.JK', 'MPPA.JK', 'MPRO.JK', 'MPXL.JK', 'MRAT.JK', 'MREI.JK', 'MSIE.JK', 'MSJA.JK', 'MSKY.JK', 'MTDL.JK', 'MTEL.JK', 'MTFN.JK', 'MTLA.JK', 'MTSM.JK', 'MTWI.JK', 'MUTU.JK', 'MYOH.JK', 'MYRX.JK', 'MYTX.JK', 'NASA.JK', 'NASI.JK', 'NATO.JK', 'NCKL.JK', 'NELY.JK', 'NETV.JK', 'NFCX.JK', 'NICE.JK', 'NICK.JK', 'NICL.JK', 'NIKL.JK', 'NINE.JK', 'NIPS.JK', 'NIRO.JK', 'NISP.JK', 'NOBU.JK', 'NPGF.JK', 'NRCA.JK', 'NUSA.JK', 'NVRA.JK', 'NZIA.JK', 'OASA.JK', 'OBMD.JK', 'OILS.JK', 'OKAS.JK', 'OLIV.JK', 'OMRE.JK', 'OPMS.JK', 'PACK.JK', 'PADI.JK', 'PALM.JK', 'PAMG.JK', 'PANI.JK', 'PANR.JK', 'PANS.JK', 'PART.JK', 'PBID.JK', 'PBRX.JK', 'PBSA.JK', 'PCAR.JK', 'PDES.JK', 'PDPP.JK', 'PEGE.JK', 'PEHA.JK', 'PEVE.JK', 'PGAS.JK', 'PGEO.JK', 'PGJO.JK', 'PGLI.JK', 'PGUN.JK', 'PICO.JK', 'PIPA.JK', 'PJAA.JK', 'PJHB.JK', 'PKPK.JK', 'PLAN.JK', 'PLAS.JK', 'PLIN.JK', 'PMJS.JK', 'PMMP.JK', 'PMUI.JK', 'PNBN.JK', 'PNBS.JK', 'PNGO.JK', 'PNIN.JK', 'PNLF.JK', 'PNSE.JK', 'POLA.JK', 'POLI.JK', 'POLL.JK', 'POLU.JK', 'POLY.JK', 'POOL.JK', 'PORT.JK', 'POSA.JK', 'POWR.JK', 'PPGL.JK', 'PPRE.JK', 'PPRI.JK', 'PPRO.JK', 'PRAS.JK', 'PRAY.JK', 'PRDA.JK', 'PRIM.JK', 'PSAB.JK', 'PSAT.JK', 'PSDN.JK', 'PSGO.JK', 'PSKT.JK', 'PSSI.JK', 'PTBA.JK', 'PTDU.JK', 'PTIS.JK', 'PTMP.JK', 'PTMR.JK', 'PTPP.JK', 'PTPS.JK', 'PTPW.JK', 'PTRO.JK', 'PTSN.JK', 'PTSP.JK', 'PUDP.JK', 'PURA.JK', 'PURE.JK', 'PURI.JK', 'PWON.JK', 'PYFA.JK', 'PZA.JK', 'RAAM.JK', 'RAFI.JK', 'RAJA.JK', 'RALS.JK', 'RANC.JK', 'RBMS.JK', 'RCCC.JK', 'RDTX.JK', 'REAL.JK', 'RELF.JK', 'RELI.JK', 'RGAS.JK', 'RICY.JK', 'RIGS.JK', 'RIMO.JK', 'RISE.JK', 'RLCO.JK', 'RMKO.JK', 'ROCK.JK', 'RODA.JK', 'RONY.JK', 'ROTI.JK', 'RSCH.JK', 'RSGK.JK', 'RUIS.JK', 'RUNS.JK', 'SAFE.JK', 'SAGE.JK', 'SAGR.JK', 'SAME.JK', 'SAMF.JK', 'SANT.JK', 'SAPX.JK', 'SATU.JK', 'SBAT.JK', 'SBMA.JK', 'SCBD.JK', 'SCCO.JK', 'SCMA.JK', 'SCNP.JK', 'SCPI.JK', 'SDMU.JK', 'SDPC.JK', 'SDRA.JK', 'SEMA.JK', 'SFAN.JK', 'SGCU.JK', 'SGER.JK', 'SHID.JK', 'SHIP.JK', 'SICO.JK', 'SIDO.JK', 'SILO.JK', 'SIMA.JK', 'SIMP.JK', 'SINI.JK', 'SIPD.JK', 'SKBM.JK', 'SKLT.JK', 'SKRN.JK', 'SKYB.JK', 'SLIS.JK', 'SMAR.JK', 'SMBR.JK', 'SMDM.JK', 'SMDR.JK', 'SMGA.JK', 'SMGR.JK', 'SMIL.JK', 'SMLE.JK', 'SMMT.JK', 'SMRA.JK', 'SMSM.JK', 'SNA.JK', 'SOCI.JK', 'SOFA.JK', 'SOHO.JK', 'SOLA.JK', 'SOSS.JK', 'SOTS.JK', 'SOUL.JK', 'SPMA.JK', 'SPRE.JK', 'SPTO.JK', 'SQMI.JK', 'SRAJ.JK', 'SRIL.JK', 'SRSN.JK', 'SRTG.JK', 'SSIA.JK', 'SSMS.JK', 'SSTM.JK', 'STAA.JK', 'STAR.JK', 'STRK.JK', 'STTP.JK', 'SUGI.JK', 'SULI.JK', 'SUNI.JK', 'SUPA.JK', 'SUPR.JK', 'SURE.JK', 'SWAT.JK', 'TAMU.JK', 'TAPG.JK', 'TARA.JK', 'TAXI.JK', 'TAYS.JK', 'TBIG.JK', 'TBLA.JK', 'TCID.JK', 'TCPI.JK', 'TDPM.JK', 'TEBE.JK', 'TECH.JK', 'TEK.JK', 'TELE.JK', 'TFAS.JK', 'TGKA.JK', 'TGRA.JK', 'TIFA.JK', 'TINS.JK', 'TIRA.JK', 'TIRT.JK', 'TKIM.JK', 'TLDN.JK', 'TLKM.JK', 'TMAS.JK', 'TMPO.JK', 'TNCA.JK', 'TOBA.JK', 'TOOL.JK', 'TOPS.JK', 'TOSK.JK', 'TOTL.JK', 'TOYS.JK', 'TPIA.JK', 'TPMA.JK', 'TRAM.JK', 'TRGU.JK', 'TRIL.JK', 'TRIM.JK', 'TRIN.JK', 'TRIO.JK', 'TRIS.JK', 'TRJA.JK', 'TRON.JK', 'TRUE.JK', 'TRUK.JK', 'TRUS.JK', 'TSPC.JK', 'TUGU.JK', 'TYRE.JK', 'UANG.JK', 'UCID.JK', 'UDNG.JK', 'UFOE.JK', 'ULTJ.JK', 'UNIC.JK', 'UNIT.JK', 'UNSP.JK', 'UNTD.JK', 'UNTR.JK', 'UNVR.JK', 'URBN.JK', 'UVCR.JK', 'VAST.JK', 'VERN.JK', 'VICI.JK', 'VICO.JK', 'VINS.JK', 'VISI.JK', 'VIVA.JK', 'VKTR.JK', 'VOKS.JK', 'VRNA.JK', 'WEHA.JK', 'WGSH.JK', 'WICO.JK', 'WIDI.JK', 'WIFI.JK', 'WIIM.JK', 'WIKA.JK', 'WINR.JK', 'WINS.JK', 'WIRG.JK', 'WMPP.JK', 'WMUU.JK', 'WOMF.JK', 'WOOD.JK', 'WOWS.JK', 'WSBP.JK', 'WSKT.JK', 'WTON.JK', 'YELO.JK', 'YPAS.JK', 'YULE.JK', 'ZINC.JK', 'ZONE.JK', 'ZYRX.JK'
    ]
    return tickers


def save_tickers_to_file(tickers: List[str], filename: str = "idx_tickers.txt"):
    """Menyimpan list ticker ke file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            for ticker in tickers:
                f.write(f"{ticker}\n")
        logger.info(f"Ticker list disimpan ke {filename}")
    except Exception as e:
        logger.error(f"Error menyimpan ticker: {str(e)}")


def load_tickers_from_file(filename: str = "idx_tickers.txt") -> List[str]:
    """Load list ticker dari file"""
    try:
        if not os.path.exists(filename):
            return []
            
        tickers = []
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Validation: Ignore empty lines or lines that are suspiciously long (likely corrupted)
                if line and len(line) < 15: 
                    tickers.append(line)
        
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
