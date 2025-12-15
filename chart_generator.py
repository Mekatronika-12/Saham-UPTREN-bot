import matplotlib
matplotlib.use('Agg')
import mplfinance as mpf
import pandas as pd
import os
import matplotlib.pyplot as plt

def generate_stock_chart(data: pd.DataFrame, ticker: str, filename: str = "chart.png"):
    """
    Generate professional technical analysis chart using mplfinance.
    Style: White/Clean (Yahoo style) matching user request.
    Indicators: MA(20, 50, 200), MACD, RSI, Volume
    """
    
    if len(data) < 30:
        return None
        
    # Prepare Data
    plot_data = data.tail(150).copy()
    
    # Calculate Indicators
    # Moving Averages
    ma20 = plot_data['Close'].rolling(window=20).mean()
    ma50 = plot_data['Close'].rolling(window=50).mean()
    ma200 = plot_data['Close'].rolling(window=200).mean()
    
    # RSI
    delta = plot_data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = plot_data['Close'].ewm(span=12, adjust=False).mean()
    ema26 = plot_data['Close'].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    
    # Create AddPlots
    apds = []
    
    # 1. Main Panel: MAs
    if not ma20.isnull().all():
        apds.append(mpf.make_addplot(ma20, color='#ffa726', width=1.2)) # Orange
    if not ma50.isnull().all():
        apds.append(mpf.make_addplot(ma50, color='#2962ff', width=1.2)) # Blue
    if not ma200.isnull().all():
        apds.append(mpf.make_addplot(ma200, color='#90caf9', width=1.5)) # Light Blue
        
    # 2. RSI (Panel 2)
    apds.append(mpf.make_addplot(rsi, panel=2, color='#ab47bc', ylabel='RSI', ylim=(0,100), width=1.5))
    
    # 3. MACD (Panel 3)
    apds.append(mpf.make_addplot(macd, panel=3, color='#2962ff', width=1.2, ylabel='MACD'))
    apds.append(mpf.make_addplot(signal, panel=3, color='#ffa726', width=1.2))
    
    # MACD Histogram with colors
    hist_colors = ['#66bb6a' if v >= 0 else '#ef5350' for v in hist]
    apds.append(mpf.make_addplot(hist, panel=3, type='bar', color=hist_colors, alpha=0.5))

    # Market Colors (TradingView Style)
    mc = mpf.make_marketcolors(
        up='#26a69a',        # Green
        down='#ef5350',      # Red
        edge='inherit',
        wick='inherit',
        volume='in',
        ohlc='inherit'
    )
    
    # Style
    s = mpf.make_mpf_style(
        base_mpf_style='yahoo', 
        marketcolors=mc,
        gridstyle=':', 
        gridcolor='#e0e0e0',
        rc={
            'font.family': 'sans-serif',
            'axes.labelsize': 8, 
            'font.size': 9,
            'axes.grid': True
        }
    )
    
    save_path = os.path.abspath(filename + ".png")
    
    kwargs = dict(
        type='candle',
        volume=True,
        figratio=(16, 9), # Landscape 16:9
        figscale=1.5,
        panel_ratios=(4, 1, 1, 1.2), # Main, Vol, RSI, MACD
        tight_layout=True,
        style=s,
        returnfig=True,
        title=f"\n{ticker} Daily Chart",
        savefig=save_path
    )
    
    try:
        fig, axes = mpf.plot(plot_data, addplot=apds, **kwargs)
        
        # Add RSI Levels
        for ax in axes:
            if ax.get_ylabel() == 'RSI':
                ax.axhline(70, color='#ef5350', linestyle='--', alpha=0.5, linewidth=0.8)
                ax.axhline(30, color='#66bb6a', linestyle='--', alpha=0.5, linewidth=0.8)
                ax.fill_between(range(len(rsi)), 70, 30, color='gray', alpha=0.1)

        # Add Watermark (BOLD & CENTERED like reference)
        # Using a large font size and bold weight, centered in the figure
        # The reference shows it spanning across the middle/volume area
        fig.text(0.5, 0.45, '@AkhmalTradingBot', 
                ha='center', va='center', 
                fontsize=40, color='gray', 
                alpha=0.15, rotation=0, weight='bold')
        
        fig.savefig(save_path, dpi=100, bbox_inches='tight')
        plt.close(fig)
        return save_path
        
    except Exception as e:
        print(f"Error plotting: {e}")
        return None
