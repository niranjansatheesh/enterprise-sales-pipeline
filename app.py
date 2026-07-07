import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, inspect
import os
import plotly.express as px

st.set_page_config(page_title="Market Data Pro", page_icon="📈", layout="wide")

st.markdown("""
<style>
    .stMetric {
        background-color: #1E1E2E;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #00FFAA;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

NEON_URL = "postgresql://neondb_owner:npg_vD2Iatbq0CiM@ep-still-thunder-atsunix7.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require"

DATABASE_URL = os.getenv("DATABASE_URL", NEON_URL)

@st.cache_resource
def init_connection():
    return create_engine(DATABASE_URL)

try:
    engine = init_connection()
    inspector = inspect(engine)
    
    if 'daily_market_logs' not in inspector.get_table_names():
        st.warning("🚀 Database connected! Waiting for the Robot Engine to fetch the first batch of data.")
        st.stop()
        
    df = pd.read_sql("SELECT * FROM daily_market_logs ORDER BY date DESC", engine)
    
    if df.empty:
        st.warning("Database connected successfully! But no data found.")
        st.stop()

    st.title("📈 Pro Market Analytics")
    st.markdown("Live data synced directly from your Neon SQL Vault.")
    
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2942/2942269.png", width=100)
    st.sidebar.header("Dashboard Controls")
    tickers = sorted(df['ticker'].unique().tolist())
    selected_ticker = st.sidebar.selectbox("Select an Asset to Analyze:", tickers)
    
    ticker_data = df[df['ticker'] == selected_ticker].sort_values('date')
    
    if not ticker_data.empty:
        st.markdown(f"### {selected_ticker} Overview")
        latest_data = ticker_data.iloc[-1]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Latest Close Price", value=f"${latest_data['close_price']:,.2f}")
        with col2:
            st.metric(label="Trading Volume", value=f"{latest_data['volume']:,}")
        with col3:
            st.metric(label="Last Updated", value=f"{latest_data['date']}")
            
        st.markdown("---")
        st.markdown(f"### {selected_ticker} Price Trend")
        
        fig = px.area(
            ticker_data, 
            x='date', 
            y='close_price', 
            markers=True,
            color_discrete_sequence=['#00FFAA']
        )
        
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", 
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis_title="", 
            yaxis_title="Closing Price ($)",
            margin=dict(l=0, r=0, t=30, b=0)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    st.markdown("---")
    st.markdown("### 🗄️ Raw SQL Vault Data")
    
    st.dataframe(
        df.style.highlight_max(axis=0, subset=['close_price'], color='#005500'),
        use_container_width=True,
        height=250
    )

except Exception as e:
    st.error(f"Error reading database: {e}")
