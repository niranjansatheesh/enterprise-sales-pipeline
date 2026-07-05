import yfinance as yf
import pandas as pd
from datetime import datetime
import os

print("🤖 Robot waking up... fetching market data.")

ticker = yf.Ticker("AAPL")
df = ticker.history(period="1d")


record = {
    "Date": datetime.now().strftime("%Y-%m-%d"),
    "Close_Price": round(df['Close'].iloc[0], 2),
    "Volume": int(df['Volume'].iloc[0])
}
new_data = pd.DataFrame([record])


file_path = "daily_market_logs.csv"

if os.path.exists(file_path):
    new_data.to_csv(file_path, mode='a', header=False, index=False)
else:
    new_data.to_csv(file_path, index=False)

print(f"✅ Success! Saved Apple's closing price (${record['Close_Price']}) to the vault.")