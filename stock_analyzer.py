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
        self.min_data_days = 30  # Adjusted to 30 to allow analysis of more stocks (e.g. recent IPOs or sparse data)

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
        
        # === 0. DETEKSI NAIK KENCANG / MOMENTUM (PRIORITAS UTAMA) ===
        # Request User: Fokus saham yang "Naik Kenceng" untuk mengurangi waktu tunggu.
        
        is_spike = False
        is_high_momentum = False
        
        # Criteria 1: Price Change > 2% AND Price > MA5 (Short term trend up)
        # Criteria 2: Significant Value (>1B)
        
        transaction_value = latest_close * latest_volume
        
        if price_change_pct > 2 and latest_close > latest_sma20:
             is_high_momentum = True
             
        if price_change_pct > 4 and vol_ratio > 1.2:
             is_spike = True
             reasons.append(f"🚀 HARGA NAIK KENCANG (+{price_change_pct:.1f}%)")
             
        # === FILTERING BARU (STRICT FOR MOMENTUM) ===
        
        # 1. Filter: Value minimal 1 Miliar (Biar liquid)
        if transaction_value < 1_000_000_000:
             return False, {"reason": "Likuiditas Rendah (< 1M)"}
             
        # 2. Filter: Momentum Check
        # User wants "Naik Kenceng". Reject if Price Change < 1% unless it's a perfect Golden Cross Setup
        if price_change_pct < 1 and not (prev_histogram < 0 and latest_histogram > 0):
             return False, {"reason": "Momentum Lemah (Kenaikan < 1%)"}

        # 3. Base Trend Filter
        # Still need basic trend filter but allow reversals
        if latest_close < latest_sma50 * 0.90: # Allow deeper discount but not trash
             return False, {"reason": "Trend Bearish Parah (<SMA50)"}

        # 4. MACD / Indicator Check
        # If it is high momentum (spike), we trust the volume and price more than lagging MACD.
        # But if not spike, we need MACD confirmation.
        
        if not is_spike and not is_high_momentum:
             # Normal strict mode for slower stocks
             if not is_macd_reversal and not (latest_macd > latest_signal):
                  return False, {"reason": "MACD Belum Confirm"}
        
        if is_macd_reversal:
             reasons.append(f"✓ {reversal_reason}")
        
        # Support Filters
        if latest_rsi > 85: # Sedikit longgar untuk saham gorengan/momentum
             return False, {"reason": "RSI Overbought (>85)"}

        # Scoring
        score = 60
        if is_spike: score += 20
        if is_high_momentum: score += 10
        if transaction_value > 5_000_000_000: score += 10 # Prefer high liquid
        
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
        Screening BSJP (BELI SORE JUAL PAGI) updated criteria:
        1. 1 Day Price Returns (%) > 1
        2. Volume > 2 * Volume MA 20
        3. Volume > 2 * Previous Volume
        4. Value > 10,000,000,000 (10 Miliar)
        5. Price > Previous Price
        6. Price > Price MA 10
        7. Previous Price >= 1
        """
        if len(data) < 25: return False
        
        close = data['Close']
        volume = data['Volume']
        
        # Get latest values
        latest_close = close.iloc[-1]
        prev_close = close.iloc[-2]
        latest_volume = volume.iloc[-1]
        prev_volume = volume.iloc[-2]
        
        # 1. 1 Day Price Returns (%) > 1
        price_return_pct = (latest_close - prev_close) / prev_close * 100
        if price_return_pct <= 1: return False
        
        # 2. Volume > 2 * Volume MA 20
        vol_ma20 = volume.rolling(window=20).mean().iloc[-1]
        if latest_volume <= 2 * vol_ma20: return False
        
        # 3. Volume > 2 * Previous Volume
        if latest_volume <= 2 * prev_volume: return False
        
        # 4. Value > 10,000,000,000
        transaction_value = latest_close * latest_volume
        if transaction_value <= 10_000_000_000: return False
        
        # 5. Price > Previous Price (Already covered by #1, but following rules)
        if latest_close <= prev_close: return False
        
        # 6. Price > Price MA 10
        price_ma10 = close.rolling(window=10).mean().iloc[-1]
        if latest_close <= price_ma10: return False
        
        # 7. Previous Price >= 1
        if prev_close < 1: return False
        
        return True
    
    def is_red_to_green_momentum(self, data: pd.DataFrame) -> Tuple[bool, Dict]:
        """
        Strategi: RED TO GREEN + SPIKE
        Mencari saham yang sempat merah (Low < PrevClose) tapi sekarang Hijau Kuat.
        Ciri-ciri saham yang akan reversal/naik tinggi hari ini.
        """
        if len(data) < 25: return False, {}
        
        close = data['Close']
        high = data['High']
        low = data['Low']
        open_price = data['Open']
        volume = data['Volume']
        
        # Latest Candle
        latest_close = close.iloc[-1]
        latest_open = open_price.iloc[-1]
        latest_low = low.iloc[-1]
        latest_high = high.iloc[-1]
        latest_volume = volume.iloc[-1]
        
        # Previous Day
        prev_close = close.iloc[-2]
        
        # 1. Condition: Was Red (Low < PrevClose)
        # Artinya sempat turun di bawah harga kemarin
        if latest_low >= prev_close:
             return False, {} # Tidak pernah merah, ini Open Gap Up atau selalu hijau
             
        # 2. Condition: Now Green (Close > PrevClose)
        if latest_close <= prev_close:
             return False, {} # Masih merah
             
        # 3. Condition: Strong Green Candle (Close > Open)
        if latest_close <= latest_open:
             return False, {}
             
        # 4. Momentum: Change > 1% but < 20% (Avoid ARA limit logic issues or too late)
        change_pct = (latest_close - prev_close) / prev_close * 100
        if change_pct < 1.0 or change_pct > 24:
             return False, {}
             
        # 5. Volume Spike (Relative to MA20)
        # Kita asumsikan ini intraday, jadi volume mungkin belum full daily.
        # Tapi "Momentum" biasanya volume deres.
        vol_ma20 = volume.rolling(window=20).mean().iloc[-2] # Pakai rata2 historical
        
        # Minimal volume sudah tembus 25% dari rata-rata harian (untuk pagi)
        # atau Ratio > 1.5x volume kemarin di jam yang sama (susah dpt data jam)
        # Kita pakai threshold simple: Volume > 0.3 * MA20Volume
        if latest_volume < (vol_ma20 * 0.3):
             return False, {}
             
        # 6. Value Filter (> 2 Miliar agar tidak gorengan parah)
        transaction_value = latest_close * latest_volume
        if transaction_value < 2_000_000_000:
             return False, {}

        # 7. Additional Boost: Breakout Resistance Intraday?
        # Sederhana: Close dekat High (Strong finish potential)
        # Body candle > Upper Shadow
        upper_shadow = latest_high - latest_close
        body = latest_close - latest_open
        if upper_shadow > body * 1.5: # Shadow terlalu panjang, reject (Selling pressure)
             return False, {}
             
        return True, {
            "strategy": "RED TO GREEN MOMENTUM",
            "price": latest_close,
            "change_pct": change_pct,
            "volume": latest_volume,
            "prev_close": prev_close,
            "low": latest_low,
            "reason": f"Sempat turun ke {int(latest_low)}, Rebound kuat ke {int(latest_close)} (+{change_pct:.1f}%)"
        }

    def calculate_entry_tp(self, data: pd.DataFrame, analysis: Dict, session: int = None, iep: float = None) -> Tuple[Optional[float], Optional[float], Dict]:
        """
        Menghitung Entry Point & TP dengan Analisis Mendalam (Deep Research):
        1. Fibonacci Retracement (Golden Price)
        2. Trend Structure
        3. Momentum Adaptive Entry
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
        
        # 3. Indicators
        indicators = analysis.get("indicators", {})
        latest_adx = indicators.get("adx", 20)
        support, resistance = self.calculate_support_resistance(data, 20)
        
        # 4. Candlestick Analysis (Latest finalized candle)
        candle_pattern = self.detect_candlestick(
            data['Open'].iloc[-1], data['High'].iloc[-1], 
            data['Low'].iloc[-1], latest_close, close.iloc[-2]
        )
        
        # === STRATEGY: SMART ENTRY SYSTEM ===
        
        # Determine Market Momentum State
        # Lowered threshold to 25 for strong uptrend (Indonesian market often volatile with lower ADX start)
        if latest_adx > 25 and latest_close > ma5:
            market_state = "STRONG_UPTREND"
        elif latest_adx > 15:
            market_state = "NORMAL_UPTREND"
        else:
            market_state = "SIDEWAYS/WEAK"
            
        # Entry Logic Options
        
        # 1. Aggressive Entry (For High Conviction/HAKA)
        # Entry near current price
        entry_aggressive = int(latest_close)
        
        # 2. Moderate/Best Entry (Dynamic Support)
        if market_state == "STRONG_UPTREND":
            # If fast moving, MA5 is the floor.
            entry_best = int(ma5)
            
            # If deviation is large (Price >> MA5), 'Best' might be too far.
            # Create a 'Hybrid' entry closer to price.
            if latest_close > ma5 * 1.05:
                 entry_best = int((latest_close + ma5) / 2)
        
        elif market_state == "NORMAL_UPTREND":
            entry_best = int(ma10)
            # If price is maintaining above MA5 distinctively
            if latest_close > ma5:
                entry_best = int(ma5)
        else:
            entry_best = int((ma10 + support)/2) # Wait deeper
        
        # 3. Conservative/Safe Entry (Deep Pullback)
        entry_safe = int(max(support, fib['fib_0618']))

        # === SELECTION LOGIC ===
        
        # Logic: If user asks "Why not current price?", we validte it here.
        # If trend is strong, Recommended Option becomes HAKA/Aggressive
        
        if market_state == "STRONG_UPTREND":
             entry_final = entry_aggressive
             recommended_option = "HAKA (Momentum)"
             recom_reason = "Momentum sangat kuat. Disarankan masuk dekat harga running (HAKA) agar tidak ketinggalan."
             if entry_best < entry_aggressive * 0.98:
                  # If there's a significant gap between Aggressive and MA5, offer range
                  recom_reason += f" Atau antri di {entry_best} jika ingin lebih aman."
        elif market_state == "NORMAL_UPTREND":
             entry_final = entry_best
             recommended_option = "BUY ON WEAKNESS"
             recom_reason = f"Trend solid. Entry terbaik di area MA5-MA10."
        else:
             entry_final = entry_safe
             recommended_option = "WAIT AND SEE"
             recom_reason = "Trend belum confirm kuat. Tunggu di support bawah."

        # SESSION 1 / LIVE MARKET LOGIC
        iep_val = 0
        if session == 1 and iep is not None and iep > 0:
            iep_val = iep
            # Gap Check
            if iep > latest_close * 1.02: # Gap Up > 2%
                 entry_final = iep
                 recommended_option = "BUY ON BREAKOUT (GAP)"
                 recom_reason = f"Open Gap Up signifik. Ikuti arus momentum pagi."
            elif iep < latest_close * 0.98: # Gap Down > 2%
                 entry_final = entry_safe
                 recommended_option = "WAIT FOR DIP"
                 recom_reason = f"Open Gap Down. Tunggu pantulan di area support kuat."
            else:
                 # Normal open
                 if market_state == "STRONG_UPTREND":
                     entry_final = iep
                     recommended_option = "HAKA (Open)"
        
        # Force Adjust: If Entry Final is too far from current (e.g. > 5%) in an uptrend, pull it up.
        if market_state in ["STRONG_UPTREND", "NORMAL_UPTREND"] and entry_final < latest_close * 0.95:
             entry_final = int(latest_close * 0.98) # 2% discount max
             recommended_option += " (Adjusted)"
             recom_reason = "Harga running kencang. Entry disesuaikan mendekati harga pasar."

        # === TP CALCULATION ===
        tp_conservative = fib['fib_ext_1272']
        tp_aggressive = fib['fib_ext_1618']
        
        # TP 1
        tp1 = max(resistance, latest_close * 1.03) # Min 3% yield
        
        # TP 2 (Target Utama)
        if market_state == "STRONG_UPTREND":
            tp2 = tp_aggressive
            strategy = "TREND FOLLOWING"
        else:
            tp2 = tp_conservative
            strategy = "SWING TRADING"
            
        tp3 = tp2 * 1.10 # Extended run
        
        # Ensure Hierarchy
        if tp2 <= tp1: tp2 = tp1 * 1.05
        if tp3 <= tp2: tp3 = tp2 * 1.05

        # === TIMEFRAME INFERENCE ===
        # Determine the holding period based on strategy and option
        if recommended_option.startswith("HAKA") or recommended_option.startswith("BUY ON BREAKOUT"):
             timeframe = "DAYTRADE (1-3 Hari) / SCALPING"
        elif strategy == "SWING TRADING" or recommended_option == "BUY ON WEAKNESS":
             timeframe = "SWING (1-3 Minggu)"
        elif strategy == "TREND FOLLOWING":
             timeframe = "TREND FOLLOWING (Bisa > 1 Bulan)"
        else:
             timeframe = "WATCHLIST / SHORT TERM"
             
        # Override for Session 1 gap ups -> likely Daytrade focus
        if session == 1 and iep > latest_close * 1.02:
             timeframe = "DAYTRADE (Manfaatkan Volatilitas Pagi)"

        # Calculate profit pct for the dictionary
        profit_pct = ((tp2 - entry_final) / entry_final) * 100
        is_ara_potential = ((resistance - entry_final) / entry_final * 100 < 5) and profit_pct > 3

        result = {
            "entry": entry_final,
            "entry_aggressive": int(entry_aggressive),
            "entry_safe": int(entry_safe),
            "entry_haka": int(entry_aggressive), # Alias for aggressive
            "entry_pullback": int(entry_safe),   # Alias for safe
            "entry_pullback_reason": recom_reason, # Alias
            "iep": iep_val if iep_val else 0,
            "recommended_option": recommended_option,
            "recom_reason": recom_reason,
            "tp": int(tp2), # Main TP for simple dict access
            "tp1": int(tp1),
            "tp2": int(tp2),
            "tp3": int(tp3),
            "profit_pct": profit_pct,
            "is_ara_potential": is_ara_potential,
            "support": int(support),
            "resistance": int(resistance),
            "candle_pattern": candle_pattern,
            "strategy": strategy,
            "timeframe": timeframe,
            "market_cond": f"{market_state} (ADX {latest_adx:.0f})"
        }
        
        return entry_final, int(tp2), result
    
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
                # Log but don't delete from file, just return failure for this run
                return {
                    "success": False,
                    "error": f"Data tidak mencukupi/kosong untuk {ticker}",
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
    
    def get_stock_news(self, stock: yf.Ticker) -> str:
        """Mengambil dan menganalisis sentimen berita terbaru via Google News RSS"""
        import requests
        import xml.etree.ElementTree as ET
        import html
        import re
        
        try:
            # 1. Try Google News RSS first (More up to date for IDX)
            ticker_clean = stock.ticker.replace(".JK", "")
            # Use quotes to ensure specific ticker search (e.g. "BUMI")
            query = f'"{ticker_clean}" saham'
            url = f"https://news.google.com/rss/search?q={query}&hl=id-ID&gl=ID&ceid=ID:id"
            
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
            response = requests.get(url, headers=headers, timeout=5)
            news_items = []
            
            # Helper to clean and add item
            def add_item(t, l):
                t = html.unescape(t)
                for sept in [' - ', ' | ']: # Remove source suffix
                    if sept in t:
                        t = t.rsplit(sept, 1)[0]
                # Filter: Ticker must be present (lenient) or generic huge news
                # But user wants specific.
                if ticker_clean.lower() in t.lower():
                     news_items.append({"title": t, "link": l})

            if response.status_code == 200:
                root = ET.fromstring(response.content)
                items = root.findall('./channel/item')
                
                for item in items[:5]: # Check top 5 parent items
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    desc_elem = item.find('description') # Description often has the cluster
                    
                    if title_elem is None or link_elem is None: continue

                    title_raw = title_elem.text
                    link_raw = link_elem.text
                    desc_raw = desc_elem.text if desc_elem is not None else ""
                    
                    # Check if description has clustered stories (HTML list)
                    if desc_raw and '<ol>' in desc_raw:
                        # Extract links from HTML
                        matches = re.findall(r'<a href="(.*?)".*?>(.*?)</a>', desc_raw)
                        for link, title in matches:
                            add_item(title, link)
                    else:
                        add_item(title_raw, link_raw)
                        
            # 2. Deduplicate by title
            unique_news = []
            seen_titles = set()
            for n in news_items:
                if n['title'] not in seen_titles:
                    unique_news.append(n)
                    seen_titles.add(n['title'])
            
            news_items = unique_news[:5] # Limit pool

            # 3. Fallback to Yahoo if empty
            if not news_items:
                 try:
                     y_news = stock.news
                     for item in y_news[:3]:
                        content = item.get('content', {})
                        t = content.get('title', item.get('title', ''))
                        l = content.get('clickThroughUrl', item.get('link', ''))
                        if t and l:
                            add_item(t, l)
                 except: 
                     pass
                 
                 # Deduplicate again after fallback
                 unique_news = []
                 seen_titles = set()
                 for n in news_items:
                    if n['title'] not in seen_titles:
                        unique_news.append(n)
                        seen_titles.add(n['title'])

            news_items = unique_news[:3] # Final Check limit 3

            if not news_items:
                return "Tidak ada berita terbaru saat ini."
            
            # Keywords for sentiment
            pos_keywords = ["profit", "jump", "surge", "gain", "buy", "bull", "growth", "record", "revenue up", "income up", "acquisition", "laba", "naik", "tumbuh", "dividen", "akuisisi", "kerjasama", "positif", "hijau", "cuan", "melejit", "terbang", "disetujui", "divestasi", "untung", "kinclong", "bersinar", "net buy", "full senyum", "dividen"]
            neg_keywords = ["loss", "drop", "plunge", "fall", "sell", "bear", "down", "revenue down", "income down", "suit", "fine", "debt", "bankrupt", "rugi", "turun", "anjlok", "utang", "pailit", "gugat", "merah", "koreksi", "suspend", "net sell", "boncos", "melorot", "anjlok", "kebakaran", "phk"]
            
            formatted_news = []
            
            for item in news_items:
                title = item['title']
                link = item['link']
                
                # Sentiment
                text_to_check = title.lower()
                if any(k in text_to_check for k in pos_keywords):
                    emoji = "🟢"
                elif any(k in text_to_check for k in neg_keywords):
                    emoji = "🔴"
                else:
                    emoji = "⚪"
                
                # Format: "• [Emoji] Title" -> Link (Clean & clickable)
                news_entry = f"• {emoji} [{title}]({link})"
                formatted_news.append(news_entry)
                
            return "\n".join(formatted_news)
            
        except Exception as e:
            print(f"News fetch error: {e}")
            return "Gagal mengambil berita."

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
        base_result["fundamentals"] = finals
        
        # 2b. Add News
        news_summary = self.get_stock_news(stock)
        base_result["news"] = news_summary
        
        # 3. Check technicals again if base_result was 'false' on uptrend
        # or if we are just doing a detailed lookup.
        # Retry mechanism for data fetching
        data = pd.DataFrame()
        for attempt in range(3):
            try:
                data = stock.history(period="6mo")
                if not data.empty and len(data) > 30: # 30 days min for basic MA
                    break
            except Exception as e:
                print(f"Retry {attempt+1} for {ticker}: {e}")
            
        # 2c. Force Realtime Price Update
        
        # Helper for safe float -> int
        def safe_int(val):
            try:
                if val is None or pd.isna(val): return 0
                return int(val)
            except:
                return 0

        # Helper for safe pct
        def calc_pct(curr, prev):
            if not prev or prev == 0: return 0.0
            return ((curr - prev) / prev) * 100

        current_price = 0
        change_pct = 0

        try:
            # Get realtime price from fast_info (most accurate for IDX)
            current_price = None
            prev_close = None
            
            # Try fast_info first (most reliable/fast)
            if hasattr(stock, 'fast_info'):
                try:
                    current_price = stock.fast_info.last_price
                    prev_close = stock.fast_info.previous_close
                    if current_price is None: 
                        current_price = stock.fast_info.get('last_price')
                        prev_close = stock.fast_info.get('previous_close')
                except:
                    pass
            
            # Fallback to stock.info
            if current_price is None:
                 info = stock.info
                 current_price = info.get('currentPrice') or info.get('regularMarketPrice')
                 prev_close = info.get('previousClose') or info.get('regularMarketPreviousClose')

            if current_price and prev_close:
                change_pct = calc_pct(current_price, prev_close)
            
                # Update base_result
                base_result["current_price"] = current_price
                base_result["change_pct"] = change_pct
                
                # Update DataFrame for technical analysis
                if not data.empty:
                    last_dt = data.index[-1]
                    # Check if the last candle is from Today
                    is_today = last_dt.date() == datetime.now().date()
                    
                    if is_today:
                        # Update existing candle
                        data.at[last_dt, 'Close'] = current_price
                        # Update High/Low if price broke them
                        if current_price > data.at[last_dt, 'High']:
                            data.at[last_dt, 'High'] = current_price
                        if current_price < data.at[last_dt, 'Low']:
                            data.at[last_dt, 'Low'] = current_price
                    else:
                        # Append new virtual candle for Today (Snapshot)
                        # import pandas as pd # Removed to avoid UnboundLocalError
                        new_idx = pd.Timestamp(datetime.now(), tz=last_dt.tz)
                        
                        new_row_dict = {
                            'Open': current_price,
                            'High': current_price,
                            'Low': current_price,
                            'Close': current_price,
                            'Volume': 0
                        }
                        new_row = pd.DataFrame([new_row_dict], index=[new_idx])
                        
                        # Explicitly cast to match types to avoid FutureWarnings or Errors
                        try:
                           data = pd.concat([data, new_row])
                        except:
                           pass # If concat fails, ignore realtime update to dataframe
                        
        except Exception as e:
            print(f"Realtime price fetch error: {e}")
            current_price = data['Close'].iloc[-1] if not data.empty else 0
            change_pct = 0
            
        # Fallback if current_price is missing
        if not current_price and not data.empty:
            current_price = data['Close'].iloc[-1]
            
        if data.empty or len(data) < 30:
             return {"success": False, "error": f"Data tidak cukup/kosong untuk {ticker} (Coba lagi nanti)"}

        if not base_result.get("is_uptrend"):
             if not data.empty and len(data) > 50:
                 is_up, analysis = self.is_uptrend(data)
                 # Force calculation for detailed view even if technically not 'Strong Uptrend'
                 entry, tp, tp_analysis = self.calculate_entry_tp(data, analysis)
                 base_result.update(tp_analysis)
                 base_result["analysis"] = analysis
                 base_result["success"] = True
                 base_result["is_uptrend"] = is_up # Update status
             else:
                 return {"success": False, "error": "Data history terlalu pendek (<50 hari)"}

        analysis = base_result.get("analysis", {})
        indicators = analysis.get("indicators", {})
        
        # 4. Add Bollinger Bands Analysis
        # Re-calculate with updated data
        close = data['Close']
        sma20 = close.rolling(window=20).mean()
        std20 = close.rolling(window=20).std()
        upper_bb = sma20 + (std20 * 2)
        lower_bb = sma20 - (std20 * 2)
        
        latest_close = close.iloc[-1]
        latest_upper = upper_bb.iloc[-1]
        latest_lower = lower_bb.iloc[-1]
        bb_width = (latest_upper - latest_lower) / sma20.iloc[-1] if not sma20.empty and sma20.iloc[-1] != 0 else 0
        
        bb_status = "NORMAL"
        if bb_width < 0.10: # Narrow band
             bb_status = "SQUEEZE"
        elif latest_close > latest_upper:
             bb_status = "UPPER_BREAK"
        
        # Narrative
        support = base_result.get("support", 0)
        resistance = base_result.get("resistance", 0)
        
        narrative = self.get_market_narrative(ticker, latest_close, support, resistance, analysis, bb_status)
        
        # Override Narrative if manual Price Change is high but ADX low (False Sideways)
        if indicators.get('adx', 0) < 20 and abs(change_pct) > 3 and "Sideways" in narrative:
            narrative = narrative.replace("Sideways", "Volatile / Breakout").replace("Bergerak stabil", "Bergerak agresif")

        # 4. Construct Final Response Structure
        entry = base_result.get("entry", latest_close)
        
        # Custom TP Levels (Sorted & Validated)
        potential_tps = {
            entry * 1.02,
            base_result.get("resistance", 0),
            base_result.get("tp", 0),
            base_result.get("fib_resistance", 0)
        }
        
        # Filter: Unique, > Entry + 1% to be meaningful
        valid_tps = sorted([t for t in potential_tps if t > entry * 1.01])
        
        # Ensure we have at least 3 levels
        if not valid_tps:
             valid_tps = [entry * 1.02]
             
        while len(valid_tps) < 3:
             valid_tps.append(valid_tps[-1] * 1.05)
             
        tp1 = valid_tps[0]
        tp2 = valid_tps[1]
        tp3 = valid_tps[2]
        
        cutloss = base_result.get("entry_pullback", entry * 0.95) * 0.97
        
        # Estimate Hit Days
        tp_pct_calc = ((tp2 - entry) / entry) * 100
        if tp_pct_calc <= 3: est_days = "1-2 Hari"
        elif tp_pct_calc <= 8: est_days = "3-5 Hari"
        elif tp_pct_calc <= 15: est_days = "1-2 Minggu"
        else: est_days = "2-4 Minggu"
        
        base_result["est_hit_days"] = est_days
        
        change_pct_clean = change_pct if isinstance(change_pct, (int, float)) else 0
        
        price_icon = "🟢" if change_pct_clean >= 0 else "🔴"
        
        # Safe Int wrappers
        c_price = safe_int(current_price)
        s_eps = finals.get('eps', '-')
        s_ni = finals.get('net_income', '-')
        s_ast = finals.get('total_assets', '-')
        
        message = (
            f"⚡ *ANALISA SAHAM - {stock.info.get('longName', ticker)} ({ticker})*\n"
            f"🕒 Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"{price_icon} *Harga Saat Ini: {c_price:,}* ({change_pct_clean:+.2f}%)\n\n"
            f"{narrative}\n\n"
            f"Kondisi Fundamental:\n"
            f"• EPS (Earnings Per Share): {s_eps}\n"
            f"• Net Income (TTM): {s_ni}\n"
            f"• Total Aset: {s_ast}\n\n"
            f"📰 *Berita Terkait:*\n"
            f"{base_result.get('news', '-')}\n\n"
            
            f"🎯 *Rekomendasi Entry:*\n"
            f"🔹 Best Buy: {safe_int(entry)}\n"
            f"🔸 Aggressive: {safe_int(base_result.get('entry_aggressive', entry))}\n"
            f"🛡 Conservative: {safe_int(base_result.get('entry_safe', entry))}\n\n"
            
            f"🛡 Support: {safe_int(support)}\n"
            f"🚀 Resistance: {safe_int(resistance)}\n\n"
            f"💵 TP 1: {safe_int(tp1)}\n"
            f"💰 TP 2: {safe_int(tp2)}\n"
            f"💸 TP 3: {safe_int(tp3)}\n\n"
            f"Cutloss: {safe_int(cutloss)}\n\n"
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
