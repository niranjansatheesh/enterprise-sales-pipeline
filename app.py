import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

# --- DATABASE CONNECTION ---
# 1. Go to Supabase and click the green "Connect" button at the top.
# 2. Copy the URI link they give you.
# 3. Paste it inside the quotes below. 
# 4. Replace [YOUR-PASSWORD] with Niranjan%4056789
DATABASE_URL = "postgresql://postgres:Niranjan%4056789@db.gytdxosyynzrsbefrgfi.supabase.co:5432/postgres"

# This line safely fixes the link for SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

try:
    engine = create_engine(DATABASE_URL)
except Exception as e:
    st.error(f"Error creating database engine: {e}")
    st.stop()

# --- DASHBOARD UI ---
st.set_page_config(page_title="Market Data Dashboard", layout="wide")
st.title("📈 Live Market Dashboard")

try:
    query = "SELECT * FROM daily_market_logs ORDER BY date DESC"
    df = pd.read_sql(query, engine)
    
    if df.empty:
        st.warning("The database is connected, but no data has been found yet.")
    else:
        df['date'] = pd.to_datetime(df['date'])
        
        st.write("### Latest Market Data")
        st.dataframe(df, use_container_width=True)

        st.write("### Price Trend Analysis")
        tickers = sorted(df['ticker'].unique().tolist())
        ticker_choice = st.selectbox("Select a Ticker to view history:", tickers)
        
        filtered_df = df[df['ticker'] == ticker_choice].sort_values('date')
        
        if not filtered_df.empty:
            chart_data = filtered_df.set_index('date')[['close_price']]
            st.line_chart(chart_data)
        else:
            st.info("No data available for the selected ticker.")

except Exception as e:
    st.error(f"Could not connect to database or fetch data. Error: {e}")