import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os
import plotly.express as px
from dotenv import load_dotenv

# Load database variables
load_dotenv()

# --- SETUP & STYLING ---
st.set_page_config(page_title="MarketPulse", page_icon="📈", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* ---------- Base ---------- */
.stApp {
    background: radial-gradient(circle at 15% 0%, #101820 0%, #0A0E13 45%, #06080B 100%);
    color: #E8ECEF;
    font-family: 'Space Grotesk', sans-serif;
}

/* Hide default streamlit chrome */
#MainMenu, header, footer { visibility: hidden; }

/* ---------- Top masthead ---------- */
.masthead {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.6rem 0 1.3rem 0;
    border-bottom: 1px solid rgba(212, 175, 55, 0.25);
    margin-bottom: 1.8rem;
}
.brand-block {
    display: flex;
    align-items: center;
    gap: 0.9rem;
}
.brand-mark {
    width: 42px;
    height: 42px;
    border-radius: 8px;
    border: 1px solid rgba(212, 175, 55, 0.4);
    background: linear-gradient(155deg, #171B21 0%, #0D1116 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.brand-mark svg { width: 22px; height: 22px; }
.brand-text { display: flex; flex-direction: column; line-height: 1.15; }
.masthead-title {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 1.65rem;
    letter-spacing: -0.01em;
    color: #F4F1EA;
}
.masthead-title .accent { color: #D4AF37; }
.masthead-tagline {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #6B7684;
    margin-top: 0.15rem;
}
.masthead-status {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #8A93A0;
}
.status-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #3ED598;
    box-shadow: 0 0 6px rgba(62, 213, 152, 0.7);
}

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {
    background: #0B0F14;
    border-right: 1px solid rgba(212, 175, 55, 0.15);
}
section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] label {
    font-family: 'JetBrains Mono', monospace !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.78rem !important;
    color: #9AA5B1 !important;
}

/* ---------- Metric card ---------- */
div[data-testid="stMetric"] {
    background: linear-gradient(155deg, #11161D 0%, #0D1116 100%);
    border: 1px solid rgba(212, 175, 55, 0.18);
    border-radius: 10px;
    padding: 1.1rem 1.4rem;
    box-shadow: 0 4px 18px rgba(0,0,0,0.35);
}
div[data-testid="stMetricLabel"] {
    font-family: 'JetBrains Mono', monospace !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-size: 0.75rem !important;
    color: #8A93A0 !important;
}
div[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    color: #F4F1EA !important;
}

/* ---------- Section labels ---------- */
.section-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #D4AF37;
    margin: 1.6rem 0 0.6rem 0;
    display: flex;
    align-items: center;
    gap: 0.6rem;
}
.section-label::after {
    content: "";
    flex: 1;
    height: 1px;
    background: rgba(212, 175, 55, 0.2);
}

/* ---------- Chart container ---------- */
div[data-testid="stPlotlyChart"] {
    background: #0D1116;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    padding: 0.6rem;
}

/* ---------- Dataframe ---------- */
div[data-testid="stDataFrame"] {
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    overflow: hidden;
}

/* ---------- Warning box ---------- */
div[data-testid="stAlert"] {
    background: #14181F;
    border: 1px solid rgba(212, 175, 55, 0.25);
    border-radius: 8px;
}
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

# --- MASTHEAD ---
st.markdown("""
<div class="masthead">
    <div class="brand-block">
        <div class="brand-mark">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M3 17L9 11L13 15L21 6" stroke="#D4AF37" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M15 6H21V12" stroke="#D4AF37" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        </div>
        <div class="brand-text">
            <div class="masthead-title">MARKET<span class="accent">PULSE</span></div>
            <div class="masthead-tagline">Real-time equity analytics terminal</div>
        </div>
    </div>
    <div class="masthead-status">
        <span class="status-dot"></span>
        Live · refreshed every 10 min
    </div>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("No data found yet. Wait for the robot to run!")
else:
    # 1. Sidebar Section
    st.sidebar.markdown("## Navigation")
    tickers = df['ticker'].unique()
    selected_ticker = st.sidebar.selectbox("Select Asset to Analyze", tickers)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f"<div style='font-family:JetBrains Mono, monospace; font-size:0.72rem; color:#6B7684;'>"
        f"TRACKED ASSETS<br><span style='color:#D4AF37; font-size:1.1rem;'>{len(tickers)}</span>"
        f"</div>", unsafe_allow_html=True
    )

    # Filter data for the selected asset
    ticker_data = df[df['ticker'] == selected_ticker].copy()
    
    # 2. Main Dashboard Area
    st.markdown('<div class="section-label">Snapshot</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 2])

    # Calculate Price Change
    if len(ticker_data) >= 2:
        current_price = ticker_data['close_price'].iloc[-1]
        prev_price = ticker_data['close_price'].iloc[-2]
        delta = current_price - prev_price
        pct = (delta / prev_price * 100) if prev_price else 0
        with col1:
            st.metric(label=f"{selected_ticker} Price", value=f"${current_price:.2f}", delta=f"{delta:.2f}")
        with col2:
            st.metric(label="Change %", value=f"{pct:.2f}%")
        with col3:
            st.metric(label="Observations", value=f"{len(ticker_data)}")
    else:
        st.subheader(f"{selected_ticker} Current Price")
        st.write(f"${ticker_data['close_price'].iloc[-1]:.2f}")
    
    # Line graph (using width='stretch' instead of use_container_width=True)
    st.markdown('<div class="section-label">Price History</div>', unsafe_allow_html=True)

    fig = px.line(
        ticker_data, 
        x='date', 
        y='close_price',
        markers=True,
        template="plotly_dark"
    )
    
    fig.update_traces(line_color='#D4AF37', line_width=2.5, marker=dict(size=5, color='#F4F1EA'))
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Close Price ($)",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="JetBrains Mono, monospace", color="#C7CDD4"),
        margin=dict(l=10, r=10, t=20, b=10),
        hoverlabel=dict(bgcolor="#11161D", font_family="JetBrains Mono, monospace"),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.05)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)")
    
    st.plotly_chart(fig, width='stretch')
    
    st.markdown('<div class="section-label">Recent Records</div>', unsafe_allow_html=True)
    st.dataframe(ticker_data.tail(10), width='stretch')