import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import os
import sys
import requests 
from dotenv import load_dotenv

# Tell Python to load the variables from the .env file automatically
load_dotenv()

print("🤖 Robot waking up... initializing.")

NEON_URL = "postgresql://neondb_owner:npg_vD2Iatbq0CiM@ep-still-thunder-atsunix7.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require"
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
DATABASE_URL = os.getenv("DATABASE_URL", NEON_URL)

# Placeholder link. We will update this when your dashboard is live!
DASHBOARD_URL = "https://your-future-dashboard.com" 

def send_discord_alert(ticker, change_pct):
    if not DISCORD_WEBHOOK_URL:
        print("⚠️ Discord Webhook URL not set. Alerts will not be sent.")
        return
    
    # Updated message with Markdown link for easy dashboard access
    message = {
        "content": f"🚨 **MARKET ALERT** 🚨\nTicker: **{ticker}** dropped **{change_pct:.2f}%** today!\n[👉 Click here to view the Pro Market Dashboard]({DASHBOARD_URL})"
    }
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=message)
        if response.status_code == 204:
            print(f"📢 Alert successfully sent to Discord for {ticker}")
        else:
            print(f"❌ Discord API returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Failed to send Discord alert: {e}")

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✅ Database connection successful!")
except Exception as e:
    print(f"❌ DATABASE FAILED: {e}")
    sys.exit(1)

today_str = datetime.now().strftime("%Y-%m-%d")

tickers = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
all_records = []

for t in tickers:
    try:
        stock = yf.Ticker(t)
        df = stock.history(period="2d")
        
        if len(df) >= 2:
            prev_close = df['Close'].iloc[-2]
            curr_close = df['Close'].iloc[-1]
            change_pct = ((curr_close - prev_close) / prev_close) * 100
            
            if change_pct <= -5.0:
                send_discord_alert(t, change_pct)
            
            record = {
                "date": today_str,
                "ticker": t,
                "close_price": round(curr_close, 2),
                "volume": int(df['Volume'].iloc[-1])
            }
            all_records.append(record)
            print(f"✅ Fetched {t} (Price: {record['close_price']}, Change: {change_pct:.2f}%)")
            
    except Exception as e:
        print(f"❌ Failed to fetch {t}: {e}")

if all_records:
    new_data = pd.DataFrame(all_records)
    try:
        new_data.to_sql('daily_market_logs', engine, if_exists='append', index=False)
        print("🎉 SUCCESS! Data saved to database and checked for alerts.")
    except Exception as e:
        print(f"⚠️ Error saving to database: {e}")
else:
    print("😴 No new data to save.")
