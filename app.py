import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL

# --- ROBUST CONNECTION ---
# Using URL object construction to prevent parsing errors with special characters
db_url = URL.create(
    drivername="postgresql",
    username="postgres.gytdxosyynzrsbefrgfi",
    password="Niranjan@56789",
    host="db.gytdxosyynzrsbefrgfi.supabase.co",
    port=5432,
    database="postgres"
)

try:
    # Explicitly force SSL for Supabase security
    engine = create_engine(db_url, connect_args={"sslmode": "require"})
except Exception as e:
    st.error(f"Error creating database engine: {e}")
    st.stop()

st.set_page_config(page_title="Market Data Dashboard", layout="wide")
st.title("📈 Live Market Dashboard")

try:
    query = "SELECT * FROM daily_market_logs ORDER BY date DESC"
    df = pd.read_sql(query, engine)
    
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
    st.error(f"Could not connect: {e}")