import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

# --- FORCED DATABASE CONNECTION ---
# We are switching to the DIRECT connection (port 5432) to avoid 
# the 'tenant/user not found' error caused by the pooler.
DATABASE_URL = "postgresql://postgres.gytdxosyynzrsbefrgfi:Niranjan%4056789@db.gytdxosyynzrsbefrgfi.supabase.co:5432/postgres"

try:
    # Adding connect_args with sslmode=require is necessary for Supabase
    engine = create_engine(DATABASE_URL, connect_args={"sslmode": "require"})
except Exception as e:
    st.error(f"Error creating database engine: {e}")
    st.stop()
# ---------------------------------

st.set_page_config(page_title="Market Data Dashboard", layout="wide")
st.title("📈 Live Market Dashboard")

try:
    # Query all records
    query = "SELECT * FROM daily_market_logs ORDER BY date DESC"
    df = pd.read_sql(query, engine)
    
    if df.empty:
        st.warning("The database is connected, but no data has been found yet. Run the robot engine to populate.")
    else:
        # Ensure date column is datetime objects for better plotting
        df['date'] = pd.to_datetime(df['date'])
        
        st.write("### Latest Market Data")
        st.dataframe(df, use_container_width=True)

        # Interactive selection
        st.write("### Price Trend Analysis")
        tickers = sorted(df['ticker'].unique().tolist())
        ticker_choice = st.selectbox("Select a Ticker to view history:", tickers)
        
        # Filter and prepare chart
        filtered_df = df[df['ticker'] == ticker_choice].sort_values('date')
        
        if not filtered_df.empty:
            chart_data = filtered_df.set_index('date')[['close_price']]
            st.line_chart(chart_data)
        else:
            st.info("No data available for the selected ticker.")

except Exception as e:
    st.error(f"Could not connect to database or fetch data. Error: {e}")