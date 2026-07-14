import yfinance as yf
import pandas as pd
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

print("🤖 Robot waking up... initializing.")

# --- CONFIGURATION (no secrets in code!) ---
DATABASE_URL = os.getenv("DATABASE_URL")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Set this to your real deployed dashboard link once deployed.
# A dashboard URL is not a secret, so hardcoding the real one is fine too.
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "https://your-app-name.streamlit.app")

# Alert threshold: alert when a stock moves this much (%) in EITHER direction.
ALERT_THRESHOLD_PCT = float(os.getenv("ALERT_THRESHOLD_PCT", "3.0"))

if not DATABASE_URL:
    print("❌ DATABASE_URL is not set.")
    print("   → Locally: add it to your .env file.")
    print("   → GitHub Actions: add it under Settings → Secrets and variables → Actions.")
    sys.exit(1)


def send_discord_alert(ticker, change_pct):
    if not DISCORD_WEBHOOK_URL:
        print("⚠️ Discord Webhook URL not set. Alerts will not be sent.")
        return

    webhook_url = DISCORD_WEBHOOK_URL.strip().strip('"').strip("'")

    if "YOUR_ACTUAL_ID" in webhook_url or "YOUR_PASTED_URL" in webhook_url:
        print("🛑 STOP! The robot detected placeholder text in your URL.")
        print(f"🛑 Your current link is: {webhook_url}")
        print("🛑 Please open your .env file and paste your REAL Discord Webhook link.")
        return

    direction = "📈" if change_pct >= 0 else "📉"

    payload = {
        "embeds": [
            {
                "title": f"{direction} {ticker} moved {change_pct:+.2f}% — View Live Dashboard",
                "url": DASHBOARD_URL,  # Clicking the title opens the dashboard
                "description": (
                    f"Significant daily movement detected for **{ticker}**.\n\n"
                    f"{direction} **Change:** {change_pct:+.2f}%\n\n"
                    f"👉 **[Open Dashboard]({DASHBOARD_URL})**"
                ),
                "color": 15158332 if change_pct < 0 else 3066993,  # red drop, green gain
                "footer": {"text": "Midnight Data Robot"},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ]
    }

    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(webhook_url, json=payload, headers=headers)

        if response.status_code in [200, 204]:
            print(f"📢 Embed alert successfully sent to Discord for {ticker}")
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

            # Alert only on significant moves (up OR down)
            if abs(change_pct) >= ALERT_THRESHOLD_PCT:
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