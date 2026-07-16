import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import os
import hashlib
import random
import re
from pathlib import Path
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dotenv import load_dotenv
from twilio.rest import Client
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=SCRIPT_DIR / ".env")

st.set_page_config(page_title="MARKETPULSE", page_icon="📈", layout="wide")

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

if "theme" not in st.session_state:
    st.session_state.theme = "Dark"
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = None
if "auth_step" not in st.session_state:
    st.session_state.auth_step = "login"  # login, signup, otp_verify
if "auth_otp" not in st.session_state:
    st.session_state.auth_otp = None
if "auth_target" not in st.session_state:
    st.session_state.auth_target = None
if "otp_attempts" not in st.session_state:
    st.session_state.otp_attempts = 0
if "alerts_read" not in st.session_state:
    st.session_state.alerts_read = False

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

.auth-box {{ max-width:420px; margin:6vh auto 0; padding:2rem;
    border:1px solid {T['border']}; border-radius:12px; background:{T['panel']}; }}
.auth-title {{ font-size:1.5rem; font-weight:800; color:{T['text']}; margin-bottom:0.5rem; }}
.auth-sub {{ font-size:0.85rem; color:{T['subtext']}; margin-bottom:1.2rem; }}
.gdpr-box {{ font-size:0.75rem; color:{T['subtext']}; background:rgba(0,0,0,0.1);
    padding:0.8rem; border-radius:8px; margin:0.8rem 0; line-height:1.5; }}

.tk-price-row {{ display:flex; align-items:baseline; gap:0.8rem; }}
.tk-price {{ font-size:2.6rem; font-weight:800; color:{T['text']}; letter-spacing:-0.02em; }}
.tk-change-up   {{ font-size:1.15rem; font-weight:700; color:{T['up']}; }}
.tk-change-down {{ font-size:1.15rem; font-weight:700; color:{T['down']}; }}

.stat-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin:0.6rem 0; }}
.stat-card {{ border:1px solid {T['border']}; border-radius:8px; padding:0.65rem 0.9rem; background:{T['panel']}; }}
.stat-label {{ font-size:0.68rem; color:{T['subtext']}; text-transform:uppercase; }}
.stat-value {{ font-size:1.05rem; font-weight:700; color:{T['text']}; margin-top:2px; }}

.sec-h {{ font-size:0.95rem; font-weight:700; color:{T['text']}; margin:1.2rem 0 0.4rem 0;
    padding-bottom:0.3rem; border-bottom:1px solid {T['border']}; }}

div[role="radiogroup"] {{ gap:0.25rem !important; }}
section[data-testid="stSidebar"] {{ background:{T['panel']}; border-right:1px solid {T['border']}; }}
div[data-testid="stDataFrame"] {{ border:1px solid {T['border']}; border-radius:8px; }}
</style>
""", unsafe_allow_html=True)

# =========================================================
# DATABASE SETUP (users table + market data)
# =========================================================
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    st.error("DATABASE_URL not configured.")
    st.stop()

@st.cache_resource
def init_db():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # Create users table (GDPR-compliant)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email_or_phone VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                gdpr_consent BOOLEAN DEFAULT FALSE,
                data_deletion_requested BOOLEAN DEFAULT FALSE,
                data_deletion_date TIMESTAMP,
                notification_preference VARCHAR(50) DEFAULT 'email',
                deleted_at TIMESTAMP
            );
        """))
        conn.commit()
    return engine

engine = init_db()

@st.cache_data(ttl=600)
def load_market_data():
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

# =========================================================
# HELPER FUNCTIONS
# =========================================================
def is_valid_input(target):
    """Validate email or phone; return type or None."""
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    phone_regex = r'^\+?1?\d{9,15}$'
    
    if re.match(email_regex, target.strip()):
        return "email"
    elif re.match(phone_regex, target.strip().replace(" ", "").replace("-", "")):
        return "phone"
    return None

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def user_exists(email_or_phone):
    try:
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT id FROM users WHERE email_or_phone = :target AND deleted_at IS NULL"
            ), {"target": email_or_phone.strip()})
            return result.fetchone() is not None
    except:
        return False

def create_user(email_or_phone, password, full_name, gdpr_consent):
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO users (email_or_phone, password_hash, full_name, gdpr_consent)
                VALUES (:email_or_phone, :password_hash, :full_name, :gdpr_consent)
            """), {
                "email_or_phone": email_or_phone.strip(),
                "password_hash": hash_password(password),
                "full_name": full_name,
                "gdpr_consent": gdpr_consent,
            })
            conn.commit()
            return True
    except Exception as e:
        st.error(f"Error creating user: {e}")
        return False

def verify_credentials(email_or_phone, password):
    try:
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT id, full_name FROM users WHERE email_or_phone = :target AND password_hash = :pwd AND deleted_at IS NULL"
            ), {
                "target": email_or_phone.strip(),
                "pwd": hash_password(password),
            })
            user = result.fetchone()
            if user:
                conn.execute(text(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = :uid"
                ), {"uid": user[0]})
                conn.commit()
                return user[1]  # full_name
            return None
    except:
        return None

def send_otp_sms(phone, otp):
    """Send OTP via Twilio SMS."""
    try:
        client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
        client.messages.create(
            body=f"Your MARKETPULSE verification code is: {otp}. Expires in 10 minutes.",
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            to=phone.strip()
        )
        return True
    except Exception as e:
        st.error(f"SMS failed: {e}")
        return False

def send_otp_email(email, otp):
    """Send OTP via SendGrid email."""
    try:
        message = Mail(
            from_email=os.getenv("SENDGRID_FROM_EMAIL"),
            to_emails=email.strip(),
            subject="Your MARKETPULSE Verification Code",
            html_content=f"""
            <div style='font-family:Inter,sans-serif; max-width:500px;'>
                <h2>Verify Your Email</h2>
                <p>Your MARKETPULSE verification code is:</p>
                <h1 style='color:#0F69FF; letter-spacing:2px;'>{otp}</h1>
                <p style='color:#666;'>This code expires in 10 minutes.</p>
                <hr style='border:none; border-top:1px solid #eee; margin:1.5rem 0;'/>
                <p style='font-size:0.85rem; color:#999;'>
                    If you didn't request this code, please ignore this email.
                </p>
            </div>
            """
        )
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        sg.send(message)
        return True
    except Exception as e:
        st.error(f"Email failed: {e}")
        return False

def request_data_deletion(email_or_phone):
    """Mark account for GDPR deletion (30-day grace period)."""
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE users SET data_deletion_requested = TRUE,
                data_deletion_date = CURRENT_TIMESTAMP + INTERVAL '30 days'
                WHERE email_or_phone = :target
            """), {"target": email_or_phone.strip()})
            conn.commit()
            return True
    except:
        return False

# =========================================================
# AUTHENTICATION UI
# =========================================================
if not st.session_state.authenticated:
    st.markdown(f"""
    <div style="text-align:center; margin-top:4vh;">
        <div class="masthead-title" style="font-size:1.8rem;">MARKET<span class="accent">PULSE</span></div>
        <div class="masthead-tagline">Professional Market Analytics</div>
    </div>
    """, unsafe_allow_html=True)
    
    _, auth_col, _ = st.columns([1, 1.2, 1])
    
    with auth_col:
        # ===== LOGIN STEP =====
        if st.session_state.auth_step == "login":
            st.markdown('<div class="auth-box">', unsafe_allow_html=True)
            st.markdown('<div class="auth-title">Sign In</div>', unsafe_allow_html=True)
            st.markdown('<div class="auth-sub">Access your dashboard</div>', unsafe_allow_html=True)
            
            with st.form("login_form"):
                email_or_phone = st.text_input("Email or Phone", placeholder="you@example.com or +33 6 XX XX XX XX")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Sign In", use_container_width=True)
                
                if submitted:
                    if not email_or_phone.strip() or not password.strip():
                        st.error("Please fill all fields.")
                    else:
                        full_name = verify_credentials(email_or_phone, password)
                        if full_name:
                            st.session_state.authenticated = True
                            st.session_state.username = email_or_phone.strip()
                            st.rerun()
                        else:
                            st.error("Invalid email/phone or password.")
            
            st.markdown("---")
            if st.button("Create Account", use_container_width=True, key="signup_btn"):
                st.session_state.auth_step = "signup"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        # ===== SIGNUP STEP =====
        elif st.session_state.auth_step == "signup":
            st.markdown('<div class="auth-box">', unsafe_allow_html=True)
            st.markdown('<div class="auth-title">Create Account</div>', unsafe_allow_html=True)
            st.markdown('<div class="auth-sub">Join MARKETPULSE</div>', unsafe_allow_html=True)
            
            with st.form("signup_form"):
                full_name = st.text_input("Full Name", placeholder="John Doe")
                email_or_phone = st.text_input("Email or Phone", placeholder="you@example.com or +33 6 XX XX XX XX")
                password = st.text_input("Password", type="password", placeholder="Min. 8 chars")
                password_confirm = st.text_input("Confirm Password", type="password")
                
                st.markdown('<div class="gdpr-box">', unsafe_allow_html=True)
                st.markdown("""
                ✅ **GDPR Compliance**
                - We encrypt and protect your data
                - You can delete your account anytime
                - No data sharing without consent
                - Read our [Privacy Policy](#)
                """)
                gdpr_consent = st.checkbox("I agree to the Terms & Privacy Policy")
                st.markdown('</div>', unsafe_allow_html=True)
                
                submitted = st.form_submit_button("Create Account", use_container_width=True)
                
                if submitted:
                    if not all([full_name, email_or_phone, password, password_confirm]):
                        st.error("Please fill all fields.")
                    elif len(password) < 8:
                        st.error("Password must be at least 8 characters.")
                    elif password != password_confirm:
                        st.error("Passwords don't match.")
                    elif not is_valid_input(email_or_phone):
                        st.error("Invalid email or phone format.")
                    elif not gdpr_consent:
                        st.error("Please accept Terms & Privacy Policy.")
                    elif user_exists(email_or_phone):
                        st.error("This email/phone is already registered.")
                    else:
                        # Send OTP
                        otp = str(random.randint(100000, 999999))
                        target_type = is_valid_input(email_or_phone)
                        
                        if target_type == "email":
                            if send_otp_email(email_or_phone, otp):
                                st.session_state.auth_otp = otp
                                st.session_state.auth_target = email_or_phone.strip()
                                st.session_state.auth_step = "otp_verify"
                                st.session_state.signup_data = {
                                    "full_name": full_name,
                                    "password": password,
                                    "gdpr_consent": gdpr_consent
                                }
                                st.success("OTP sent to your email. Verify below.")
                                st.rerun()
                        elif target_type == "phone":
                            if send_otp_sms(email_or_phone, otp):
                                st.session_state.auth_otp = otp
                                st.session_state.auth_target = email_or_phone.strip()
                                st.session_state.auth_step = "otp_verify"
                                st.session_state.signup_data = {
                                    "full_name": full_name,
                                    "password": password,
                                    "gdpr_consent": gdpr_consent
                                }
                                st.success("OTP sent to your phone. Verify below.")
                                st.rerun()
            
            st.markdown("---")
            if st.button("Back to Sign In", use_container_width=True, key="back_login"):
                st.session_state.auth_step = "login"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        # ===== OTP VERIFICATION STEP =====
        elif st.session_state.auth_step == "otp_verify":
            st.markdown('<div class="auth-box">', unsafe_allow_html=True)
            st.markdown('<div class="auth-title">Verify Code</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="auth-sub">Enter the code sent to {st.session_state.auth_target[:3]}***</div>', unsafe_allow_html=True)
            
            with st.form("otp_form"):
                otp_input = st.text_input("Verification Code", placeholder="000000", max_chars=6)
                submitted = st.form_submit_button("Verify", use_container_width=True)
                
                if submitted:
                    if otp_input.strip() == st.session_state.auth_otp:
                        # Create user now
                        data = st.session_state.signup_data
                        if create_user(
                            st.session_state.auth_target,
                            data["password"],
                            data["full_name"],
                            data["gdpr_consent"]
                        ):
                            st.session_state.authenticated = True
                            st.session_state.username = st.session_state.auth_target
                            st.success("Account created! Logging in...")
                            st.session_state.auth_step = "login"
                            st.rerun()
                        else:
                            st.error("Failed to create account.")
                    else:
                        st.session_state.otp_attempts += 1
                        if st.session_state.otp_attempts >= 3:
                            st.error("Too many attempts. Start over.")
                            st.session_state.auth_step = "signup"
                            st.session_state.otp_attempts = 0
                            st.rerun()
                        else:
                            st.error(f"Incorrect code. ({st.session_state.otp_attempts}/3)")
            st.markdown('</div>', unsafe_allow_html=True)
    
    st.stop()

# =========================================================
# AUTHENTICATED DASHBOARD STARTS HERE
# =========================================================

df = load_market_data()

# --- MASTHEAD ---
brand_col, _, settings_col = st.columns([6, 1, 2])

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

with settings_col:
    with st.popover(f"👤 {st.session_state.username[:20]}", use_container_width=True):
        st.markdown(f"**{st.session_state.username}**")
        
        # GDPR Controls
        st.markdown("---")
        st.markdown("**Account & Privacy**")
        theme_choice = st.radio("Theme", ["Dark", "Light"], index=0 if st.session_state.theme == "Dark" else 1)
        if theme_choice != st.session_state.theme:
            st.session_state.theme = theme_choice
            st.rerun()
        
        st.markdown("---")
        if st.button("📋 Privacy Policy", use_container_width=True):
            st.info("""
            ### MARKETPULSE Privacy Policy
            
            **Data We Collect:** Email/phone, name, trading preferences
            **Data Protection:** AES-256 encryption, GDPR-compliant infrastructure
            **Your Rights:**
            - Access your data anytime
            - Request deletion (30-day grace period)
            - Opt-out of analytics
            - Port your data
            
            **Contact:** privacy@marketpulse.com
            """)
        
        if st.button("🗑️ Request Data Deletion", use_container_width=True):
            if request_data_deletion(st.session_state.username):
                st.success("Deletion requested. Your data will be purged in 30 days.")
            else:
                st.error("Deletion request failed.")
        
        st.markdown("---")
        if st.button("Log Out", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.rerun()

st.markdown('<div class="mast-divider"></div>', unsafe_allow_html=True)

if df.empty:
    st.warning("No market data yet. Waiting for the Midnight Robot to run...")
    st.stop()

# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.markdown("### Assets")
tickers = sorted(df['ticker'].unique())
selected_ticker = st.sidebar.radio("Select Ticker", tickers, label_visibility="collapsed")

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Settings")
notify_pref = st.sidebar.radio("Notifications", ["Email", "SMS", "None"])

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
""", unsafe_allow_html=True)

# =========================================================
# PERIOD SELECTOR
# =========================================================
periods = {"1W": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 365, "Max": None}
choice = st.radio("Period", list(periods.keys()), index=len(periods) - 1, horizontal=True, label_visibility="collapsed")

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
  <div class="stat-card"><div class="stat-label">Period High</div><div class="stat-value">{view['close_price'].max():,.2f}</div></div>
  <div class="stat-card"><div class="stat-label">Period Low</div><div class="stat-value">{view['close_price'].min():,.2f}</div></div>
  <div class="stat-card"><div class="stat-label">Period Change</div><div class="stat-value" style="color:{T['up'] if period_delta>=0 else T['down']}">{period_pct:+.2f}%</div></div>
  <div class="stat-card"><div class="stat-label">Avg Volume</div><div class="stat-value">{view['volume'].mean():,.0f}</div></div>
</div>
""", unsafe_allow_html=True)

# =========================================================
# CHART
# =========================================================
going_up = view['close_price'].iloc[-1] >= view['close_price'].iloc[0]
line_color = T['up'] if going_up else T['down']
fill_color = T['upfill'] if going_up else T['downfill']

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])

fig.add_trace(go.Scatter(
    x=view['date'], y=view['close_price'], mode='lines', name='Close',
    line=dict(color=line_color, width=2), fill='tozeroy', fillcolor=fill_color,
    hovertemplate="%{x|%b %d, %Y}<br>Close: %{y:,.2f}<extra></extra>",
), row=1, col=1)

fig.add_trace(go.Bar(
    x=view['date'], y=view['volume'], name='Volume', marker_color=T['volbar'],
    hovertemplate="%{x|%b %d, %Y}<br>Volume: %{y:,.0f}<extra></extra>",
), row=2, col=1)

ymin, ymax = view['close_price'].min(), view['close_price'].max()
pad = (ymax - ymin) * 0.05 if ymax > ymin else 1
fig.update_yaxes(range=[ymin - pad, ymax + pad], row=1, col=1, gridcolor=T['grid'], tickformat=",.2f")
fig.update_yaxes(row=2, col=1, gridcolor=T['grid'], showticklabels=False)
fig.update_xaxes(gridcolor=T['grid'])
fig.update_layout(template=T['plotly'], height=460, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
    font=dict(family="Inter, sans-serif", color=T['text']),
    hoverlabel=dict(bgcolor=T['panel'], bordercolor=T['border'], font=dict(family="Inter, sans-serif", color=T['text'])),
    plot_bgcolor=T['bg'], paper_bgcolor=T['bg'], bargap=0.4)

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
st.download_button(f"Download {selected_ticker} data (CSV)", csv, file_name=f"{selected_ticker}_history.csv", mime="text/csv")