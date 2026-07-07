import yfinance as yf
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text
import os
import sys

print("🤖 Robot waking up... initializing.")

NEON_URL = "postgresql://neondb_owner:npg_vD2Iatbq0CiM@ep-still-thunder-atsunix7.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require"

DATABASE_URL = os.getenv("DATABASE_URL", NEON_URL)

if "PASTE_YOUR" in DATABASE_URL:
    print("❌ ERROR: You forgot to paste your real Neon link in update_data.py!")
    sys.exit(1)

print("🔌 Testing database connection...")
try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✅ Database connection successful!")
except Exception as e:
    print(f"❌ DATABASE CONNECTION FAILED. Please check your Neon link. Error details: {e}")
    sys.exit(1)

today_str = datetime.now().strftime("%Y-%m-%d")
existing_tickers = []

try:
    with engine.connect() as conn:
        query = text(f"SELECT ticker FROM daily_market_logs WHERE date = '{today_str}'")
        result = conn.execute(query)
        existing_tickers = [row[0] for row in result]
except Exception:
    pass

print("📊 Fetching market data...")
tickers = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
all_records = []

for t in tickers:
    if t in existing_tickers:
        print(f"  ⏭️ Skipped {t} - Data already saved for today.")
        continue

    try:
        stock = yf.Ticker(t)
        df = stock.history(period="1d")
        
        if not df.empty:
            record = {
                "date": today_str,
                "ticker": t,
                "close_price": round(df['Close'].iloc[0], 2),
                "volume": int(df['Volume'].iloc[0])
            }
            all_records.append(record)
            print(f"  ✅ Fetched {t}")
            
    except Exception as e:
        print(f"  ❌ Failed to fetch {t}. Error: {e}")

if all_records:
    new_data = pd.DataFrame(all_records)
    print("💾 Saving data to database...")
    try:
        new_data.to_sql('daily_market_logs', engine, if_exists='append', index=False)
        print("🎉 SUCCESS! Robot going back to sleep. The table is created and data is saved.")
    except Exception as e:
        print(f"⚠️ Error saving data to database: {e}")
else:
    print("😴 Robot going back to sleep. No new data needed today.")
