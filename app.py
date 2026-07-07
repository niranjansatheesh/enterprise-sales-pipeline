import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, inspect
import os

# --- NEON CLOUD DATABASE CONNECTION ---
# Make sure to completely REPLACE the placeholder text.
# It should end cleanly with "?sslmode=require" and NOTHING else.
NEON_URL = "postgresql://neondb_owner:YOUR_ACTUAL_PASSWORD@ep-your-neon-host.eu-central-1.aws.neon.tech/neondb?sslmode=require"

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
    # Check if the table exists before querying
    inspector = inspect(engine)
    if 'daily_market_logs' not in inspector.get_table_names():
        st.warning("Database connected successfully! 🚀 But the data table doesn't exist yet. Please open your terminal and run `python update_data.py` to fetch the first batch of data.")
    else:
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
    st.error(f"Error reading database: {e}")