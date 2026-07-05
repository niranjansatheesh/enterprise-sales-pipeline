import streamlit as st
import pandas as pd
import plotly.express as px


st.set_page_config(page_title="Executive Sales Dashboard", layout="wide")
st.title("📊 Executive Sales Dashboard")
st.markdown("Real-time data engine fed by our Azure Data Pipeline.")


@st.cache_data
def load_data():
    df = pd.read_csv("sales_data.csv")
    
    df.columns = df.columns.str.strip() 
    return df

df = load_data()


st.sidebar.header("Filter Options")
selected_region = st.sidebar.multiselect(
    "Select Region:",
    options=df["region"].unique(),       
    default=df["region"].unique()        
)


df_filtered = df[df["region"].isin(selected_region)]  


total_sales = df_filtered["amount"].sum()    
total_orders = len(df_filtered)

col1, col2 = st.columns(2)
with col1:
    st.metric(label="Total Revenue", value=f"${total_sales:,.2f}")
with col2:
    st.metric(label="Total Orders Placed", value=f"{total_orders:,}")


st.subheader("Regional Performance Analysis")
fig_bar = px.bar(
    df_filtered, 
    x="region",                          
    y="amount",                              
    title="Sales Breakdown by Region"        
)
st.plotly_chart(fig_bar, use_container_width=True)


st.subheader("Raw Cleaned Dataset")
st.dataframe(df_filtered)