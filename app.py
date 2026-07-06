import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf


st.set_page_config(page_title="Live Financial Pipeline", layout="wide")
st.title("📈 Live Financial Data Engine")
st.markdown("Real-time data pipeline pulling directly from the Yahoo Finance API.")


st.sidebar.header("Pipeline Controls")
tickers = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
selected_ticker = st.sidebar.selectbox("Select Asset to Track:", tickers)
time_period = st.sidebar.selectbox("Time Period:", ["1mo", "3mo", "6mo", "1y", "5y"])


@st.cache_data(ttl=300) 
def load_live_data(ticker, period):
    stock = yf.Ticker(ticker)
    df = stock.history(period=period)
    df.reset_index(inplace=True)
    # Format the dates cleanly
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    return df


df = load_live_data(selected_ticker, time_period)


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




st.markdown("---") 
st.subheader("🤖 Historical Vault Data")
st.markdown("This data is collected automatically every night by our GitHub Actions robot.")


try:
    history_df = pd.read_csv("daily_market_logs.csv")
    
    
    history_df["Ticker"] = history_df["Ticker"].str.strip()
    
    
    asset_history = history_df[history_df["Ticker"] == selected_ticker]
    
    if not asset_history.empty:
        
            fig_hist = px.bar(
                asset_history, 
                x="Date", 
                y="Close_Price", 
                title=f"{selected_ticker} Historical Closing Prices",
                text="Close_Price"
            )
            st.plotly_chart(fig_hist, use_container_width=True)
            
            with st.expander("View Raw Robot Database"):
                st.dataframe(asset_history)
                
        else:
            st.info(f"The robot hasn't collected historical data for {selected_ticker} yet.")
            
except FileNotFoundError:
    st.warning("Historical vault file not found. Waiting for the robot's first run!")

