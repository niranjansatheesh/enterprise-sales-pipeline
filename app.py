import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

# Use your Direct Connection string (Port 5432)
# Ensure the password and user are encoded correctly if they contain special characters
DATABASE_URL = "postgresql://postgres.gytdxosyynzrsbefrgfi:Niranjan%4056789@db.gytdxosyynzrsbefrgfi.supabase.co:5432/postgres"

# Force a stricter connection configuration
connect_args = {
    "sslmode": "require",
    "options": "-c search_path=public"
}

try:
    # Use pool_pre_ping to keep the connection alive
    engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
except Exception as e:
    st.error(f"Engine Error: {e}")
    st.stop()

st.set_page_config(page_title="Market Data Dashboard", layout="wide")
st.title("📈 Live Market Dashboard")

try:
    # Use a direct query
    df = pd.read_sql("SELECT * FROM daily_market_logs ORDER BY date DESC", engine)
    
    if df.empty:
        st.warning("Database connected, but no data found.")
    else:
        st.dataframe(df)
except Exception as e:
    st.error(f"Connection Error: {e}")