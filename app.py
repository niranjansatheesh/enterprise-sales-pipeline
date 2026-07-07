import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

# FIX FOR "Name or service not known":
# Supabase direct connections (db.xxx.supabase.co) are IPv6 ONLY. 
# If your internet doesn't support IPv6, it fails. 
# We MUST use the IPv4 Pooler URL instead.
# For the pooler, the username MUST be 'postgres.[project-id]'

DATABASE_URL = "postgresql://postgres.gytdxosyynzrsbefrgfi:Niranjan%4056789@aws-0-eu-central-2.pooler.supabase.com:5432/postgres"

# Stricter connection configuration for Supabase
connect_args = {
    "sslmode": "require"
}

try:
    # Initialize engine with pool_pre_ping to verify connections before use
    engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
except Exception as e:
    st.error(f"Engine Error: {e}")
    st.stop()

st.set_page_config(page_title="Market Data Dashboard", layout="wide")
st.title("📈 Live Market Dashboard")

try:
    # Fetching data using the engine
    df = pd.read_sql("SELECT * FROM daily_market_logs ORDER BY date DESC", engine)
    
    if df.empty:
        st.warning("Database connected, but no data found. Please run the Robot Engine.")
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
    st.error(f"Connection Error: {e}")