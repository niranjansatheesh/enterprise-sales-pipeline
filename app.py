import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os


LOCAL_DB_URL = "postgresql://postgres.gytdxosyynzrsbefrgfi:Niranjan%4056789@aws-0-eu-central-2.pooler.supabase.com:6543/postgres"


DATABASE_URL = os.getenv("DATABASE_URL", LOCAL_DB_URL)

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

try:
    engine = create_engine(DATABASE_URL)
except Exception as e:
    st.error(f"Error creating database engine: {e}")
    st.stop()


st.set_page_config(page_title="Market Data Dashboard", layout="wide")
st.title("📈 Live Market Dashboard")


try:
  
    query = "SELECT * FROM daily_market_logs ORDER BY date DESC"
    df = pd.read_sql(query, engine)
    
    if df.empty:
        st.warning("The database is connected, but no data has been found yet. Run the robot engine to populate.")
    else:
       
        df['date'] = pd.to_datetime(df['date'])
        
        st.write("### Latest Market Data")
        st.dataframe(df, use_container_width=True)

        
        st.write("### Price Trend Analysis")
        tickers = sorted(df['ticker'].unique().tolist())
        ticker_choice = st.selectbox("Select a Ticker to view history:", tickers)
        
        
        filtered_df = df[df['ticker'] == ticker_choice].sort_values('date')
        
        if not filtered_df.empty:
            chart_data = filtered_df.set_index('date')[['close_price']]
            st.line_chart(chart_data)
        else:
            st.info("No data available for the selected ticker.")

except Exception as e:
    st.error(f"Could not connect to database or fetch data. Error: {e}")