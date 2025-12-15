import asyncio
import yfinance as yf
from stock_analyzer import StockAnalyzer
from chart_generator import generate_stock_chart
import logging

# Setup logging to see errors
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_analysis(ticker):
    print(f"Testing {ticker}...")
    analyzer = StockAnalyzer()
    
    try:
        print("1. Running detailed analysis...")
        # Simulate what the bot does
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, analyzer.analyze_stock_detailed, ticker)
        
        if not result.get("success"):
            print(f"Analysis failed: {result.get('error')}")
            return
            
        print("Analysis success.")
        print(result['narrative'])
        
        print("2. Generating chart...")
        stock = yf.Ticker(ticker)
        hist = await loop.run_in_executor(None, stock.history, "1y")
        
        if hist.empty:
            print("History is empty!")
        else:
            print(f"History length: {len(hist)}")
        
        chart_path = await loop.run_in_executor(None, generate_stock_chart, hist, ticker, "test_chart")
        print(f"Chart path: {chart_path}")
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_analysis("CDIA.JK"))
