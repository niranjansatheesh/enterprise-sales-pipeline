import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import os
import sys
import requests 
from dotenv import load_dotenv

load_dotenv()

print("🤖 Robot waking up... initializing.")

NEON_URL = "postgresql://neondb_owner:npg_vD2Iatbq0CiM@ep-still-thunder-atsunix7.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require"
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
DATABASE_URL = os.getenv("DATABASE_URL", NEON_URL)

DASHBOARD_URL = "https://your-future-dashboard.com" 

def send_discord_alert(ticker, change_pct):
    if not DISCORD_WEBHOOK_URL:
        print("⚠️ Discord Webhook URL not set. Alerts will not be sent.")
        return
    
    webhook_url = DISCORD_WEBHOOK_URL.strip().strip('"').strip("'")
    
    if "YOUR_ACTUAL_ID" in webhook_url or "YOUR_PASTED_URL" in webhook_url:
        print(f"🛑 STOP! The robot detected placeholder text in your URL.")
        print(f"🛑 Your current link is: {webhook_url}")
        print("🛑 Please open your .env file, delete the contents, and paste your REAL Discord Webhook link.")
        return
    
    message = {
        "content": f"🚨 **MARKET ALERT** 🚨\nTicker: **{ticker}** dropped **{change_pct:.2f}%** today!\n👉 **View Dashboard:** {DASHBOARD_URL}"
    }
    
    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(webhook_url, json=message, headers=headers)
        
        if response.status_code in [200, 204]:
            print(f"📢 Alert successfully sent to Discord for {ticker}")
        else:
            print(f"❌ Discord API returned status {response.status_code}")
            print(f"🔍 Error Details: {response.text}") 
            
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
            
            if change_pct <= -3.0:
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
