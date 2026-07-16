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
if "notify_pref" not in st.session_state:
    st.session_state.notify_pref = None
if "alerts_read" not in st.session_state:
    st.session_state.alerts_read = False

ALERT_THRESHOLD = 3.0  # % move that counts as an "update"

# =========================================================
# THEMES
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

.brand-row {{ display:flex; align-items:center; gap:0.7rem; }}
.brand-mark {{ width:38px; height:38px; border-radius:8px; background:{T['accent']};
    display:flex; align-items:center; justify-content:center; flex-shrink:0; }}
.brand-mark svg {{ width:20px; height:20px; }}
.masthead-title {{ font-weight:800; font-size:1.35rem; color:{T['text']}; letter-spacing:-0.02em; }}
.masthead-title .accent {{ color:{T['accent']}; }}
.masthead-tagline {{ font-size:0.7rem; color:{T['subtext']}; margin-top:0.05rem; }}
.mast-divider {{ border-bottom:1px solid {T['border']}; margin:0.4rem 0 1.2rem 0; }}

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

.alert-item {{ border:1px solid {T['border']}; border-radius:8px; padding:0.5rem 0.7rem;
    margin-bottom:0.4rem; background:{T['panel']}; font-size:0.8rem; }}
.alert-up {{ color:{T['up']}; font-weight:700; }}
.alert-down {{ color:{T['down']}; font-weight:700; }}

div[role="radiogroup"] {{ gap:0.25rem !important; }}
div[role="radiogroup"] label {{ border:1px solid {T['border']} !important; border-radius:6px !important;
    padding:2px 12px !important; background:{T['panel']} !important; }}

section[data-testid="stSidebar"] {{ background:{T['panel']}; border-right:1px solid {T['border']}; }}
div[data-testid="stDataFrame"] {{ border:1px solid {T['border']}; border-radius:8px; }}
div[data-testid="stAlert"] {{ border:1px solid {T['border']}; border-radius:8px; }}
</style>
""", unsafe_allow_html=True)

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
# BUILD UPDATES/ALERTS FROM REAL DATA
# (significant daily moves across all tickers, most recent first)
# =========================================================
def build_alerts(frame, threshold):
    alerts = []
    if frame.empty:
        return alerts
    for tk, g in frame.groupby('ticker'):
        g = g.sort_values('date')
        g = g.assign(chg=g['close_price'].pct_change() * 100)
        sig = g[abs(g['chg']) >= threshold]
        for _, row in sig.iterrows():
            alerts.append({
                "ticker": tk,
                "date": row['date'],
                "chg": row['chg'],
                "price": row['close_price'],
            })
    alerts.sort(key=lambda a: a['date'], reverse=True)
    return alerts[:15]  # keep the 15 most recent

alerts = build_alerts(df, ALERT_THRESHOLD)
unread = 0 if st.session_state.alerts_read else len(alerts)

# =========================================================
# MASTHEAD: brand left · updates + login top-right
# =========================================================
brand_col, bell_col, login_col = st.columns([6, 1.3, 1.6])

with brand_col:
    st.markdown(f"""
    <div class="brand-row">
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
    """, unsafe_allow_html=True)

# ---------- MESSAGE / UPDATES BOX (top-right) ----------
with bell_col:
    bell_label = f"🔔 Updates ({unread})" if unread else "🔔 Updates"
    with st.popover(bell_label, use_container_width=True):
        st.markdown("**Market updates**")
        if not alerts:
            st.caption(f"No moves beyond ±{ALERT_THRESHOLD:.0f}% yet. "
                       "Updates appear here as the robot collects more data.")
        else:
            st.session_state.alerts_read = True
            for a in alerts:
                cls = "alert-up" if a['chg'] >= 0 else "alert-down"
                arrow = "▲" if a['chg'] >= 0 else "▼"
                st.markdown(
                    f"<div class='alert-item'><b>{a['ticker']}</b> "
                    f"<span class='{cls}'>{arrow} {a['chg']:+.2f}%</span> "
                    f"→ {a['price']:,.2f}<br>"
                    f"<span style='color:{T['subtext']}; font-size:0.7rem;'>{a['date'].strftime('%b %d, %Y')}</span></div>",
                    unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Get updates by message**")
        st.caption("Big moves are pushed to our Discord channel automatically. "
                   "Leave a contact to be added to message alerts.")
        contact = st.text_input("Email or phone", key="notify_contact",
                                placeholder="you@email.com / +33 6 XX XX XX XX")
        if st.button("Subscribe", key="notify_btn", use_container_width=True):
            if contact.strip():
                st.session_state.notify_pref = contact.strip()
                st.success("Saved! You'll be added to message updates.")
            else:
                st.warning("Please enter an email or phone number.")
        if st.session_state.notify_pref:
            st.caption(f"Subscribed: {st.session_state.notify_pref}")
        # NOTE (dev): real SMS/email delivery requires a service like Twilio /
        # SendGrid — wire it here. The Discord webhook in update_data.py is the
        # channel that actually pushes alerts today.

# ---------- LOGIN (top-right) ----------
with login_col:
    if not