import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os
import hashlib
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import timedelta
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=SCRIPT_DIR / ".env")

st.set_page_config(page_title="MARKETPULSE", page_icon="📈", layout="wide")

# =========================================================
# USERS (demo login)
# Passwords are stored as SHA-256 hashes, never plain text.
# To add a user: run in Python ->
#   import hashlib; hashlib.sha256("yourpassword".encode()).hexdigest()
# and paste the result below.
# =========================================================
USERS = {
    "niranjan": {
        "name": "Niranjan Satheesh",
        # password: demo123  (CHANGE THIS - generate your own hash!)
        "password_hash": "94bb8fbfe6da8fd10bf1a7f3e6cbb2f0adfc90ee9223aa3aa79ad2f6b1d5b6ee",
        "default_ticker": "NVDA",
    },
    "guest": {
        "name": "Guest User",
        # password: guest
        "password_hash": "84983c60f7daadc1cb8698621f802c0d9f9a3c3c295c810748fb048115c186ec",
        "default_ticker": "AAPL",
    },
}

def check_password(username, password):
    user = USERS.get(username.lower().strip())
    if not user:
        return False
    return hashlib.sha256(password.encode()).hexdigest() == user["password_hash"]

# ---------- session state ----------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = None
if "theme" not in st.session_state:
    st.session_state.theme = "Dark"

# =========================================================
# THEME DEFINITIONS
# =========================================================
THEMES = {
    "Light": dict(
        bg="#FFFFFF", panel="#F7F8FA", text="#232A31", subtext="#5B636A",
        border="#E0E4E9", accent="#0F69FF", up="#00873C", down="#D93025",
        grid="#EEF1F4", volbar="#B0BEC5", plotly="plotly_white",
        upfill="rgba(0,135,60,0.08)", downfill="rgba(217,48,37,0.08)",
    ),
    "Dark": dict(
        bg="#0E1117", panel="#161B22", text="#E8ECEF", subtext="#8A93A0",
        border="#2A3038", accent="#3B82F6", up="#3ED598", down="#F26D6D",
        grid="rgba(255,255,255,0.06)", volbar="#3A424C", plotly="plotly_dark",
        upfill="rgba(62,213,152,0.10)", downfill="rgba(242,109,109,0.10)",
    ),
}
T = THEMES[st.session_state.theme]

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

.stApp {{ background: {T['bg']}; font-family: 'Inter', sans-serif; color: {T['text']}; }}
#MainMenu, header, footer {{ visibility: hidden; }}

.masthead {{ display:flex; align-items:center; justify-content:space-between;
    padding:0.5rem 0 0.9rem 0; border-bottom:1px solid {T['border']}; margin-bottom:1.2rem; }}
.brand-block {{ display:flex; align-items:center; gap:0.7rem; }}
.brand-mark {{ width:38px; height:38px; border-radius:8px; background:{T['accent']};
    display:flex; align-items:center; justify-content:center; }}
.brand-mark svg {{ width:20px; height:20px; }}
.masthead-title {{ font-weight:800; font-size:1.35rem; color:{T['text']}; letter-spacing:-0.02em; }}
.masthead-title .accent {{ color:{T['accent']}; }}
.masthead-tagline {{ font-size:0.7rem; color:{T['subtext']}; margin-top:0.05rem; }}
.masthead-user {{ font-size:0.78rem; color:{T['subtext']}; text-align:right; }}
.masthead-user b {{ color:{T['text']}; }}

.tk-price-row {{ display:flex; align-items:baseline; gap:0.8rem; }}
.tk-price {{ font-size:2.6rem; font-weight:800; color:{T['text']}; letter-spacing:-0.02em; }}
.tk-change-up   {{ font-size:1.15rem; font-weight:700; color:{T['up']}; }}
.tk-change-down {{ font-size:1.15rem; font-weight:700; color:{T['down']}; }}
.tk-asof {{ font-size:0.72rem; color:{T['subtext']}; margin:0.1rem 0 0.6rem 0; }}

.stat-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin:0.6rem 0; }}
.stat-card {{ border:1px solid {T['border']}; border-radius:8px; padding:0.65rem 0.9rem; background:{T['panel']}; }}
.stat-label {{ font-size:0.68rem; color:{T['subtext']}; text-transform:uppercase; letter-spacing:0.06em; }}
.stat-value {{ font-size:1.05rem; font-weight:700; color:{T['text']}; margin-top:2px; }}

.sec-h {{ font-size:0.95rem; font-weight:700; color:{T['text']}; margin:1.2rem 0 0.4rem 0;
    padding-bottom:0.3rem; border-bottom:1px solid {T['border']}; }}

div[role="radiogroup"] {{ gap:0.25rem !important; }}
div[role="radiogroup"] label {{ border:1px solid {T['border']} !important; border-radius:6px !important;
    padding:2px 12px !important; background:{T['panel']} !important; }}

section[data-testid="stSidebar"] {{ background:{T['panel']}; border-right:1px solid {T['border']}; }}
div[data-testid="stDataFrame"] {{ border:1px solid {T['border']}; border-radius:8px; }}
div[data-testid="stAlert"] {{ border:1px solid {T['border']}; border-radius:8px; }}

.login-box {{ max-width:380px; margin:8vh auto 0 auto; padding:2rem;
    border:1px solid {T['border']}; border-radius:12px; background:{T['panel']}; }}
</style>
""", unsafe_allow_html=True)

# =========================================================
# LOGIN SCREEN
# =========================================================
if not st.session_state.authenticated:
    st.markdown(f"""
    <div style="text-align:center; margin-top:6vh;">
        <div class="masthead-title" style="font-size:1.8rem;">MARKET<span class="accent">PULSE</span></div>
        <div class="masthead-tagline">Sign in to your dashboard</div>
    </div>
    """, unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)
            if submitted:
                if check_password(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username.lower().strip()
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
        st.caption("Demo accounts — niranjan / demo123 · guest / guest")
    st.stop()

user = USERS[st.session_state.username]

# =========================================================
# DATABASE
# =========================================================
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    st.error("DATABASE_URL is not configured. Set it in your .env file (local) or app secrets (deployment).")
    st.stop()

@st.cache_resource
def init_connection():
    return create_engine(DATABASE_URL)

engine = init_connection()

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

# =========================================================
# MASTHEAD (with personalized greeting)
# =========================================================
st.markdown(f"""
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
    <div class="masthead-user">Welcome back,<br><b>{user['name']}</b></div>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("No data found yet. Wait for the robot to run!")
    st.stop()

# =========================================================
# SIDEBAR: assets + settings
# =========================================================
st.sidebar.markdown("### Assets")
tickers = sorted(df['ticker'].unique())
default_idx = tickers.index(user['default_ticker']) if user['default_ticker'] in tickers else 0
selected_ticker = st.sidebar.radio("Select a ticker", tickers, index=default_idx,
                                   label_visibility="collapsed")

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Settings")
theme_choice = st.sidebar.radio("Theme", ["Dark", "Light"],
                                index=0 if st.session_state.theme == "Dark" else 1)
if theme_choice != st.session_state.theme:
    st.session_state.theme = theme_choice
    st.rerun()

if st.sidebar.button("Log out", use_container_width=True):
    st.session_state.authenticated = False
    st.session_state.username = None
    st.rerun()

data = df[df['ticker'] == selected_ticker].copy().sort_values('date')

# =========================================================
# TICKER HEADER
# =========================================================
last = data.iloc[-1]
prev = data.iloc[-2] if len(data) >= 2 else last
delta = last['close_price'] - prev['close_price']
pct = (delta / prev['close_price'] * 100) if prev['close_price'] else 0
cls = "tk-change-up" if delta >= 0 else "tk-change-down"
arrow = "▲" if delta >= 0 else "▼"

st.markdown(f"""
<div style="font-size:1.05rem; font-weight:600;">{selected_ticker}</div>
<div class="tk-price-row">
    <span class="tk-price">{last['close_price']:,.2f}</span>
    <span class="{cls}">{arrow} {delta:+,.2f} ({pct:+.2f}%)</span>
</div>
<div class="tk-asof">At close on {last['date'].strftime('%b %d, %Y')}</div>
""", unsafe_allow_html=True)

# =========================================================
# PERIOD SELECTOR
# =========================================================
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

# =========================================================
# STAT CARDS
# =========================================================
period_delta = view['close_price'].iloc[-1] - view['close_price'].iloc[0]
period_pct = period_delta / view['close_price'].iloc[0] * 100 if view['close_price'].iloc[0] else 0
st.markdown(f"""
<div class="stat-grid">
  <div class="stat-card"><div class="stat-label">Period High</div>
      <div class="stat-value">{view['close_price'].max():,.2f}</div></div>
  <div class="stat-card"><div class="stat-label">Period Low</div>
      <div class="stat-value">{view['close_price'].min():,.2f}</div></div>
  <div class="stat-card"><div class="stat-label">Period Change</div>
      <div class="stat-value" style="color:{T['up'] if period_delta>=0 else T['down']}">{period_pct:+.2f}%</div></div>
  <div class="stat-card"><div class="stat-label">Avg Daily Volume</div>
      <div class="stat-value">{view['volume'].mean():,.0f}</div></div>
</div>
""", unsafe_allow_html=True)

# =========================================================
# CHART
# =========================================================
going_up = view['close_price'].iloc[-1] >= view['close_price'].iloc[0]
line_color = T['up'] if going_up else T['down']
fill_color = T['upfill'] if going_up else T['downfill']

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03,
                    row_heights=[0.75, 0.25])

fig.add_trace(go.Scatter(
    x=view['date'], y=view['close_price'], mode='lines', name='Close',
    line=dict(color=line_color, width=2),
    fill='tozeroy', fillcolor=fill_color,
    hovertemplate="%{x|%b %d, %Y}<br>Close: %{y:,.2f}<extra></extra>",
), row=1, col=1)

fig.add_trace(go.Bar(
    x=view['date'], y=view['volume'], name='Volume', marker_color=T['volbar'],
    hovertemplate="%{x|%b %d, %Y}<br>Volume: %{y:,.0f}<extra></extra>",
), row=2, col=1)

ymin, ymax = view['close_price'].min(), view['close_price'].max()
pad = (ymax - ymin) * 0.05 if ymax > ymin else 1
fig.update_yaxes(range=[ymin - pad, ymax + pad], row=1, col=1,
                 gridcolor=T['grid'], tickformat=",.2f")
fig.update_yaxes(row=2, col=1, gridcolor=T['grid'], showticklabels=False)
fig.update_xaxes(gridcolor=T['grid'])

fig.update_layout(
    template=T['plotly'], height=460,
    margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
    font=dict(family="Inter, sans-serif", color=T['text']),
    hoverlabel=dict(bgcolor=T['panel'], bordercolor=T['border'],
                    font=dict(family="Inter, sans-serif", color=T['text'])),
    plot_bgcolor=T['bg'], paper_bgcolor=T['bg'], bargap=0.4,
)

st.plotly_chart(fig, width='stretch')

# =========================================================
# HISTORICAL DATA
# =========================================================
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

csv = view.to_csv(index=False).encode('utf-8')
st.download_button(f"Download {selected_ticker} data (CSV)", csv,
                   file_name=f"{selected_ticker}_history.csv", mime="text/csv")