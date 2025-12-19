
from stock_analyzer import StockAnalyzer
import json

analyzer = StockAnalyzer()
print("Analyzing BUMI...")
result = analyzer.analyze_stock_detailed("BUMI.JK")

if result.get("success"):
    print("--- RESULT MESSAGE ---")
    print(result['message'])
else:
    print("--- FAIL ---")
    print(result)
