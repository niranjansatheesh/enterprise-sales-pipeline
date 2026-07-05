import yfinance as yf
import pandas as pd
from datetime import datetime
import os

print("🤖 Robot waking up... fetching market data for all assets.")


tickers = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
all_records = []

for t in tickers:
    try:
        stock = yf.Ticker(t)
        df = stock.history(period="1d")
        
        if not df.empty:
            record = {
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Ticker": t,                                  
                "Close_Price": round(df['Close'].iloc[0], 2),
                "Volume": int(df['Volume'].iloc[0])
            }
            all_records.append(record)
            print(f"✅ Successfully fetched data for {t}")
            
    except Exception as e:
        print(f"❌ Failed to fetch {t}. Error: {e}")


new_data = pd.DataFrame(all_records)


file_path = "daily_market_logs.csv"

if os.path.exists(file_path):
    new_data.to_csv(file_path, mode='a', header=False, index=False)
else:
    new_data.to_csv(file_path, index=False)

print("🎉 Robot going back to sleep. All market data saved to the vault.")
