import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time
import random

def test_yahoo_finance():
    print("Testing Yahoo Finance API...")
    
    def add_delay():
        """Add a random delay between requests to avoid rate limiting"""
        delay = random.uniform(2, 5)
        print(f"Waiting {delay:.2f} seconds to avoid rate limiting...")
        time.sleep(delay)
    
    # Test with a single stock
    symbol = "AAPL"
    print(f"\nTesting {symbol}:")
    try:
        stock = yf.Ticker(symbol)
        # Try different time periods
        print("\nTrying different time periods:")
        for period in ["1d", "5d", "1mo"]:
            print(f"\nPeriod: {period}")
            add_delay()  # Add delay before each request
            history = stock.history(period=period)
            if not history.empty:
                print(f"Data found: {len(history)} rows")
                print(history.tail())
            else:
                print("No data found")
    except Exception as e:
        print(f"Error: {str(e)}")
    
    # Test with multiple stocks
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    print("\nTesting multiple stocks:")
    try:
        add_delay()  # Add delay before batch request
        data = yf.download(symbols, period="1d", group_by='ticker', progress=False)
        if not data.empty:
            print("Data found for multiple stocks:")
            print(data)
        else:
            print("No data found for multiple stocks")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_yahoo_finance() 