import streamlit as st
import yfinance as yf
import plotly.graph_objs as go
import pandas as pd
import numpy as np
import requests
from fredapi import Fred
from datetime import datetime

# FRED API setup
FRED_API_KEY = "31934d0584960301655194d067cc9399"
fred = Fred(api_key=FRED_API_KEY)

# Helper function to fetch FRED data
def fetch_fred_data(series_id):
    try:
        data = fred.get_series(series_id)
        return data
    except Exception as e:
        st.error(f"Error fetching FRED data for {series_id}: {str(e)}")
        return None

# Function to calculate implied fed funds rate
def get_implied_fed_funds_rate():
    data = fetch_fred_data('EFFR')
    if data is not None:
        last_price = data[-1]
        previous_price = data[-2]
        change = last_price - previous_price
        risk_on = "Risk On" if change > 0 else "Risk Off"
        return last_price, change, risk_on
    return None, None, None

# Function to calculate real fed funds rate
def get_real_fed_funds_rate():
    nominal_rate = fetch_fred_data('EFFR')
    inflation_rate = fetch_fred_data('CPIAUCSL')
    if nominal_rate is not None and inflation_rate is not None:
        real_rate = nominal_rate[-1] - inflation_rate[-1]
        previous_real_rate = nominal_rate[-2] - inflation_rate[-2]
        change = real_rate - previous_real_rate
        risk_on = "Risk On" if change > 0 else "Risk Off"
        return real_rate, change, risk_on
    return None, None, None

# Fetch 10Y treasury yields
def fetch_treasury_yield():
    yield_data = fetch_fred_data('DGS10')
    if yield_data is not None:
        last_yield = yield_data[-1]
        previous_yield = yield_data[-2]
        change = last_yield - previous_yield
        risk_on = "Risk On" if change > 0 else "Risk Off"
        return last_yield, change, risk_on
    return None, None, None

# Premarket Data
def get_premarket_data(symbol):
    ticker = yf.Ticker(symbol)
    data = ticker.history(period="1d", prepost=True)
    premarket_price = data['Open'].iloc[0] if not data.empty else None
    return premarket_price

# Volatility Indices - VIX
def get_volatility_index():
    vix = yf.Ticker('^VIX')
    vix_data = vix.history(period='1d')
    if 'Adj Close' in vix_data.columns:
        vix_volatility = vix_data['Adj Close'].iloc[-1]
        return vix_volatility
    return None

# Function to calculate the Risk-On / Risk-Off consensus
def calculate_risk_on_off():
    risk_on_count = 0
    risk_off_count = 0
    
    # Calculate values for all sections (assumed to be implemented already)
    fed_fund_implied, _, implied_risk = get_implied_fed_funds_rate()
    if implied_risk == "Risk On":
        risk_on_count += 1
    else:
        risk_off_count += 1
    
    fed_fund_real, _, real_risk = get_real_fed_funds_rate()
    if real_risk == "Risk On":
        risk_on_count += 1
    else:
        risk_off_count += 1

    treasury_yield, _, treasury_risk = fetch_treasury_yield()
    if treasury_risk == "Risk On":
        risk_on_count += 1
    else:
        risk_off_count += 1
    
    vix_volatility = get_volatility_index()
    if vix_volatility is not None:
        vix_risk = "Risk On" if vix_volatility < 20 else "Risk Off"
        if vix_risk == "Risk On":
            risk_on_count += 1
        else:
            risk_off_count += 1
    
    # Display the risk on/off consensus
    consensus = "Risk On" if risk_on_count > risk_off_count else "Risk Off"
    return risk_on_count, risk_off_count, consensus

# Streamlit Application
def app():
    st.title("Risk-On / Risk-Off Consensus Dashboard")
    
    # Fetch Core Interest Rate Data
    implied_fed_rate, fed_change, implied_risk = get_implied_fed_funds_rate()
    real_fed_rate, real_change, real_risk = get_real_fed_funds_rate()

    # Fetch Treasury Yields
    ten_year_yield, yield_change, yield_risk = fetch_treasury_yield()

    # Fetch Premarket Data
    es_premarket = get_premarket_data("ES=F")
    gold_premarket = get_premarket_data("GC=F")
    dxy_premarket = get_premarket_data("DX=F")
    
    # Calculate Risk Consensus
    risk_on_count, risk_off_count, consensus = calculate_risk_on_off()
    
    st.markdown(f"### Risk-On / Risk-Off Consensus: {consensus}")
    st.markdown(f"**Risk-On Count:** {risk_on_count} | **Risk-Off Count:** {risk_off_count}")
    
    # Display Core Interest Rate Data
    st.markdown("### Core Interest Rate Data")
    st.write(f"**Implied Fed Funds Rate:** {implied_fed_rate} ({implied_risk} from yesterday)")
    st.write(f"**Real Fed Funds Rate:** {real_fed_rate} ({real_risk} from yesterday)")

    # Display Treasury Yields
    st.markdown("### 10-Year Treasury Yield Data")
    st.write(f"**10Y Treasury Yield:** {ten_year_yield} ({yield_risk} from yesterday)")
    
    # Display Premarket Data
    st.markdown("### Premarket Data")
    st.write(f"**ES Futures Premarket Price:** {es_premarket}")
    st.write(f"**Gold Futures Premarket Price:** {gold_premarket}")
    st.write(f"**DXY Futures Premarket Price:** {dxy_premarket}")

    # Display Volatility Indices
    vix_volatility = get_volatility_index()
    st.markdown("### Volatility Index")
    st.write(f"**VIX Volatility:** {vix_volatility}")
    
    # Add additional sections (Treasury curve, spreads, premium calculations, etc.)
    # Here you can add the full details of your dashboard, such as plotting charts,
    # calculating term structures, implied open premiums, etc.

if __name__ == '__main__':
    app()
