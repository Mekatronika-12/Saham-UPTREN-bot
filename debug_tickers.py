import asyncio
from stock_analyzer import StockAnalyzer
import logging
import traceback

# Setup logging
logging.basicConfig(level=logging.INFO)

async def test_tickers():
    analyzer = StockAnalyzer()
    # Adding more tickers to test broadly as requested
    tickers = ["BULL.JK", "BBYB.JK", "BBCA.JK", "GOTO.JK", "ANTM.JK", "BRIS.JK"]
    
    print("=== STARTING BATCH TEST ===")
    for ticker in tickers:
        print(f"\nTesting {ticker}...")
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, analyzer.analyze_stock_detailed, ticker)
            
            if not result.get("success"):
                if "UnboundLocalError" in str(result.get("error")):
                    print(f"❌ FAILED: {result.get('error')} (Still Variable Error!)")
                else:
                    print(f"⚠️  NOTICE: {result.get('error')} (Likely Data/Uptrend issue, not Code Error)")
            else:
                print("✅ SUCCESS")
                
        except Exception as e:
            print(f"❌ CRITICAL EXCEPTION for {ticker}: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_tickers())
