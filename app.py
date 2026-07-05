import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf

# 1. Page Configuration
st.set_page_config(page_title="Live Financial Pipeline", layout="wide")
st.title("📈 Live Financial Data Engine")
st.markdown("Real-time data pipeline pulling directly from the Yahoo Finance API.")

# 2. Sidebar Controls
st.sidebar.header("Pipeline Controls")
tickers = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
selected_ticker = st.sidebar.selectbox("Select Asset to Track:", tickers)
time_period = st.sidebar.selectbox("Time Period:", ["1mo", "3mo", "6mo", "1y", "5y"])

# 3. Live API Data Fetcher (with 5-minute caching to prevent API bans)
@st.cache_data(ttl=300) 
def load_live_data(ticker, period):
    stock = yf.Ticker(ticker)
    df = stock.history(period=period)
    df.reset_index(inplace=True)
    # Format the dates cleanly
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    return df

# Trigger the API
df = load_live_data(selected_ticker, time_period)

# 4. Top Metric Cards (Calculated on the fly)
latest_price = df['Close'].iloc[-1]
previous_price = df['Close'].iloc[-2]
price_change = latest_price - previous_price
pct_change = (price_change / previous_price) * 100

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Current Price (Close)", f"${latest_price:.2f}", f"{price_change:.2f} ({pct_change:.2f}%)")
with col2:
    st.metric("Trading Volume", f"{df['Volume'].iloc[-1]:,}")
with col3:
    st.metric("Active Asset", selected_ticker)

# 5. Interactive Time-Series Chart
st.subheader("Live Market Performance")
fig = px.line(
    df, 
    x='Date', 
    y='Close', 
    title=f"{selected_ticker} Stock Price Trend ({time_period})"
)
st.plotly_chart(fig, use_container_width=True)

# Display the raw data streaming in
st.subheader("Raw API Data Stream")
st.dataframe(df.tail(10))