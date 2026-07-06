import streamlit as st
import pandas as pd
import psycopg2

# --- DIRECT PSYCOPG2 CONNECTION ---
# We bypass SQLAlchemy to pinpoint the connection error
DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres.gytdxosyynzrsbefrgfi",
    "password": "Niranjan@56789",
    "host": "db.gytdxosyynzrsbefrgfi.supabase.co",
    "port": "5432",
    "sslmode": "require"
}

st.set_page_config(page_title="Market Data Dashboard", layout="wide")
st.title("📈 Live Market Dashboard")

try:
    # Connect using psycopg2 directly
    conn = psycopg2.connect(**DB_CONFIG)
    
    # Fetch data
    query = "SELECT * FROM daily_market_logs ORDER BY date DESC"
    df = pd.read_sql(query, conn)
    conn.close()
    
    if df.empty:
        st.warning("The database is connected, but no data has been found yet.")
    else:
        df['date'] = pd.to_datetime(df['date'])
        st.write("### Latest Market Data")
        st.dataframe(df, use_container_width=True)

        st.write("### Price Trend Analysis")
        tickers = sorted(df['ticker'].unique().tolist())
        ticker_choice = st.selectbox("Select a Ticker:", tickers)
        
        filtered_df = df[df['ticker'] == ticker_choice].sort_values('date')
        if not filtered_df.empty:
            st.line_chart(filtered_df.set_index('date')[['close_price']])
        else:
            st.info("No data available.")
            
except Exception as e:
    st.error(f"Connection Error: {e}")