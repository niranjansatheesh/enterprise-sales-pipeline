import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import os
import plotly.express as px
from dotenv import load_dotenv

# Tell Python to load the variables from the .env file automatically
load_dotenv()

# --- SETUP & STYLING ---
st.set_page_config(page_title="Market Data Pro", page_icon="📈", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #0E1117; color: white; }
</style>
""", unsafe_allow_html=True)

st.title("📈 Pro Market Analytics")

# --- NEON CLOUD DATABASE CONNECTION ---
NEON_URL = "postgresql://neondb_owner:npg_vD2Iatbq0CiM@ep-still-thunder-atsunix7.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require"
DATABASE_URL = os.getenv("DATABASE_URL", NEON_URL)

@st.cache_resource
def init_connection():
    return create_engine(DATABASE_URL)

engine = init_connection()

# --- DATA FETCHING & ADVANCED ANALYTICS ---
@st.cache_data(ttl=600)
def load_data():
    try:
        with engine.connect() as conn:
            df = pd.read_sql("SELECT * FROM daily_market_logs", conn)
            
            # --- PHASE 3: TECHNICAL INDICATORS MATH ---
            # Sort by date to ensure the rolling math calculates in the correct chronological order
            df = df.sort_values(by=['ticker', 'date'])
            
            # Calculate a 5-Day Simple Moving Average (SMA)
            # (We use 5 days instead of 50 right now so you can see it working sooner!)
            df['5_Day_SMA'] = df.groupby('ticker')['close_price'].transform(lambda x: x.rolling(window=5, min_periods=1).mean())
            
            return df
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return pd.DataFrame()

df = load_data()

# --- UI DASHBOARD ---
if df.empty:
    st.warning("No data found in the database yet. Waiting for the robot to run!")
else:
    # Top Row: Selection
    tickers = df['ticker'].unique()
    selected_ticker = st.selectbox("Select Asset to Analyze", tickers)
    
    ticker_data = df[df['ticker'] == selected_ticker].copy()
    latest_data = ticker_data.iloc[-1]
    
    # KPI Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Latest Close Price", f"${latest_data['close_price']:.2f}")
    col2.metric("Trading Volume", f"{latest_data['volume']:,}")
    col3.metric("5-Day Average Trend", f"${latest_data['5_Day_SMA']:.2f}")
    
    st.markdown("---")
    st.markdown(f"### {selected_ticker} Price vs. Moving Average")
    
    # Advanced Plotly Chart with Multiple Lines
    fig = px.line(
        ticker_data, 
        x='date', 
        # Plotting both the daily price AND our new moving average
        y=['close_price', '5_Day_SMA'], 
        markers=True,
        color_discrete_map={'close_price': '#00FFAA', '5_Day_SMA': '#FF5500'}
    )
    
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", 
        xaxis_title="Date",
        yaxis_title="Price ($)",
        legend_title="Indicators",
        hovermode="x unified" # Makes hovering over the chart show both prices at once!
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.subheader("Raw Data Logs")
    st.dataframe(ticker_data.tail(10))