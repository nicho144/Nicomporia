import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import requests
import yfinance as yf
import numpy as np

# FRED API key
API_KEY = 'f693521d3101f329c121220251a424b3'
FRED_BASE_URL = 'https://api.stlouisfed.org/fred/'

# Function to fetch FRED data
def fetch_fred_data(series_id, api_key=API_KEY):
    url = f"{FRED_BASE_URL}series/observations?series_id={series_id}&api_key={api_key}&file_type=json"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise error for bad requests
        data = response.json()
        return pd.DataFrame(data['observations'])
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data for {series_id}: {e}")
        return pd.DataFrame()  # Return an empty DataFrame on error

# Function to fetch VIX data (using yfinance)
def fetch_vix_data():
    try:
        vix = yf.download('^VIX', period="1d", interval="1m")
        return vix
    except Exception as e:
        st.error(f"Error fetching VIX data: {e}")
        return pd.DataFrame()  # Return empty dataframe if error

# Function to calculate implied open from CNBC
def fetch_premarket_ES_data():
    try:
        # Example fetching premarket data for ES (S&P 500 futures) from Yahoo Finance
        es_futures = yf.download('ES=F', period="1d", interval="1m")
        return es_futures
    except Exception as e:
        st.error(f"Error fetching ES premarket data: {e}")
        return pd.DataFrame()

# Function to calculate risk condition for Fed Funds data
def calculate_fed_condition(dff, dff_implied):
    if dff.empty or dff_implied.empty:
        return "Data Missing"
    
    try:
        fed_condition = 'Risk On' if dff['value'].iloc[-1] > dff_implied['value'].iloc[-1] else 'Risk Off'
        return fed_condition
    except Exception as e:
        st.error(f"Error calculating Fed condition: {e}")
        return "Data Error"

# Function to analyze all factors for risk conditions
def analyze_all_factors():
    # Fetch data
    dff = fetch_fred_data('EFFR')  # Fed Funds Rate
    dff_implied = fetch_fred_data('DFF')  # Implied Fed Funds Rate
    
    # Calculate Fed condition
    fed_condition = calculate_fed_condition(dff, dff_implied)

    # Fetch VIX and other market data
    vix_data = fetch_vix_data()
    vix_condition = 'Risk On' if vix_data['Adj Close'].iloc[-1] < 20 else 'Risk Off'  # Example condition for VIX

    es_futures = fetch_premarket_ES_data()
    es_condition = 'Risk On' if es_futures['Close'].iloc[-1] > es_futures['Open'].iloc[-1] else 'Risk Off'
    
    # Aggregate total risk condition count
    risk_conditions = {
        'Fed Condition': fed_condition,
        'VIX Condition': vix_condition,
        'ES Condition': es_condition
    }

    risk_on_count = sum(1 for condition in risk_conditions.values() if 'On' in condition)
    risk_off_count = sum(1 for condition in risk_conditions.values() if 'Off' in condition)
    
    consensus = 'Risk On' if risk_on_count > risk_off_count else 'Risk Off'

    return risk_conditions, consensus

# Streamlit Dashboard Display Function
def display_dashboard():
    # Display the title and introductory information
    st.title("Financial Dashboard")
    st.markdown("Welcome to the financial dashboard, which aggregates key indicators and market conditions to assess whether the market is in a 'Risk On' or 'Risk Off' environment.")

    # Analyze all factors
    risk_conditions, consensus = analyze_all_factors()
    
    # Display risk conditions and consensus
    st.subheader("Risk Conditions")
    for factor, condition in risk_conditions.items():
        st.write(f"{factor}: {condition}")
    
    st.subheader("Market Consensus")
    st.write(f"Overall market condition: **{consensus}**")

    # Display relevant charts
    st.subheader("VIX Chart")
    vix_data = fetch_vix_data()
    if not vix_data.empty:
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=vix_data.index,
                                     open=vix_data['Open'],
                                     high=vix_data['High'],
                                     low=vix_data['Low'],
                                     close=vix_data['Adj Close'],
                                     name="VIX"))
        fig.update_layout(title="VIX Chart", xaxis_title="Time", yaxis_title="VIX Value")
        st.plotly_chart(fig)
    
    # Display other relevant data (such as Fed Funds)
    st.subheader("Fed Funds Rate")
    if not dff.empty:
        st.write(f"Current Fed Funds Rate: {dff['value'].iloc[-1]}")
        st.write(f"Implied Fed Funds Rate: {dff_implied['value'].iloc[-1]}")
    
    # Display ES Futures premarket price
    st.subheader("S&P 500 Futures (ES) Premarket")
    if not es_futures.empty:
        st.write(f"Premarket Close: {es_futures['Close'].iloc[-1]}")
        st.write(f"Premarket Open: {es_futures['Open'].iloc[-1]}")
    
    # Add additional indicators like Gold, DXY, etc.
    # ...

# Run the Streamlit app
if __name__ == "__main__":
    display_dashboard()
