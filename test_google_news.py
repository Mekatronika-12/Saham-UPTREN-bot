
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

def get_google_news(ticker):
    # Search query: "{TICKER} saham idx"
    query = f"{ticker.replace('.JK', '')} saham"
    url = f"https://news.google.com/rss/search?q={query}&hl=id-ID&gl=ID&ceid=ID:id"
    
    print(f"Fetching: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"Failed: {response.status_code}")
            return

        root = ET.fromstring(response.content)
        
        # News items are in channel/item
        items = root.findall('./channel/item')
        
        print(f"Found {len(items)} items.")
        
        for item in items[:5]:
            title = item.find('title').text
            link = item.find('link').text
            pubDate = item.find('pubDate').text
            description = item.find('description').text
            
            print(f"- [{pubDate}] {title}")
            print(f"  Desc: {description}")
            print(f"  Link: {link}\n")
            
    except Exception as e:
        print(f"Error: {e}")

get_google_news("BBCA")
get_google_news("BUMI")
get_google_news("GOTO")
