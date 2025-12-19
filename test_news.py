
import yfinance as yf
import json

def test_news(ticker):
    stock = yf.Ticker(ticker)
    try:
        news = stock.news
        print(json.dumps(news, indent=2))
    except Exception as e:
        print(e)

test_news("BBCA.JK")
test_news("GOTO.JK")
