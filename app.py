import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dotenv import load_dotenv

# Tell Python to load the variables from the .env file automatically
load_dotenv()

# --- SETUP & STYLING ---
st.set_page_config(page_title="Market Data Pro", page_icon="📈", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #0E1117; color: white; }
div[data-testid="stMetricValue"] { color: #00FFAA; }
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
            
            # Sort by date to ensure chronological math
            df = df.sort_values(by=['ticker', 'date'])
            
            # Since we only have close_price, we will simulate open/high/low for the candlestick 
            # (In a real app, your robot would fetch all 4 of these!)
            df['open'] = df['close_price'] * 0.99
            df['high'] = df['close_price'] * 1.02
            df['low'] = df['close_price'] * 0.98
            
            # Calculate a 5-Day Simple Moving Average (SMA)
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
    
    # --- PROFESSIONAL SUBPLOT CHART ---
    # Create a layout with 2 rows: The large price chart on top, smaller volume chart below
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, row_heights=[0.7, 0.3])

    # 1. Candlestick Chart (Top Row)
    fig.add_trace(go.Candlestick(
        x=ticker_data['date'],
        open=ticker_data['open'],
        high=ticker_data['high'],
        low=ticker_data['low'],
        close=ticker_data['close_price'],
        name='Price'
    ), row=1, col=1)

    # 2. Moving Average Overlay (Top Row)
    fig.add_trace(go.Scatter(
        x=ticker_data['date'], 
        y=ticker_data['5_Day_SMA'], 
        line=dict(color='#FF5500', width=2),
        name='5-Day SMA'
    ), row=1, col=1)

    # 3. Volume Bar Chart (Bottom Row)
    # Color volume green if price went up, red if it went down
    colors = ['#FF4A4A' if ticker_data['open'].iloc[i] > ticker_data['close_price'].iloc[i] else '#00FFAA' for i in range(len(ticker_data))]
    fig.add_trace(go.Bar(
        x=ticker_data['date'], 
        y=ticker_data['volume'],
        marker_color=colors,
        name='Volume'
    ), row=2, col=1)

    # Make it look dark and professional
    fig.update_layout(
        title=f"<b>{selected_ticker} Advanced Chart</b>",
        yaxis_title="Price ($)",
        yaxis2_title="Volume",
        xaxis2_title="Date",
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis_rangeslider_visible=False, # Hide the clunky slider at the bottom
        height=600,
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.subheader("Raw Data Logs")
    st.dataframe(ticker_data.tail(10), use_container_width=True)