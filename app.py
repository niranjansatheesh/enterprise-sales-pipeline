import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

# --- SETUP & STYLING ---
st.set_page_config(page_title="MARKETPULSE", page_icon="📈", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

.stApp { background: #FFFFFF; font-family: 'Inter', sans-serif; }
#MainMenu, header, footer { visibility: hidden; }

/* ---------- Masthead (light version) ---------- */
.masthead {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0.5rem 0 0.9rem 0; border-bottom: 1px solid #E0E4E9; margin-bottom: 1.2rem;
}
.brand-block { display: flex; align-items: center; gap: 0.7rem; }
.brand-mark {
    width: 38px; height: 38px; border-radius: 8px;
    background: #0F69FF; display: flex; align-items: center; justify-content: center;
}
.brand-mark svg { width: 20px; height: 20px; }
.masthead-title { font-weight: 800; font-size: 1.35rem; color: #232A31; letter-spacing: -0.02em; }
.masthead-title .accent { color: #0F69FF; }
.masthead-tagline { font-size: 0.7rem; color: #5B636A; margin-top: 0.05rem; }
.masthead-status { display: flex; align-items: center; gap: 0.45rem; font-size: 0.72rem; color: #5B636A; }
.status-dot { width: 7px; height: 7px; border-radius: 50%; background: #00873C; }

/* ---------- Ticker header ---------- */
.tk-price-row { display: flex; align-items: baseline; gap: 0.8rem; }
.tk-price { font-size: 2.6rem; font-weight: 800; color: #232A31; letter-spacing: -0.02em; }
.tk-change-up   { font-size: 1.15rem; font-weight: 700; color: #00873C; }
.tk-change-down { font-size: 1.15rem; font-weight: 700; color: #D93025; }
.tk-asof { font-size: 0.72rem; color: #5B636A; margin: 0.1rem 0 0.6rem 0; }

/* ---------- Stat cards ---------- */
.stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 0.6rem 0; }
.stat-card { border: 1px solid #E0E4E9; border-radius: 8px; padding: 0.65rem 0.9rem; background: #FFF; }
.stat-label { font-size: 0.68rem; color: #5B636A; text-transform: uppercase; letter-spacing: 0.06em; }
.stat-value { font-size: 1.05rem; font-weight: 700; color: #232A31; margin-top: 2px; }

/* ---------- Section headers ---------- */
.sec-h { font-size: 0.95rem; font-weight: 700; color: #232A31; margin: 1.2rem 0 0.4rem 0;
         padding-bottom: 0.3rem; border-bottom: 1px solid #E0E4E9; }

/* ---------- Period tabs ---------- */
div[role="radiogroup"] { gap: 0.25rem !important; }
div[role="radiogroup"] label {
    border: 1px solid #E0E4E9 !important; border-radius: 6px !important;
    padding: 2px 12px !important; background: #FFF !important;
}

/* ---------- Sidebar / table ---------- */
section[data-testid="stSidebar"] { background: #F7F8FA; border-right: 1px solid #E0E4E9; }
div[data-testid="stDataFrame"] { border: 1px solid #E0E4E9; border-radius: 8px; }
div[data-testid="stAlert"] { border: 1px solid #E0E4E9; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE CONNECTION (env only — no hardcoded secrets!) ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    st.error("DATABASE_URL is not configured. Set it in your .env file (local) or app secrets (deployment).")
    st.stop()

@st.cache_resource
def init_connection():
    return create_engine(DATABASE_URL)

engine = init_connection()

# --- DATA FETCHING ---
@st.cache_data(ttl=600)
def load_data():
    try:
        with engine.connect() as conn:
            df = pd.read_sql("SELECT * FROM daily_market_logs ORDER BY date ASC", conn)
            df['date'] = pd.to_datetime(df['date'])
            df = df.drop_duplicates(subset=['ticker', 'date'], keep='last')
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
                <path d="M3 17L9 11L13 15L21 6" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M15 6H21V12" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        </div>
        <div>
            <div class="masthead-title">MARKET<span class="accent">PULSE</span></div>
            <div class="masthead-tagline">Daily equity analytics · Powered by the Midnight Data Robot</div>
        </div>
    </div>
    <div class="masthead-status"><span class="status-dot"></span> Data refreshed nightly</div>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("No data found yet. Wait for the robot to run!")
    st.stop()

# --- SIDEBAR ---
st.sidebar.markdown("### Assets")
tickers = sorted(df['ticker'].unique())
selected_ticker = st.sidebar.radio("Select a ticker", tickers, label_visibility="collapsed")

data = df[df['ticker'] == selected_ticker].copy().sort_values('date')

# --- TICKER HEADER (Yahoo style: big price + colored change) ---
last = data.iloc[-1]
prev = data.iloc[-2] if len(data) >= 2 else last
delta = last['close_price'] - prev['close_price']
pct = (delta / prev['close_price'] * 100) if prev['close_price'] else 0
cls = "tk-change-up" if delta >= 0 else "tk-change-down"
arrow = "▲" if delta >= 0 else "▼"

st.markdown(f"""
<div style="font-size:1.05rem; font-weight:600; color:#232A31;">{selected_ticker}</div>
<div class="tk-price-row">
    <span class="tk-price">{last['close_price']:,.2f}</span>
    <span class="{cls}">{arrow} {delta:+,.2f} ({pct:+.2f}%)</span>
</div>
<div class="tk-asof">At close on {last['date'].strftime('%b %d, %Y')}</div>
""", unsafe_allow_html=True)

# --- PERIOD SELECTOR ---
periods = {"1W": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 365, "Max": None}
choice = st.radio("Period", list(periods.keys()), index=len(periods) - 1,
                  horizontal=True, label_visibility="collapsed")

if periods[choice]:
    cutoff = data['date'].max() - timedelta(days=periods[choice])
    view = data[data['date'] >= cutoff]
else:
    view = data
if len(view) < 2:
    view = data

# --- STAT CARDS ---
period_delta = view['close_price'].iloc[-1] - view['close_price'].iloc[0]
period_pct = period_delta / view['close_price'].iloc[0] * 100 if view['close_price'].iloc[0] else 0
st.markdown(f"""
<div class="stat-grid">
  <div class="stat-card"><div class="stat-label">Period High</div>
      <div class="stat-value">{view['close_price'].max():,.2f}</div></div>
  <div class="stat-card"><div class="stat-label">Period Low</div>
      <div class="stat-value">{view['close_price'].min():,.2f}</div></div>
  <div class="stat-card"><div class="stat-label">Period Change</div>
      <div class="stat-value" style="color:{'#00873C' if period_delta>=0 else '#D93025'}">{period_pct:+.2f}%</div></div>
  <div class="stat-card"><div class="stat-label">Avg Daily Volume</div>
      <div class="stat-value">{view['volume'].mean():,.0f}</div></div>
</div>
""", unsafe_allow_html=True)

# --- CHART: area price + volume bars ---
line_color = "#00873C" if view['close_price'].iloc[-1] >= view['close_price'].iloc[0] else "#D93025"
fill_color = "rgba(0,135,60,0.08)" if line_color == "#00873C" else "rgba(217,48,37,0.08)"

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03,
                    row_heights=[0.75, 0.25])

fig.add_trace(go.Scatter(
    x=view['date'], y=view['close_price'], mode='lines', name='Close',
    line=dict(color=line_color, width=2),
    fill='tozeroy', fillcolor=fill_color,
    hovertemplate="%{x|%b %d, %Y}<br>Close: %{y:,.2f}<extra></extra>",
), row=1, col=1)

fig.add_trace(go.Bar(
    x=view['date'], y=view['volume'], name='Volume', marker_color="#B0BEC5",
    hovertemplate="%{x|%b %d, %Y}<br>Volume: %{y:,.0f}<extra></extra>",
), row=2, col=1)

ymin, ymax = view['close_price'].min(), view['close_price'].max()
pad = (ymax - ymin) * 0.05 if ymax > ymin else 1
fig.update_yaxes(range=[ymin - pad, ymax + pad], row=1, col=1,
                 gridcolor="#EEF1F4", tickformat=",.2f")
fig.update_yaxes(row=2, col=1, gridcolor="#EEF1F4", showticklabels=False)
fig.update_xaxes(gridcolor="#EEF1F4")

fig.update_layout(
    template="plotly_white", height=460,
    margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
    font=dict(family="Inter, sans-serif", color="#232A31"),
    hoverlabel=dict(bgcolor="#FFF", bordercolor="#E0E4E9",
                    font=dict(family="Inter, sans-serif", color="#232A31")),
    plot_bgcolor="#FFF", paper_bgcolor="#FFF", bargap=0.4,
)

st.plotly_chart(fig, width='stretch')

# --- HISTORICAL DATA TABLE ---
st.markdown('<div class="sec-h">Historical Data</div>', unsafe_allow_html=True)

hist = view.sort_values('date', ascending=False).copy()
hist['Change %'] = (hist['close_price'].pct_change(-1) * 100)
table = pd.DataFrame({
    "Date": hist['date'].dt.strftime('%b %d, %Y'),
    "Close": hist['close_price'].map(lambda v: f"{v:,.2f}"),
    "Change %": hist['Change %'].map(lambda v: f"{v:+.2f}%" if pd.notna(v) else "—"),
    "Volume": hist['volume'].map(lambda v: f"{v:,.0f}"),
})
st.dataframe(table, width='stretch', hide_index=True, height=340)

# --- DOWNLOAD ---
csv = view.to_csv(index=False).encode('utf-8')
st.download_button(f"Download {selected_ticker} data (CSV)", csv,
                   file_name=f"{selected_ticker}_history.csv", mime="text/csv")