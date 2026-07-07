import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

# --- BULLETPROOF CONNECTION CONFIGURATION ---
# Using URL.create() prevents Python from mangling special characters 
# in your password (like '@') or your username.
db_url = URL.create(
    drivername="postgresql",
    username="postgres.gytdxosyynzrsbefrgfi", # Must include project ID for pooler
    password="Niranjan@56789",              # Type EXACTLY as it is, no %40 needed!
    host="aws-0-eu-central-2.pooler.supabase.com",
    port=6543,
    database="postgres"
)

try:
    # Initialize engine with SSL requirement and connection testing
    engine = create_engine(db_url, connect_args={"sslmode": "require"}, pool_pre_ping=True)
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
    st.info("💡 Note: If you still see 'tenant/user not found' with this exact code, Supabase is actively experiencing an outage in your region (eu-central-2), or your database password needs to be reset in the Supabase dashboard.")