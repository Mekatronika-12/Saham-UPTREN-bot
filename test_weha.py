
import asyncio
from stock_analyzer import StockAnalyzer

async def test_weha():
    analyzer = StockAnalyzer()
    print("Analyzing WEHA.JK...")
    result = await asyncio.to_thread(analyzer.analyze_stock_detailed, "WEHA.JK")
    
    if result['success']:
        print("✅ Analysis Successful!")
        print(result['message'])
    else:
        print(f"❌ Analysis Failed: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(test_weha())
