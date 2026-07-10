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

st.title("📈 Pro Market Analytics")

# --- DATABASE CONNECTION ---
# Using the standard Neon connection string
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
if df.empty:
    st.warning("No data found yet. Wait for the robot to run!")
else:
    # Sidebar selection
    tickers = df['ticker'].unique()
    selected_ticker = st.selectbox("Select Asset to Analyze", tickers)
    
    ticker_data = df[df['ticker'] == selected_ticker].copy()
    
    # Simple line graph
    st.subheader(f"{selected_ticker} Price Progress")
    
    fig = px.line(
        ticker_data, 
        x='date', 
        y='close_price',
        markers=True,
        template="plotly_dark"
    )
    
    # Customizing the line to look clean
    fig.update_traces(line_color='#00FFAA', line_width=3)
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Close Price ($)",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.dataframe(ticker_data.tail(10), use_container_width=True)