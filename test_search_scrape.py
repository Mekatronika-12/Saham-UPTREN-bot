
import requests
import re
import yfinance as yf

ticker = "HAIS"
# Search query scraping
url = f"https://www.google.com/search?q=saham+{ticker}"

print(f"Fetching {url}...")
try:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    r = requests.get(url, headers=headers)
    content = r.text
    
    # Try to find the fin-streamer or specific class for big price
    # Google Search widgets often use <div class="IsqQVc NprOob"> or <span class="IsqQVc NprOob">
    # or look for "IDR"
    
    # Rough regex for price near IDR
    # e.g. "242,00 IDR"
    
    # Matches like ">242.00<"
    # But usually comma in ID/Indo: "242,00"
    
    # Let's verify what we get
    # Note: scraping google search is against TOS and brittle, but user demands it.
    
    # Finding the big bold number in the Finance widget
    # Class names are obfuscated.
    # Look for "g-card-section" then finding a number.
    
    # Try finding "242" (I know the number, I want to see the pattern)
    if "242" in content:
        print("Found 242 in content!")
        # Print surrounding
        idx = content.find("242")
        print(content[idx-50:idx+50])
    elif "238" in content:
         print("Found 238 (Yahoo Price) in content")
    else:
         print("Price not found in text")
         
except Exception as e:
    print(f"Search Error: {e}")
