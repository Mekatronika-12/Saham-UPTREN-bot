
import yfinance as yf
import pandas as pd
from datetime import datetime

def test_price(ticker):
    print(f"--- Testing {ticker} ---")
    stock = yf.Ticker(ticker)
    
    # Method 1: History
    hist = stock.history(period="5d")
    print("History Last 2 Rows:")
    print(hist.tail(2)[['Open', 'High', 'Low', 'Close', 'Volume']])
    
    last_hist_price = hist['Close'].iloc[-1]
    last_hist_date = hist.index[-1]
    print(f"History Last Price: {last_hist_price} at {last_hist_date}")
    
    # Method 2: Fast Info
    try:
        fast_price = stock.fast_info['last_price']
        print(f"Fast Info Last Price: {fast_price}")
    except Exception as e:
        print(f"Fast Info Error: {e}")

    # Method 3: Stock Info (Legacy)
    try:
        info_price = stock.info.get('currentPrice') or stock.info.get('regularMarketPrice')
        print(f"Info Price: {info_price}")
    except Exception as e:
        print(f"Info Error: {e}")

test_price("KDTN.JK")
test_price("BBCA.JK")
