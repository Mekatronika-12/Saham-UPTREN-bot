
import asyncio
from stock_analyzer import StockAnalyzer
import traceback

async def debug():
    analyzer = StockAnalyzer()
    print("Debugging FUTR.JK...")
    try:
        # analyze_stock_detailed calls yfinance internally
        result = analyzer.analyze_stock_detailed("FUTR.JK")
        if not result.get("success"):
            print(f"FAILED (Logical): {result.get('error')}")
            # If error is stored in result
        else:
            print("SUCCESS")
            print(result)
            
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug())
