import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import os
import random
import re
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import timedelta
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=SCRIPT_DIR / ".env")

st.set_page_config(page_title="MARKETPULSE", page_icon="📈", layout="wide")

# =========================================================
# INITIALIZE SESSION STATE FOR AUTH & THEME
# =========================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = None
if "auth_step" not in st.session_state:
    st.session_state.auth_step = "input"  # "input" or "verify"
if "auth_target" not in st.session_state:
    st.session_state.auth_target = None  # Stores email/phone
if "auth_otp" not in st.session_state:
    st.session_state.auth_otp = None
if "auth_action" not in st.session_state:
    st.session_state.auth_action = "login"  # "login" or "signup"
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght=400;500;600;700;800&display=swap');

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
# DATABASE & GDPR USER TABLE SETUP
# =========================================================
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    st.error("DATABASE_URL is not configured. Set it in your .env file.")
    st.stop()

@st.cache_resource
def init_connection():
    return create_engine(DATABASE_URL)

engine = init_connection()

def setup_users_table():
    """Create a GDPR-compliant users table if it doesn't exist."""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS marketpulse_users (
                id SERIAL PRIMARY KEY,
                identifier VARCHAR(255) UNIQUE NOT NULL,
                default_ticker VARCHAR(10) DEFAULT 'AAPL',
                consent_given BOOLEAN DEFAULT TRUE,
                consent_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

setup_users_table()

@st.cache_data(ttl=600)
def load_data():
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text("SELECT * FROM daily_market_logs ORDER BY date ASC"), conn)
            df['date'] = pd.to_datetime(df['date'])
            df = df.drop_duplicates(subset=['ticker', 'date'], keep='last')
            df = df.sort_values(by=['ticker', 'date'])
            return df
    except Exception as e:
        st.error(f"Database error loading market data: {e}")
        return pd.DataFrame()

df = load_data()

# ---------- Database User CRUD operations ----------
def get_user_db(identifier):
    with engine.connect() as conn:
        res = conn.execute(
            text("SELECT * FROM marketpulse_users WHERE identifier = :id"), 
            {"id": identifier.lower().strip()}
        ).fetchone()
        return res

def create_user_db(identifier):
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO marketpulse_users (identifier, default_ticker, consent_given) VALUES (:id, 'AAPL', TRUE) ON CONFLICT DO NOTHING"),
            {"id": identifier.lower().strip()}
        )

def delete_user_db(identifier):
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM marketpulse_users WHERE identifier = :id"),
            {"id": identifier.lower().strip()}
        )

# =========================================================
# SECURITY UTILITIES
# =========================================================
def is_valid_input(target):
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    phone_regex = r"^\+?[1-9]\d{1,14}$"  # E.164 phone format
    cleaned = target.strip()
    if re.match(email_regex, cleaned):
        return "email"
    elif re.match(phone_regex, cleaned.replace(" ", "").replace("-", "")):
        return "phone"
    return None

def trigger_otp_generation(target):
    otp = f"{random.randint(100000, 999999)}"
    st.session_state.auth_otp = otp
    st.session_state.auth_target = target
    st.session_state.auth_step = "verify"
    
    # ----------------- PRODUCTION IMPLEMENTATION -----------------
    # This is where you would call Twilio (SMS) or SendGrid (Email).
    # For this demo, we simulate delivery by flashing it on the screen.
    # -------------------------------------------------------------
    st.info(f"🔑 Mock Dispatch: OTP sent to **{target}** is **{otp}**")

# =========================================================
# BUILD UPDATES/ALERTS FROM REAL DATA
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
# MASTHEAD
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

# ---------- MESSAGE / UPDATES BOX ----------
with bell_col:
    bell_label = f"🔔 Updates ({unread})" if unread else "🔔 Updates"
    with st.popover(bell_label, use_container_width=True):
        st.markdown("**Market updates**")
        if not alerts:
            st.caption(f"No moves beyond ±{ALERT_THRESHOLD:.0f}% yet. Updates appear here as the robot collects more data.")
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

# ---------- PROFESSIONAL PASSWORDLESS LOGIN & SIGNUP (GDPR COMPLIANT) ----------
with login_col:
    if not st.session_state.authenticated:
        with st.popover("👤 Sign in / Sign up", use_container_width=True):
            
            # Action Picker
            action = st.radio("Choose Action", ["Sign In", "Create Account"], 
                              horizontal=True, label_visibility="collapsed")
            st.session_state.auth_action = "login" if action == "Sign In" else "signup"

            # STEP 1: Enter Email/Phone (and GDPR Consent for Sign Up)
            if st.session_state.auth_step == "input":
                st.markdown(f"**{action}**")
                
                identifier_input = st.text_input(
                    "Email ID or Phone Number", 
                    placeholder="name@company.com or +1234567890",
                    help="Enter your mobile number with country code, or your personal/business email address."
                )

                consent_checked = True
                if st.session_state.auth_action == "signup":
                    # GDPR requirement: Transparent data collection and active consent
                    st.markdown("""
                    <div style="font-size:0.72rem; line-height:1.2; margin-bottom:8px;">
                    <b>GDPR Privacy Notice:</b> We collect and process your email/phone solely to manage authentication. We do not track cross-site nor share your contact info.
                    </div>
                    """, unsafe_allow_html=True)
                    
                    consent_checked = st.checkbox(
                        "I agree to the processing of my authentication details.", 
                        value=False,
                        help="Required to register your profile in our secure database under GDPR rules."
                    )

                if st.button("Send Verification Code", use_container_width=True):
                    validated_type = is_valid_input(identifier_input)
                    if not validated_type:
                        st.error("Please enter a valid Email address or E.164 Phone number.")
                    elif st.session_state.auth_action == "signup" and not consent_checked:
                        st.warning("You must accept the privacy policy statement to register.")
                    else:
                        db_user = get_user_db(identifier_input)
                        if st.session_state.auth_action == "login" and not db_user:
                            st.error("No account associated with this email/phone. Click 'Create Account' to start.")
                        elif st.session_state.auth_action == "signup" and db_user:
                            st.warning("An account with this email/phone already exists. Switching to Sign In.")
                        else:
                            trigger_otp_generation(identifier_input)
                            st.rerun()

            # STEP 2: Verify OTP
            elif st.session_state.auth_step == "verify":
                st.markdown(f"**Verify your identity**")
                st.caption(f"A 6-digit verification code was sent to **{st.session_state.auth_target}**.")
                
                code_input = st.text_input("Enter 6-Digit OTP", max_chars=6, placeholder="000000")
                
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("Verify Code", use_container_width=True, type="primary"):
                        if code_input.strip() == st.session_state.auth_otp:
                            # Authentication succeeds
                            if st.session_state.auth_action == "signup":
                                create_user_db(st.session_state.auth_target)
                            
                            st.session_state.authenticated = True
                            st.session_state.username = st.session_state.auth_target.lower().strip()
                            
                            # Clean credentials
                            st.session_state.auth_step = "input"
                            st.session_state.auth_target = None
                            st.session_state.auth_otp = None
                            st.success("Authenticated successfully!")
                            st.rerun()
                        else:
                            st.error("Invalid verification code. Please try again.")
                
                with col_b2:
                    if st.button("Cancel / Back", use_container_width=True):
                        st.session_state.auth_step = "input"
                        st.session_state.auth_target = None
                        st.session_state.auth_otp = None
                        st.rerun()
                        
    else:
        # USER MANAGE PROFILE (GDPR-Compliant: User Profile + Right to Be Forgotten)
        db_user = get_user_db(st.session_state.username)
        display_name = st.session_state.username if len(st.session_state.username) <= 15 else st.session_state.username[:12] + "..."
        
        with st.popover(f"👤 {display_name}", use_container_width=True):
            st.markdown(f"Logged in as:<br>**{st.session_state.username}**", unsafe_allow_html=True)
            if db_user:
                st.caption(f"Saved default asset: **{db_user[2]}**")
                
            if st.button("Log out", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.username = None
                st.rerun()
            
            st.markdown("---")
            st.markdown("<p style='font-size:0.75rem; font-weight:600; margin-bottom:2px;'>GDPR Portability & Erasure</p>", unsafe_allow_html=True)
            
            # Export user's data (GDPR Article 20 - Data Portability)
            data_export = {
                "identifier": st.session_state.username,
                "preferred_ticker": db_user[2] if db_user else "AAPL",
                "consent_records": "Given dynamically via double-auth registration flow."
            }
            st.download_button(
                "Export My Data (JSON)", 
                data=str(data_export), 
                file_name="my_personal_data.json", 
                mime="application/json",
                use_container_width=True
            )
            
            # Right to Erasure / Right to be Forgotten (GDPR Article 17)
            with st.expander("Delete Account (Irreversible)"):
                st.warning("Deleting your account will instantly remove your records permanently.")
                if st.button("Confirm Delete Data", use_container_width=True, type="primary"):
                    delete_user_db(st.session_state.username)
                    st.session_state.authenticated = False
                    st.session_state.username = None
                    st.success("Account and data completely erased.")
                    st.rerun()

st.markdown('<div class="mast-divider"></div>', unsafe_allow_html=True)

if df.empty:
    st.warning("No data found yet. Wait for the robot to run!")
    st.stop()

# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.markdown("### Assets")
tickers = sorted(df['ticker'].unique())

user_rec = get_user_db(st.session_state.username) if st.session_state.authenticated else None
if user_rec:
    default_ticker_val = user_rec[2]
    default_idx = tickers.index(default_ticker_val) if default_ticker_val in tickers else 0
else:
    default_idx = 0

selected_ticker = st.sidebar.radio("Select a ticker", tickers, index=default_idx,
                                   label_visibility="collapsed")

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Settings")
theme_choice = st.sidebar.radio("Theme", ["Dark", "Light"],
                                index=0 if st.session_state.theme == "Dark" else 1)
if theme_choice != st.session_state.theme:
    st.session_state.theme = theme_choice
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

greeting = ""
if st.session_state.authenticated:
    greeting = f"<span style='color:{T['subtext']}; font-size:0.8rem;'> · Welcome back, {display_name}</span>"

st.markdown(f"""
<div style="font-size:1.05rem; font-weight:600;">{selected_ticker}{greeting}</div>
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