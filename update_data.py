import yfinance as yf
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text
import os
import sys

print("🤖 Robot waking up... initializing.")

# --- NEON CLOUD DATABASE CONNECTION ---
# Make sure to completely REPLACE the placeholder text below.
NEON_URL = "postgresql://neondb_owner:npg_vD2Iatbq0CiM@ep-still-thunder-atsunix7.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require"

# Automatically uses local string or GitHub Secret
DATABASE_URL = os.getenv("DATABASE_URL", NEON_URL)

if "PASTE_YOUR" in DATABASE_URL:
    print("❌ ERROR: You forgot to paste your real Neon link in update_data.py!")
    sys.exit(1)

print("🔌 Testing database connection...")
try:
    engine = create_engine(DATABASE_URL)
    # Test the connection immediately
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✅ Database connection successful!")
except Exception as e:
    print(f"❌ DATABASE CONNECTION FAILED. Please check your Neon link. Error details: {e}")
    sys.exit(1)

# 2. Fetch the data
print("📊 Fetching market data...")
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
            print(f"  ✅ Fetched {t}")
            
    except Exception as e:
        print(f"  ❌ Failed to fetch {t}. Error: {e}")

# 3. Save directly to Neon Database
if all_records:
    new_data = pd.DataFrame(all_records)
    print("💾 Saving data to database...")
    try:
        # Pushes the dataframe into your Neon SQL database
        new_data.to_sql('daily_market_logs', engine, if_exists='append', index=False)
        print("🎉 SUCCESS! Robot going back to sleep. The table is created and data is saved.")
    except Exception as e:
        print(f"⚠️ Error saving data to database: {e}")
else:
    print("⚠️ No data was fetched today. Database was not updated.")
