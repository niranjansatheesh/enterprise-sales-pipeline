import yfinance as yf
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine
import os

print("🤖 Robot waking up... fetching market data for all assets.")


NEON_URL = "postgresql://neondb_owner:npg_vD2Iatbq0CiM@ep-still-thunder-atsunix7.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require"

DATABASE_URL = os.getenv("DATABASE_URL", NEON_URL)
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
        print("🎉 Success! Robot going back to sleep. All market data saved to Neon Cloud.")
    except Exception as e:
        print(f"⚠️ Error saving data to database: {e}")
else:
    print("⚠️ No data was fetched today. Database was not updated.")
