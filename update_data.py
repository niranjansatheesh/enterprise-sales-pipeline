import yfinance as yf
import pandas as pd
from datetime import datetime
import os
from sqlalchemy import create_engine

print("🤖 Robot waking up... fetching market data for all assets.")


DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("🚨 DATABASE_URL secret is missing from GitHub Actions!")


if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


engine = create_engine(DATABASE_URL)


tickers = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
all_records = []

for t in tickers:
    try:
        stock = yf.Ticker(t)
        df = stock.history(period="1d")
        
        if not df.empty:
      
            record = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "ticker": t,
                "close_price": round(df['Close'].iloc[0], 2),
                "volume": int(df['Volume'].iloc[0])
            }
            all_records.append(record)
            print(f"✅ Successfully fetched data for {t}")
            
    except Exception as e:
        print(f"❌ Failed to fetch {t}. Error: {e}")


if all_records:
    new_data = pd.DataFrame(all_records)
    
    try:
  
        new_data.to_sql('daily_market_logs', engine, if_exists='append', index=False)
        print("🎉 Success! Robot going back to sleep. All market data saved to the Supabase SQL Vault.")
    except Exception as e:
        print(f"⚠️ Notice: Data might already exist for today or a connection error occurred. Error details: {e}")
