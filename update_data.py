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
            
            # Triggers if the stock falls or meets your test threshold
            if change_pct <= 100.0:
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