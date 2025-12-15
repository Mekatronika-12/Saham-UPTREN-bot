"""
Modul Analisis Saham untuk Deteksi Uptrend
Menggunakan kombinasi indikator teknikal terbaik
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Optional, Tuple


class StockAnalyzer:
    """Kelas untuk menganalisis saham dan mendeteksi uptrend"""
    
    def __init__(self):
        self.min_data_days = 60  # Minimum data yang diperlukan (increased for ADX)

    def get_tick_size(self, price: float) -> int:
        """Mendapatkan fraksi harga (tick size) sesuai aturan BEI"""
        if price < 200:
            return 1
        elif price < 500:
            return 2
        elif price < 2000:
            return 5
        elif price < 5000:
            return 10
        else:
            return 25

    def add_ticks(self, price: float, ticks: int) -> float:
        """Menambahkan n ticks ke harga"""
        current_price = int(price)
        for _ in range(abs(ticks)):
            tick = self.get_tick_size(current_price)
            if ticks > 0:
                current_price += tick
            else:
                current_price -= tick
        return float(current_price)
        
    def calculate_sma(self, data: pd.Series, period: int) -> pd.Series:
        """Menghitung Simple Moving Average"""
        return data.rolling(window=period).mean()
    
    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """Menghitung Exponential Moving Average"""
        return data.ewm(span=period, adjust=False).mean()
    
    def calculate_rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """Menghitung Relative Strength Index"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_macd(self, data: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Menghitung MACD (Moving Average Convergence Divergence)"""
        ema12 = self.calculate_ema(data, 12)
        ema26 = self.calculate_ema(data, 26)
        macd_line = ema12 - ema26
        signal_line = self.calculate_ema(macd_line, 9)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Menghitung Average True Range untuk volatilitas"""
        high_low = high - low
        high_close = np.abs(high - close.shift())
        low_close = np.abs(low - close.shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        
        # Wilder's Smoothing for ATR seems more standard, but simple rolling mean is often used too.
        # Let's use Wilder's method (EMA with alpha=1/n) for consistency if we were stricter, 
        # but here we stick to simple rolling to match previous method or improve slightly.
        # Using rolling mean as previous implementation:
        atr = true_range.rolling(window=period).mean()
        return atr

    def calculate_adx(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Menghitung Average Directional Index (ADX)"""
        # 1. Calculate True Range (TR)
        high_low = high - low
        high_close = np.abs(high - close.shift())
        low_close = np.abs(low - close.shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        tr = ranges.max(axis=1)

        # 2. Calculate Directional Movement (+DM, -DM)
        up_move = high - high.shift()
        down_move = low.shift() - low
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
        
        plus_dm = pd.Series(plus_dm, index=high.index)
        minus_dm = pd.Series(minus_dm, index=high.index)

        # 3. Smooth TR, +DM, -DM (Wilder's Smoothing usually, we use EMA approximation alpha=1/period)
        # Using ewm(alpha=1/period, adjust=False) matches Wilder's
        tr_smooth = tr.ewm(alpha=1/period, adjust=False).mean()
        plus_dm_smooth = plus_dm.ewm(alpha=1/period, adjust=False).mean()
        minus_dm_smooth = minus_dm.ewm(alpha=1/period, adjust=False).mean()

        # 4. Calculate +DI and -DI
        plus_di = 100 * (plus_dm_smooth / tr_smooth)
        minus_di = 100 * (minus_dm_smooth / tr_smooth)

        # 5. Calculate DX
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)

        # 6. Calculate ADX (Smooth DX)
        adx = dx.ewm(alpha=1/period, adjust=False).mean()
        return adx, plus_di, minus_di
    
    def calculate_fibonacci(self, data: pd.DataFrame, period: int = 60) -> Dict:
        """
        Menghitung level Fibonacci Retracement & Extension
        berdasarkan Swing Low & Swing High terakhir.
        """
        # Scan data terakhir
        recent_data = data.tail(period)
        
        # Cari Highest High (Swing High)
        high_idx = recent_data['High'].idxmax()
        swing_high = recent_data['High'].max()
        
        # Cari Lowest Low SEBELUM Swing High (untuk tarikan garis Uptrend valid)
        # Jika swing high adalah candle pertama, kita cari low periode sebelumnya.
        # Simplifikasi: Cari min low di window data, prioritaskan low yang terjadi sebelum high.
        
        # Slice data up to swing high
        data_up_to_high = recent_data.loc[:high_idx]
        if len(data_up_to_high) < 5:
            # Jika High baru saja terjadi, gunakan Low periode penuh
            swing_low = recent_data['Low'].min()
        else:
            swing_low = data_up_to_high['Low'].min()
            
        diff = swing_high - swing_low
        
        levels = {
            "swing_high": swing_high,
            "swing_low": swing_low,
            "fib_0": swing_high,            # 0% (High)
            "fib_0236": swing_high - (0.236 * diff),
            "fib_0382": swing_high - (0.382 * diff),
            "fib_05": swing_high - (0.5 * diff),
            "fib_0618": swing_high - (0.618 * diff), # Golden Ratio (Best Entry)
            "fib_0786": swing_high - (0.786 * diff),
            "fib_1": swing_low,            # 100% (Low)
            "fib_ext_1272": swing_high + (0.272 * diff),
            "fib_ext_1618": swing_high + (0.618 * diff) # Target TP Ideal
        }
        return levels

    def detect_candlestick(self, open_p, high_p, low_p, close_p, prev_close) -> str:
        """Deteksi pola candlestick sederhana"""
        body = abs(close_p - open_p)
        upper_shadow = high_p - max(close_p, open_p)
        lower_shadow = min(close_p, open_p) - low_p
        
        # Hammer (Bullish Reversal / Strength)
        if lower_shadow > body * 2 and upper_shadow < body * 0.5:
             return "HAMMER (Bullish)"
        
        # Marubozu (Strong Momentum)
        if body > (high_p - low_p) * 0.8:
             return "FULL POWER (Marubozu)"
             
        # Doji (Indecision)
        if body <= (high_p - low_p) * 0.1:
             return "DOJI (Wait)"
             
        return "NORMAL"

    def calculate_support_resistance(self, data: pd.DataFrame, lookback: int = 20) -> Tuple[float, float]:
        """Menghitung level Support dan Resistance"""
        recent_data = data.tail(lookback)
        resistance = recent_data['High'].max()
        support = recent_data['Low'].min()
        return support, resistance
    
    def calculate_volume_sma(self, volume: pd.Series, period: int = 20) -> pd.Series:
        """Menghitung Volume Moving Average"""
        return volume.rolling(window=period).mean()
    
    def is_uptrend(self, data: pd.DataFrame) -> Tuple[bool, Dict]:
        """
        Mendeteksi apakah saham dalam kondisi uptrend KUAT.
        Kriteria diperketat untuk mengurangi false signal.
        """
        if len(data) < self.min_data_days:
            return False, {"reason": "Data tidak mencukupi"}
        
        close = data['Close']
        high = data['High']
        low = data['Low']
        volume = data['Volume']
        
        # 1. SMA Analysis
        sma20 = self.calculate_sma(close, 20)
        sma50 = self.calculate_sma(close, 50)
        sma200 = self.calculate_sma(close, 200) # Optional long term context
        
        # 2. RSI Analysis
        rsi = self.calculate_rsi(close, 14)
        
        # 3. MACD Analysis
        macd_line, signal_line, histogram = self.calculate_macd(close)
        
        # 4. Volume Analysis
        volume_sma = self.calculate_volume_sma(volume, 20)

        # 5. ADX Analysis (Trend Strength)
        adx, plus_di, minus_di = self.calculate_adx(high, low, close, 14)
        
        # Get latest values
        latest_close = close.iloc[-1]
        latest_sma20 = sma20.iloc[-1]
        latest_sma50 = sma50.iloc[-1]
        
        latest_rsi = rsi.iloc[-1]
        latest_macd = macd_line.iloc[-1]
        latest_signal = signal_line.iloc[-1]
        latest_histogram = histogram.iloc[-1]
        prev_histogram = histogram.iloc[-2]
        prev2_histogram = histogram.iloc[-3]
        
        latest_volume = volume.iloc[-1]
        latest_volume_sma = volume_sma.iloc[-1]
        
        latest_adx = adx.iloc[-1]
        
        # === STRATEGY: MACD REVERSAL (Video Based) ===
        # Mencari saham yang akan Uptrend menggunakan MACD
        # Kunci: Histogram naik (Momentum Bearish melemah atau Bullish menguat)
        
        is_macd_reversal = False
        reversal_reason = ""
        
        # 1. Bearish Weakening (Merah Tua -> Merah Muda/Pendek)
        if prev_histogram < 0 and latest_histogram < 0 and latest_histogram > prev_histogram:
             is_macd_reversal = True
             reversal_reason = "MACD Histogram Bearish Melemah (Early Signal)"
             
        # 2. Bullish Crossover (Merah -> Hijau)
        elif prev_histogram < 0 and latest_histogram > 0:
             is_macd_reversal = True
             reversal_reason = "MACD Golden Cross (Konfirmasi Bullish)"
             
        # 3. Bullish Strengthening (Hijau -> Hijau Tinggi)
        elif latest_histogram > 0 and latest_histogram > prev_histogram:
             is_macd_reversal = True
             reversal_reason = "MACD Momentum Bullish Menguat"

        # === FILTERING ===
        reasons = []
        is_strong_uptrend = True
        
        
        # Calculate Price Change Today
        price_change_pct = (latest_close - close.iloc[-2]) / close.iloc[-2] * 100
        
        # === CRITICAL FIX: Calculate vol_ratio HERE before using it ===
        vol_ratio = latest_volume / latest_volume_sma if latest_volume_sma > 0 else 1
        
        # === 0. DETEKSI NAIK KENCANG (SPIKE) ===
        # Request User: Kirim sinyal juga jika harga naik kencang (walau trend belum perfect)
        is_spike = False
        if price_change_pct > 5 and vol_ratio > 1.5:
             is_spike = True
             reasons.append(f"🚀 HARGA NAIK KENCANG (+{price_change_pct:.1f}%)")
             reasons.append(f"⚡ Volume Meledak ({vol_ratio:.1f}x Rata2)")
             
             # Bypass MA Filters for Spike
             # But still check basic sanity (not penny stock dying)
             pass 
        else:
             # Normal Filter (Strict Uptrend)
             # Base Filter: Harga tidak boleh di bawah SMA50 terlalu jauh (Downtrend akut skip dulu)
             if latest_close < latest_sma50 * 0.95:
                  return False, {"reason": "Trend Masih Bearish Parah (<SMA50)"}

             # Kriteria Video: Prioritas MACD (Jika bukan Spike)
             if not is_macd_reversal and not (latest_macd > latest_signal):
                  return False, {"reason": "MACD Momentum Negatif / Tidak ada reversal"}
        
        if is_macd_reversal and not is_spike:
             reasons.append(f"✓ {reversal_reason}")
        elif not is_spike:
             reasons.append("✓ MACD > Signal (Trend Positif)")
        
        # Support Filters
        if latest_rsi > 80:
             return False, {"reason": "RSI Overbought (>80)"}
        
        reasons.append(f"✓ RSI Aman ({latest_rsi:.1f})")

        # Volume Confirmation
        # Tidak wajib breakout, tapi minimal ada transaksi
        if latest_volume < latest_volume_sma * 0.5:
             # Volume sepi banget, skip
             pass # Or strict? Let's be lenient for reversal pattern
        else:
             reasons.append("✓ Volume Aktif")

        # ADX Check (Optional for Reversal, strict for Trend Following)
        # Untuk strategi "Mencari YANG AKAN uptrend", ADX mungkin masih rendah.
        # Jadi kita tidak reject jika ADX rendah, tapi kita catat.
        if latest_adx > 20:
             reasons.append(f"✓ Trend Mulai Terbentuk (ADX={latest_adx:.1f})")

        # === SCORING SYSTEM (Refined for MACD Focus) ===
        score = 60
        
        # 1. MACD Quality (Big Weight)
        if prev_histogram < 0 and latest_histogram > 0: # Golden Cross
            score += 25
        elif latest_histogram > prev_histogram and latest_histogram > prev2_histogram: # Consistent growth
            score += 15
            
        # 2. Volume Spike
        # vol_ratio is calculated above (CRITICAL FIX)
        if vol_ratio > 1.2:
            score += 10
            
        # 3. Early Trend Bonus
        if 20 < latest_adx < 40:
             score += 5 # Sweet spot for entry
             
        analysis = {
            "score": score,
            "reasons": reasons,
            "indicators": {
                "close": latest_close,
                "sma20": latest_sma20,
                "sma50": latest_sma50,
                "rsi": latest_rsi,
                "macd": latest_macd,
                "signal": latest_signal,
                "histogram": latest_histogram,
                "adx": latest_adx,
                "volume_ratio": vol_ratio
            }
        }
        
        return True, analysis
    
    def is_bsjp(self, data: pd.DataFrame) -> bool:
        """
        Screening BSJP (Beli Sore Jual Pagi) based on specific criteria:
        1. 1 Day Price Returns (%) > 1
        2. Volume > 2 * Volume MA 20
        3. Volume > 2 * Previous Volume
        4. Value > 10 Billion
        5. Previous Price < Price (Green Candle)
        6. Price > Price MA 10
        """
        if len(data) < 25: return False
        
        close = data['Close']
        volume = data['Volume']
        
        # Get latest values
        latest_close = close.iloc[-1]
        prev_close = close.iloc[-2]
        latest_volume = volume.iloc[-1]
        prev_volume = volume.iloc[-2]
        
        # 1. Price Change > 1%
        price_change_pct = (latest_close - prev_close) / prev_close * 100
        if price_change_pct <= 1: return False
        
        # 2. Volume > 2 * Volume MA 20
        vol_ma20 = volume.rolling(window=20).mean().iloc[-1]
        if latest_volume <= 2 * vol_ma20: return False
        
        # 3. Volume > 2 * Previous Volume
        if latest_volume <= 2 * prev_volume: return False
        
        # 4. Value > 10 Billion
        # Value approx = Close * Volume
        transaction_value = latest_close * latest_volume
        if transaction_value <= 10_000_000_000: return False
        
        # 5. Previous Price < Price (Green Candle)
        # Already covered by Price Change > 1%, but explicit check:
        if prev_close >= latest_close: return False
        
        # 6. Price > Price MA 10
        ma10 = close.rolling(window=10).mean().iloc[-1]
        if latest_close <= ma10: return False
        
        return True
    
    def calculate_entry_tp(self, data: pd.DataFrame, analysis: Dict, session: int = None, iep: float = None) -> Tuple[Optional[float], Optional[float], Dict]:
        """
        Menghitung Entry Point & TP dengan Analisis Mendalam (Deep Research):
        1. Fibonacci Retracement (Golden Price)
        2. Trend Structure
        3. IEP Integration
        """
        if len(data) < 60:
            return None, None, {"error": "Data kurang untuk analisis mendalam"}
        
        close = data['Close']
        high = data['High']
        low = data['Low']
        volume = data['Volume']
        
        latest_close = close.iloc[-1]
        
        # 1. Fibonacci Analysis
        fib = self.calculate_fibonacci(data)
        
        # 2. Moving Averages Support
        ma5 = self.calculate_sma(close, 5).iloc[-1]
        ma10 = self.calculate_sma(close, 10).iloc[-1]
        ma20 = self.calculate_sma(close, 20).iloc[-1]
        
        # 3. Indicators
        indicators = analysis.get("indicators", {})
        latest_adx = indicators.get("adx", 20)
        atr = self.calculate_atr(high, low, close, 14).iloc[-1]
        support, resistance = self.calculate_support_resistance(data, 20)
        
        # 4. Candlestick Analysis (Latest finalized candle)
        candle_pattern = self.detect_candlestick(
            data['Open'].iloc[-1], data['High'].iloc[-1], 
            data['Low'].iloc[-1], latest_close, close.iloc[-2]
        )
        
        # === STRATEGY: BEST ENTRY CALCULATION ===
        
        # Base Entry: Fibonacci Golden Pocket (0.5 - 0.618)
        # Jika harga saat ini jauh di atas Fib 0.5, berarti trend sangat kuat.
        # Support terdekat menjadi MA5 atau Fib 0.382.
        
        entry_haka = int(latest_close)
        
        # Tentukan Level Pullback Ideal
        # Priority: Fib 0.382 (Strong Trend) > Fib 0.5 (Normal) > Fib 0.618 (Deep Correction)
        
        if latest_close > fib['fib_0236']:
             # Harga di pucuk swing
             entry_pullback = fib['fib_0382'] # Tunggu di first support
             entry_source = "Fibonacci 0.382"
        elif latest_close > fib['fib_05']:
             entry_pullback = fib['fib_05']
             entry_source = "Fibonacci 0.5 (Mid)"
        else:
             entry_pullback = fib['fib_0618']
             entry_source = "Fibonacci Golden Ratio (0.618)"
             
        # Combine with MAs for precision
        # Ambil max(MA10, FibLevel) karena MA sering jadi dynamic support yang lebih dihormati saat strong uptrend
        entry_pullback = max(entry_pullback, ma10) 
        if latest_adx > 30:
             # Super strong, don't wait too deep
             entry_pullback = max(entry_pullback, ma5)
             entry_source += " + MA5 Confluence"
        else:
             entry_source += " + MA10 Confluence"
             
        entry_final = int(entry_pullback)
        recommended_option = "PULLBACK"
        recom_reason = f"Entry aman di area {entry_source}. Market volatile."

        # === Derived Metrics for Logic ===
        vol_ratio = 1.0
        if len(volume) > 20: 
             vol_avg = volume.rolling(20).mean().iloc[-1]
             if vol_avg > 0: vol_ratio = volume.iloc[-1] / vol_avg
             
        tp_conservative = fib['fib_ext_1272']
        tp_aggressive = fib['fib_ext_1618']

        # === SESSION 1 & IEP DEEP ANALYSIS ===
        iep_val = 0
        if session == 1 and iep is not None and iep > 0:
            last_date = data.index[-1].date()
            if last_date == datetime.now().date():
                 prev_close = close.iloc[-2]
            else:
                 prev_close = close.iloc[-1]
            
            iep_val = iep
            
            # Smart IEP Logic with Fibonacci Validation
            if iep > prev_close:
                # GAP UP Open
                # Validasi: Apakah Gap Up ini menembus Resistance atau Fib Level?
                if iep > fib['swing_high']:
                     # Breakout New High -> Very Bullish
                     entry_final = self.add_ticks(iep, 2)
                     recommended_option = "HAKA (BREAKOUT)"
                     recom_reason = f"IEP Breakout Swing High ({int(fib['swing_high'])}). Potensi rally kencang."
                else:
                     # Gap Up tapi masih di dalam range
                     entry_final = iep
                     recommended_option = "BUY ON STRENGTH"
                     recom_reason = f"Open Gap Up. Akumulasi di harga pembukaan ({int(iep)})."
            else:
                # GAP DOWN / Correction Open
                # Cek apakah koreksi ini mendarat di Golden Pocket?
                
                # Check distance to nearest strong support (Fib 0.5 or MA10)
                dist_to_fib05 = abs(iep - fib['fib_05'])
                dist_to_ma10 = abs(iep - ma10)
                
                if iep > fib['fib_0382'] and latest_adx > 25:
                    # Koreksi dangkal di trend kuat = BUY
                    entry_final = iep
                    recommended_option = "PRO BUY (DIP)"
                    recom_reason = f"IEP ({int(iep)}) koreksi sehat (di atas Fib 0.382). Buy sebelum rebound."
                else:
                    # Koreksi agak dalam, better wait
                    entry_final = max(int(ma10), int(iep))
                    recommended_option = "WAIT / SLOW BUY"
                    recom_reason = f"Koreksi pagi. Tunggu stabil di area {int(entry_final)}."



        # === SOROS PHILOSOPHY: "It's not whether you're right or wrong, but how much money you make..." ===
        # 1. IDENTIFY HIGH CONVICTION PLAY
        soros_signal = False
        if latest_adx > 35 and vol_ratio > 1.5 and candle_pattern != "DOJI (Wait)":
             soros_signal = True
             recommended_option = "SUPER CONVICTION (HAKA)"
             recom_reason = f"🔥🔥 SOROS STYLE: High Conviction! Trend & Volume Ledakan. Sikat Kanan."
             entry_final = entry_haka # Agresif
        
        # 2. LET PROFITS RUN (Trailing Logic)
        # Instead of fixed TP, we aim for extended run if trend is strong
        if soros_signal or latest_adx > 40:
             # Target is NOT just resistance, but breakout extension
             tp_price = max(fib['fib_ext_1618'], resistance * 1.10)
             strategy = "LET PROFITS RUN (Trailing Stop)"
        else:
             # Normal Logic
             if latest_adx > 35:
                # Trend is a beast -> Aim for 1.618
                tp_price = tp_aggressive
                strategy = "TREND FOLLOWING"
             else:
                # Normal trend -> Aim for 1.272
                tp_price = tp_conservative
                strategy = "SWING OPTIMAL"
        
        # Safety Check: TP must be > Breakout/Resistance
        target_breakout = max(resistance, entry_final * 1.05)
        tp_price = max(tp_price, target_breakout)
        
        # Ensure min profit 4%
        if tp_price < entry_final * 1.04:
            tp_price = entry_final * 1.04
            
        profit_pct = ((tp_price - entry_final) / entry_final) * 100
        is_ara_potential = ((resistance - entry_final) / entry_final * 100 < 5) and profit_pct > 3

        result = {
            "entry": entry_final,
            "iep": iep_val if iep_val and iep_val > 0 else 0,
            "entry_haka": entry_haka,
            "entry_pullback": int(entry_pullback),
            "fib_support": int(fib['fib_0618']), # Info tambahan
            "fib_resistance": int(fib['fib_ext_1618']), # Info tambahan
            "recommended_option": recommended_option,
            "recom_reason": recom_reason,
            "entry_pullback_reason": entry_source,
            "tp": int(tp_price),
            "profit_pct": profit_pct,
            "support": int(support),
            "resistance": int(resistance),
            "candle_pattern": candle_pattern,
            "is_ara_potential": is_ara_potential,
            "strategy": strategy,
            "market_cond": f"{candle_pattern} / ADX {latest_adx:.1f} / SOROS MODE: {'ON' if soros_signal else 'OFF'}"
        }
        
        return entry_final, tp_price, result
    
    def analyze_stock(self, ticker: str, period: str = "6mo", session: int = None) -> Dict: # Using 6mo for better SMA200/ADX context
        """
        Main function untuk menganalisis saham
        Returns: Dictionary dengan hasil analisis lengkap
        """
        try:
            # Download data dari yfinance
            stock = yf.Ticker(ticker)
            data = stock.history(period=period)
            
            if data.empty or len(data) < self.min_data_days:
                return {
                    "success": False,
                    "error": f"Data tidak mencukupi untuk {ticker}",
                    "ticker": ticker
                }
            
            # Fetch IEP / Market Status if Session 1
            iep = 0.0
            if session == 1:
                try:
                    # Try to get Open price from info (sometimes delayed 15m)
                    # Or 'regularMarketOpen'
                    # Note: This increases latency.
                    # Optimization: Only fetch if needed, but we do need it for the logic.
                    # stock.info is slow. Check fast_info first if possible?
                    # fast_info is available in newer yfinance.
                    
                    # Try fast_info (requires yfinance >= 0.2)
                    if hasattr(stock, 'fast_info'):
                        # 'open' might be available
                        if 'open' in stock.fast_info:
                             iep = stock.fast_info['open']
                    
                    # Fallback to info
                    if not iep:
                         iep = stock.info.get('open', 0)
                         if not iep:
                             iep = stock.info.get('regularMarketOpen', 0)
                         if not iep:
                             # Try getting today's data from history if available
                             if data.index[-1].date() == datetime.now().date():
                                 iep = data['Open'].iloc[-1]
                except:
                    pass

            # Deteksi uptrend
            is_uptrend, trend_analysis = self.is_uptrend(data)
            
            if not is_uptrend:
                return {
                    "success": True,
                    "ticker": ticker,
                    "is_uptrend": False,
                    "message": "Saham tidak memenuhi kriteria strong uptrend",
                    "analysis": trend_analysis
                }
            
            # Calculate Entry dan TP
            entry, tp, tp_analysis = self.calculate_entry_tp(data, trend_analysis, session=session, iep=iep)
            
            if entry is None or tp is None:
                return {
                    "success": False,
                    "error": "Gagal menghitung entry dan TP",
                    "ticker": ticker
                }
            
            # Get stock info (Optional, might slow down if too many requests)
            try:
                info = stock.info
                stock_name = info.get('longName', ticker)
            except:
                stock_name = ticker
            
            current_price = data['Close'].iloc[-1]
            
            # Prepare result
            result = {
                "success": True,
                "ticker": ticker,
                "name": stock_name,
                "is_uptrend": True,
                "current_price": current_price,
                "entry": entry,
                "tp": tp,
                "profit_pct": tp_analysis["profit_pct"],
                "is_ara_potential": tp_analysis["is_ara_potential"],
                "support": tp_analysis["support"],
                "resistance": tp_analysis["resistance"],
                "entry_haka": tp_analysis["entry_haka"],
                "entry_pullback": tp_analysis["entry_pullback"],
                "iep": tp_analysis.get("iep", 0),
                "recommended_option": tp_analysis["recommended_option"],
                "recom_reason": tp_analysis["recom_reason"],
                "entry_pullback_reason": tp_analysis["entry_pullback_reason"],
                "strategy": tp_analysis["strategy"],
                "market_cond": tp_analysis["market_cond"],
                "analysis": trend_analysis,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "ticker": ticker
            }
    
    def get_stock_fundamentals(self, stock: yf.Ticker) -> Dict:
        """Mengambil data fundamental perusahaan"""
        try:
            info = stock.info
            
            # Helper to format big numbers
            def fmt_num(n):
                if n is None: return "-"
                if n >= 1e12: return f"{n/1e12:.2f}T"
                if n >= 1e9: return f"{n/1e9:.2f}B"
                if n >= 1e6: return f"{n/1e6:.2f}M"
                return f"{n:,.0f}"

            eps = info.get('trailingEps', info.get('forwardEps', 0))
            net_income = info.get('netIncomeToCommon', info.get('netIncome', 0))
            total_assets = info.get('totalAssets', 0)
            
            return {
                "eps": eps,
                "net_income": fmt_num(net_income),
                "total_assets": fmt_num(total_assets),
                "pe_ratio": info.get('trailingPE', 0),
                "market_cap": fmt_num(info.get('marketCap', 0))
            }
        except Exception as e:
            return {
                "eps": "-", "net_income": "-", "total_assets": "-", "error": str(e)
            }

    def get_market_narrative(self, ticker: str, close: float, support: float, resistance: float, trends: Dict, bb_status: str = "") -> str:
        """Membuat narasi deskriptif tentang kondisi saham (mirip manusia)"""
        
        # Determine Phase
        indicators = trends.get('indicators', {})
        adx = indicators.get('adx', 0)
        macd = indicators.get('macd', 0)
        signal = indicators.get('signal', 0)
        rsi = indicators.get('rsi', 50)
        
        status = ""
        narrative = ""
        
        # Logic Status
        if adx > 25 and macd > signal:
             status = "Uptrend Kuat"
             detail = "Sedang dalam fase kenaikan yang solid."
        elif macd > signal and rsi < 60:
             status = "Early Uptrend"
             detail = "Mulai menunjukkan tanda-tanda pembalikan arah positif."
        elif adx < 20:
             status = "Sideways"
             detail = f"Bergerak stabil di rentang harga terbatas."
        elif macd < signal:
             status = "Downtrend / Koreksi"
             detail = "Sedang mengalami tekanan jual."
        else:
             status = "Netral"
             detail = "Pergerakan harga belum menunjukkan arah trend yang dominan."
             
        # Build Narrative
        
        narrative = f"*{ticker}* berada dalam kondisi *{status}*, dengan harga bergerak {detail} "
        narrative += f"Saat ini rentang pergerakan berada di antara Support {int(support)} dan Resistance {int(resistance)}. "
        
        # Bollinger Bands Context
        if bb_status == "SQUEEZE":
             narrative += "Bollinger Bands menyempit (Squeeze), menandakan potensi ledakan harga (volatilitas tinggi) segera terjadi. "
        elif bb_status == "UPPER_BREAK":
             narrative += "Harga menembus Upper Bollinger Band, momentum Bullish sangat kuat. "
             
        # Indicator Narrative
        if rsi > 70:
             narrative += "RSI menunjukkan kondisi Overbought (jenuh beli), waspada koreksi. "
        elif rsi < 30:
             narrative += "RSI di area Oversold, potensi rebound teknikal. "
        else:
             narrative += "RSI dan Bollinger Bands menunjukkan kondisi yang lebih netral. "
             
        if macd > signal:
             narrative += "MACD mengonfirmasi momentum positif."
        else:
             narrative += "Hati-hati, momentum MACD masih negatif."
             
        return narrative

    def analyze_stock_detailed(self, ticker: str) -> Dict:
        """
        Analisis mendalam single shot untuk command bot interaktif
        Termasuk fundamental dan format pesan lengkap
        """
        # 1. Base Analysis
        base_result = self.analyze_stock(ticker, period="6mo")
        
        # If analyze_stock failed completely (e.g. no data)
        if base_result.get("error"):
             return base_result

        stock = yf.Ticker(ticker)
        
        # 2. Add Fundamentals (Refresh in case base analysis skipped it)
        finals = self.get_stock_fundamentals(stock)
        
        # 3. Check technicals again if base_result was 'false' on uptrend
        if not base_result.get("is_uptrend"):
             data = stock.history(period="6mo")
             if not data.empty and len(data) > 60:
                 is_up, analysis = self.is_uptrend(data)
                 entry, tp, tp_analysis = self.calculate_entry_tp(data, analysis)
                 base_result.update(tp_analysis)
                 base_result["analysis"] = analysis
                 base_result["current_price"] = data['Close'].iloc[-1]
                 base_result["name"] = ticker 
                 base_result["success"] = True
             else:
                 return {"success": False, "error": "Data tidak cukup"}

        analysis = base_result.get("analysis", {})
        indicators = analysis.get("indicators", {})
        
        # 4. Add Bollinger Bands Analysis
        data = stock.history(period="6mo")
        close = data['Close']
        sma20 = close.rolling(window=20).mean()
        std20 = close.rolling(window=20).std()
        upper_bb = sma20 + (std20 * 2)
        lower_bb = sma20 - (std20 * 2)
        
        latest_close = close.iloc[-1]
        latest_upper = upper_bb.iloc[-1]
        latest_lower = lower_bb.iloc[-1]
        bb_width = (latest_upper - latest_lower) / sma20.iloc[-1]
        
        bb_status = "NORMAL"
        if bb_width < 0.10: # Narrow band
             bb_status = "SQUEEZE"
        elif latest_close > latest_upper:
             bb_status = "UPPER_BREAK"
        
        # Narrative
        support = base_result.get("support", 0)
        resistance = base_result.get("resistance", 0)
        
        narrative = self.get_market_narrative(ticker, latest_close, support, resistance, analysis, bb_status)
        
        # 4. Construct Final Response Structure
        entry = base_result.get("entry", latest_close)
        
        # Custom TP Levels
        tp1 = entry * 1.02 # Scalping
        tp2 = base_result.get("tp", entry * 1.05)
        tp3 = base_result.get("resistance", entry * 1.10)
        
        # Calculate Cutloss
        # Typically under previous swing low or support
        cutloss = base_result.get("entry_pullback", entry * 0.95) * 0.97
        
        # Estimate Hit Days based on TP2 (Main Target)
        tp_pct_calc = ((tp2 - entry) / entry) * 100
        if tp_pct_calc <= 3:
            est_days = "1-2 Hari"
        elif tp_pct_calc <= 8:
            est_days = "3-5 Hari"
        elif tp_pct_calc <= 15:
            est_days = "1-2 Minggu"
        else:
            est_days = "2-4 Minggu"
        
        base_result["est_hit_days"] = est_days
        
        # Format response message (Text)
        message = (
            f"⚡ *ANALISA SAHAM - {stock.info.get('longName', ticker)} ({ticker})*\n"
            f"🕒 Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"{narrative}\n\n"
            f"Kondisi Fundamental:\n"
            f"• EPS (Earnings Per Share): {finals['eps']}\n"
            f"• Net Income (TTM): {finals['net_income']}\n"
            f"• Total Aset: {finals['total_assets']}\n\n"
            f"🚪 Entry: {int(entry)}\n"
            f"🛡 Support: {int(support)}\n"
            f"🚀 Resistance: {int(resistance)}\n\n"
            f"💵 TP 1: {int(tp1)}\n"
            f"💰 TP 2: {int(tp2)}\n"
            f"💸 TP 3: {int(tp3)}\n\n"
            f"Cutloss: {int(cutloss)}\n\n"
            f"🔴 ‼️ Peringatan: Waspada volatilitas pasar. Gunakan money management yang bijak."
        )
        
        base_result["message"] = message
        base_result["chart_data"] = data
        
        return base_result

    def analyze_bsjp_ticker(self, ticker: str) -> bool:
        """Helper to quickly check BSJP status for a ticker"""
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period="3mo") # Need 20 days MA
            return self.is_bsjp(data)
        except:
            return False

    def analyze_tickers_parallel(self, tickers: list, period: str = "6mo", max_workers: int = 10, session: int = None) -> list:
        """
        Menganalisis multiple saham secara parallel
        Returns: List hasil analisis
        """
        results = []
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        print(f"Menganalisis {len(tickers)} saham dengan {max_workers} threads...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_ticker = {
                executor.submit(self.analyze_stock, ticker, period, session): ticker 
                for ticker in tickers
            }
            
            # Process results as they complete
            for i, future in enumerate(as_completed(future_to_ticker)):
                ticker = future_to_ticker[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Optional: Progress logging
                    if (i + 1) % 10 == 0:
                        print(f"Progress: {i + 1}/{len(tickers)} saham selesai")
                        
                except Exception as e:
                    print(f"Error analyzing {ticker}: {e}")
                    results.append({
                        "success": False, 
                        "ticker": ticker, 
                        "error": str(e)
                    })
        
        return results

    def analyze_multiple_stocks(self, tickers: list, period: str = "6mo", session: int = None) -> list:
        """Menganalisis multiple saham sekaligus (Serial - lambat)"""
        return self.analyze_tickers_parallel(tickers, period, session=session)


if __name__ == "__main__":
    # Test
    analyzer = StockAnalyzer()
    # Test with a known major stock
    result = analyzer.analyze_stock("BBCA.JK")
    print(result)
