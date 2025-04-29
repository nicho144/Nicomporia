# app.py

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests

# Set your FRED API Key here
FRED_API_KEY = 'f693521d3101f329c121220251a424b3'

# --- Functions ---

def fetch_fred_series(series_id):
    """Fetch data from FRED."""
    try:
        url = f'https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={FRED_API_KEY}&file_type=json'
        response = requests.get(url)
        data = response.json()
        observations = data.get('observations', [])
        df = pd.DataFrame(observations)
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df['date'] = pd.to_datetime(df['date'])
        return df[['date', 'value']].dropna()
    except Exception as e:
        print(f"Error fetching FRED data for {series_id}: {e}")
        return pd.DataFrame()

def fetch_latest_yfinance_price(ticker):
    """Fetch the latest regular price from Yahoo Finance."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="2d")
        if not hist.empty:
            return hist['Close'].iloc[-1]
        else:
            return np.nan
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return np.nan

def fetch_premarket_price(ticker):
    """Fetch premarket price, fallback to last close if not available."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        premarket_price = info.get('preMarketPrice', None)
        if premarket_price is None:
            hist = stock.history(period="2d")
            if not hist.empty:
                return hist['Close'].iloc[-1]
            else:
                return np.nan
        return premarket_price
    except Exception as e:
        print(f"Error fetching premarket price for {ticker}: {e}")
        return np.nan

def analyze_all_factors():
    """Analyze various market risk factors."""
    try:
        # VIX
        vix_price = fetch_latest_yfinance_price('^VIX')
        vix_condition = 'Risk On' if vix_price < 20 else 'Risk Off'

        # Treasury Yields
        dgs2 = fetch_fred_series('DGS2')  # 2-Year Yield
        dgs10 = fetch_fred_series('DGS10')  # 10-Year Yield
        dgs30 = fetch_fred_series('DGS30')  # 30-Year Yield

        if not dgs2.empty and not dgs10.empty:
            latest_2yr = dgs2['value'].iloc[-1]
            latest_10yr = dgs10['value'].iloc[-1]
            yield_spread = latest_10yr - latest_2yr
            spread_condition = 'Risk On' if yield_spread > 0 else 'Risk Off'
        else:
            spread_condition = 'Unknown'

        # Gold
        gold_price = fetch_premarket_price('GC=F')
        gold_condition = 'Risk Off' if gold_price > 2000 else 'Risk On'

        # Oil
        oil_price = fetch_premarket_price('CL=F')
        oil_condition = 'Risk On' if oil_price < 90 else 'Risk Off'

        # Risk factors dictionary
        risk_factors = {
            'VIX': vix_condition,
            'Yield Curve Spread': spread_condition,
            'Gold': gold_condition,
            'Oil': oil_condition
        }

        # Count how many say "Risk Off"
        risk_off_count = sum(1 for v in risk_factors.values() if v == 'Risk Off')
        consensus = 'Risk Off' if risk_off_count >= 2 else 'Risk On'

        return risk_factors, consensus
    except Exception as e:
        print(f"Error analyzing factors: {e}")
        return {}, 'Unknown'

def display_dashboard():
    st.title('Market Risk Sentiment Dashboard')
    st.caption('Live Analysis Based on VIX, Yields, Gold, Oil')

    with st.spinner('Fetching Data...'):
        risk_factors, consensus = analyze_all_factors()

    if not risk_factors:
        st.error('Error fetching data. Please try again later.')
        return

    # --- Display Consensus ---
    st.markdown("---")
    if consensus == 'Risk On':
        st.success('📈 **TODAY’S MARKET CONSENSUS: RISK ON**')
    elif consensus == 'Risk Off':
        st.error('📉 **TODAY’S MARKET CONSENSUS: RISK OFF**')
    else:
        st.warning('❓ **CONSENSUS: UNKNOWN**')

    # --- Display Details ---
    st.markdown("---")
    st.header('Detailed Conditions:')
    for factor, condition in risk_factors.items():
        if condition == 'Risk On':
            st.write(f"🟢 {factor}: **{condition}**")
        elif condition == 'Risk Off':
            st.write(f"🔴 {factor}: **{condition}**")
        else:
            st.write(f"⚪ {factor}: **{condition}**")

# --- Main Execution ---
if __name__ == '__main__':
    display_dashboard()
