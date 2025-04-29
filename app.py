# app.py

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import plotly.graph_objects as go

# If using FRED or other APIs, place your API key here
FRED_API_KEY = "f693521d3101f329c121220251a424b3"  # <- Replace with your FRED key

# ---------------------------------------------
# Function to fetch treasury yields from FRED
# ---------------------------------------------
def fetch_treasury_yields():
    tickers = {
        '1M': 'DGS1MO',
        '3M': 'DGS3MO',
        '6M': 'DGS6MO',
        '1Y': 'DGS1',
        '2Y': 'DGS2',
        '5Y': 'DGS5',
        '7Y': 'DGS7',
        '10Y': 'DGS10',
        '20Y': 'DGS20',
        '30Y': 'DGS30'
    }
    yields = {}
    today = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=7)).strftime('%Y-%m-%d')

    for label, series_id in tickers.items():
        url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={FRED_API_KEY}&file_type=json&observation_start={start_date}&observation_end={today}"
        response = requests.get(url)
        data = response.json()
        observations = data.get('observations', [])
        if observations:
            yields[label] = float(observations[-1]['value'])
        else:
            yields[label] = None

    return yields

# -------------------------------------------------
# Function to fetch Fed Funds Futures Implied Rates
# -------------------------------------------------
def fetch_fed_funds_implied():
    contracts = ['ZQ=F']  # Generic front-month Fed Funds futures
    futures_data = yf.download(contracts, period="5d", interval="1d")
    if not futures_data.empty:
        last_close = futures_data['Adj Close'].iloc[-1]['ZQ=F']
        implied_rate = 100 - last_close
        return implied_rate
    else:
        return None

# -------------------------------------------------
# Calculate Yield Spreads
# -------------------------------------------------
def calculate_yield_spreads(yields):
    spread_2s10s = yields['2Y'] - yields['10Y']
    spread_2s5s = yields['2Y'] - yields['5Y']
    spread_5s10s = yields['5Y'] - yields['10Y']
    return spread_2s10s, spread_2s5s, spread_5s10s

# -------------------------------------------------
# Fetch VIX Term Structure
# -------------------------------------------------
def fetch_vix_term_structure():
    tickers = ['^VIX', '^VIX9D', '^VIX3M']
    data = yf.download(tickers, period="5d", interval="1d")['Adj Close']
    vix_spot = data['^VIX'].iloc[-1]
    vix_9d = data['^VIX9D'].iloc[-1]
    vix_3m = data['^VIX3M'].iloc[-1]
    return vix_spot, vix_9d, vix_3m

# -------------------------------------------------
# Fetch SKEW Index
# -------------------------------------------------
def fetch_skew_index():
    try:
        skew_data = yf.download('^SKEW', period="5d", interval="1d")
        skew_value = skew_data['Adj Close'].iloc[-1]
        return skew_value
    except Exception as e:
        return None

# -------------------------------------------------
# Fetch ES Futures and S&P 500 Cash for Implied Open
# -------------------------------------------------
def fetch_es_futures_spx_cash():
    es_data = yf.download('ES=F', period="5d", interval="1d")
    spx_data = yf.download('^GSPC', period="5d", interval="1d")
    es_close = es_data['Adj Close'].iloc[-1]
    spx_close = spx_data['Adj Close'].iloc[-1]
    implied_open = es_close - spx_close
    return implied_open

# -------------------------------------------------
# Dashboard Display
# -------------------------------------------------
def display_dashboard():
    st.title("🚀 NICOMPORIA Macro Risk Dashboard (Pro Version)")

    # Treasury Yield Curve
    yields = fetch_treasury_yields()
    st.subheader("📈 Treasury Yield Curve")
    st.write(pd.DataFrame(yields, index=[0]))

    spread_2s10s, spread_2s5s, spread_5s10s = calculate_yield_spreads(yields)
    st.metric("2s10s Spread", f"{spread_2s10s:.2f}%")
    st.metric("2s5s Spread", f"{spread_2s5s:.2f}%")
    st.metric("5s10s Spread", f"{spread_5s10s:.2f}%")

    # VIX Term Structure
    vix_spot, vix_9d, vix_3m = fetch_vix_term_structure()
    st.subheader("⚡ VIX Term Structure")
    st.write(f"Spot VIX: {vix_spot:.2f}")
    st.write(f"9-Day VIX: {vix_9d:.2f}")
    st.write(f"3-Month VIX: {vix_3m:.2f}")

    # Skew Index
    skew_value = fetch_skew_index()
    st.subheader("📊 SKEW Index (Crash Risk Premium)")
    if skew_value:
        st.write(f"SKEW Index: {skew_value:.2f}")
    else:
        st.write("SKEW data not available.")

    # Fed Funds Futures
    fed_funds_implied = fetch_fed_funds_implied()
    st.subheader("🏛️ Fed Funds Futures Implied Rate")
    st.write(f"Fed Funds Futures Implied Rate: {fed_funds_implied:.2f}%")

    # ES Futures Fair Value
    implied_open = fetch_es_futures_spx_cash()
    st.subheader("📈 ES Futures vs SPX Cash Implied Open")
    st.write(f"Futures Premium/Discount to SPX: {implied_open:.2f} points")

    # Risk Meter Summary
    st.header("📊 RISK METER SUMMARY")
    st.write("Tells you Risk On / Risk Off based on yield curves, vol term structure, credit spreads, etc. (Next phase adding full calculations.)")

# MAIN CALL
if __name__ == "__main__":
    display_dashboard()
