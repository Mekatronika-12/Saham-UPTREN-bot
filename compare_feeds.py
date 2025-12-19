
import requests
import re
import yfinance as yf

ticker = "HAIS"
url = f"https://www.google.com/finance/quote/{ticker}:IDX"

print(f"Fetching {url}...")
try:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    r = requests.get(url, headers=headers)
    content = r.text
    # Log content length
    print(f"Content Length: {len(content)}")
    
    # Try multiple regex patterns just in case
    # Pattern 1: The standard big price
    matches = re.findall(r'<div class="YMlKec fxKbKc">([\d,.]+)</div>', content)
    if not matches:
         # Pattern 2: Typical meta tag?
         matches = re.findall(r'<meta itemprop="price" content="([\d.]+)"', content)
    
    print(f"Google Finance Matches: {matches}")
    
except Exception as e:
    print(f"Google Error: {e}")

print("\n--- YFinance Comparison ---")
s = yf.Ticker(f"{ticker}.JK")
try:
    print(f"Fast Info Last: {s.fast_info.last_price}")
except:
    print("Fast info fail")
