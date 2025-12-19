
import yfinance as yf
ticker = "BBCA.JK"
print(f"Fetching {ticker}...")
try:
    dat = yf.Ticker(ticker).history(period="1mo")
    print(dat.tail())
except Exception as e:
    print(f"Error: {e}")
