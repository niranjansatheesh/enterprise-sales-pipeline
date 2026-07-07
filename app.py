import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os

# --- NEON CLOUD DATABASE CONNECTION ---
# Paste your connection string from neon.tech inside the quotes below!
NEON_URL = "postgresql://neondb_owner:npg_kQPDyGF61SWX@ep-old-butterfly-ahycnjeo.c-3.us-east-1.aws.neon.tech/neondb?sslmode=requirePASTE_YOUR_NEON_CONNECTION_STRING_HERE"

# This setup uses your hardcoded URL when testing locally,
# but automatically uses the GitHub Secret (os.getenv) when running in the cloud!
DATABASE_URL = os.getenv("DATABASE_URL", NEON_URL)

try:
    engine = create_engine(DATABASE_URL)
except Exception as e:
    st.error(f"Engine Error: {e}")
    st.stop()

st.set_page_config(page_title="Market Data Dashboard", layout="wide")
st.title("📈 Live Market Dashboard")

try:
    df = pd.read_sql("SELECT * FROM daily_market_logs ORDER BY date DESC", engine)
    
    if df.empty:
        st.warning("Database connected successfully! But no data found. Please run the Robot Engine (update_data.py) to fetch data.")
    else:
        st.write("### Latest Market Data")
        st.dataframe(df, use_container_width=True)
        
        # Interactive selection
        tickers = sorted(df['ticker'].unique().tolist())
        ticker_choice = st.selectbox("Select a Ticker:", tickers)
        
        filtered_df = df[df['ticker'] == ticker_choice].sort_values('date')
        if not filtered_df.empty:
            st.line_chart(filtered_df.set_index('date')[['close_price']])
except Exception as e:
    st.error(f"Error reading database. If you just connected Neon, run update_data.py first to create the table! Error: {e}")