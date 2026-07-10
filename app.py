import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os
import plotly.express as px
from dotenv import load_dotenv

# Load database variables
load_dotenv()

# --- SETUP & STYLING ---
st.set_page_config(page_title="Market Data Pro", page_icon="📈", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #0E1117; color: white; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE CONNECTION ---
NEON_URL = "postgresql://neondb_owner:npg_vD2Iatbq0CiM@ep-still-thunder-atsunix7.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require"
DATABASE_URL = os.getenv("DATABASE_URL", NEON_URL)

@st.cache_resource
def init_connection():
    return create_engine(DATABASE_URL)

engine = init_connection()

# --- DATA FETCHING ---
@st.cache_data(ttl=600)
def load_data():
    try:
        with engine.connect() as conn:
            # Load the data
            df = pd.read_sql("SELECT * FROM daily_market_logs", conn)
            
            # Clean: Only keep the last run of the day to ensure the graph isn't messy
            df = df.drop_duplicates(subset=['ticker', 'date'], keep='last')
            
            # Convert date column to datetime objects
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values(by=['ticker', 'date'])
            
            return df
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()

df = load_data()

# --- UI DASHBOARD ---
st.title("📈 Pro Market Analytics")

if df.empty:
    st.warning("No data found yet. Wait for the robot to run!")
else:
    # 1. Sidebar Section
    st.sidebar.header("Navigation")
    tickers = df['ticker'].unique()
    selected_ticker = st.sidebar.selectbox("Select Asset to Analyze", tickers)
    
    # Filter data for the selected asset
    ticker_data = df[df['ticker'] == selected_ticker].copy()
    
    # 2. Main Dashboard Area
    # Calculate Price Change
    if len(ticker_data) >= 2:
        current_price = ticker_data['close_price'].iloc[-1]
        prev_price = ticker_data['close_price'].iloc[-2]
        delta = current_price - prev_price
        st.metric(label=f"{selected_ticker} Price", value=f"${current_price:.2f}", delta=f"{delta:.2f}")
    else:
        st.subheader(f"{selected_ticker} Current Price")
        st.write(f"${ticker_data['close_price'].iloc[-1]:.2f}")
    
    # Line graph (using width='stretch' instead of use_container_width=True)
    fig = px.line(
        ticker_data, 
        x='date', 
        y='close_price',
        markers=True,
        template="plotly_dark"
    )
    
    fig.update_traces(line_color='#00FFAA', line_width=3)
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Close Price ($)",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    
    st.plotly_chart(fig, width='stretch')
    
    st.markdown("---")
    st.dataframe(ticker_data.tail(10), width='stretch')