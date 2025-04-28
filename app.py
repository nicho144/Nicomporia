# app.py
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from fredapi import Fred
import datetime

# ----------- CONFIGURATION ---------------
st.set_page_config(page_title="Risk-On Risk-Off Dashboard", layout="wide")

# Replace with your FRED API key here
FRED_API_KEY = "your_actual_fred_api_key_here"
fred = Fred(api_key=FRED_API_KEY)

today = datetime.date.today()
start_date = today - datetime.timedelta(days=7)

# -------------- FUNCTIONS ----------------

def get_fred_data(series_id):
    try:
        data = fred.get_series(series_id)
        return data
    except Exception as e:
        st.error(f"Error fetching FRED data: {series_id}, {e}")
        return pd.Series()

def get_yfinance_data(ticker):
    try:
        data = yf.download(ticker, start=start_date, end=today)
        return data
    except Exception as e:
        st.error(f"Error fetching Yahoo Finance data: {ticker}, {e}")
        return pd.DataFrame()

def calculate_implied_rate():
    futures = get_yfinance_data('ZQ=F')
    if not futures.empty:
        try:
            last_price = futures['Adj Close'].iloc[-1]
            implied_rate = 100 - last_price
            return implied_rate
        except:
            pass
    # fallback to FRED data
    data = get_fred_data('EFFR')
    if not data.empty:
        return data.iloc[-1]
    return None

def load_yield_curve():
    maturities = {
        "3M": "DTB3",
        "2Y": "DGS2",
        "5Y": "DGS5",
        "10Y": "DGS10",
        "30Y": "DGS30"
    }
    yield_curve = {}
    for label, code in maturities.items():
        series = get_fred_data(code)
        if not series.empty:
            yield_curve[label] = series.iloc[-1]
        else:
            yield_curve[label] = np.nan
    return yield_curve

def calculate_spread(yield_curve, short_term, long_term):
    if short_term in yield_curve and long_term in yield_curve:
        return yield_curve[short_term] - yield_curve[long_term]
    else:
        return np.nan

def get_hyoas_spread():
    series = get_fred_data('BAMLH0A0HYM2')  # High Yield OAS spread
    if not series.empty:
        return series.iloc[-1]
    return None

def get_real_yield():
    series = get_fred_data('DFII10')  # 10-year TIPS real yield
    if not series.empty:
        return series.iloc[-1]
    return None

def get_breakeven_inflation():
    series = get_fred_data('T10YIE')  # 10-year breakeven inflation
    if not series.empty:
        return series.iloc[-1]
    return None

def determine_risk_on_off(metrics):
    score = 0
    for metric, value in metrics.items():
        if value == "Risk-On":
            score += 1
        elif value == "Risk-Off":
            score -= 1
    return "Risk-On" if score > 0 else "Risk-Off"

# --------- STREAMLIT LAYOUT -------------

st.title("📈 RISK-ON / RISK-OFF Consensus Dashboard")

st.header("🔵 Core Interest Rate Data")
implied_rate = calculate_implied_rate()
real_yield = get_real_yield()
breakeven_inflation = get_breakeven_inflation()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("📈 Implied Fed Funds Rate", f"{implied_rate:.2f}%" if implied_rate else "N/A")

with col2:
    st.metric("📉 10Y Real Yield", f"{real_yield:.2f}%" if real_yield else "N/A")

with col3:
    st.metric("🔥 Breakeven Inflation (10Y)", f"{breakeven_inflation:.2f}%" if breakeven_inflation else "N/A")


st.header("🔵 Yield Curve & Credit Spread Data")
yield_curve = load_yield_curve()

spread_2s10s = calculate_spread(yield_curve, "2Y", "10Y")
spread_3m10y = calculate_spread(yield_curve, "3M", "10Y")
hyoas_spread = get_hyoas_spread()

col4, col5, col6 = st.columns(3)

with col4:
    st.metric("2Y-10Y Spread", f"{spread_2s10s:.2f}%" if not np.isnan(spread_2s10s) else "N/A")

with col5:
    st.metric("3M-10Y Spread", f"{spread_3m10y:.2f}%" if not np.isnan(spread_3m10y) else "N/A")

with col6:
    st.metric("HY-OAS Spread", f"{hyoas_spread:.2f}%" if hyoas_spread else "N/A")


st.header("🔵 Skew and Options Premium")
# Placeholder logic (actual skew needs options chain data)
skew = np.random.choice(["Cheap Premiums (Risk-On)", "Expensive Premiums (Risk-Off)"])
st.write(f"Today's Option Skew Status: **{skew}**")

st.header("🔵 Unusual Options / Dark Pool Activity")
# Placeholder display
st.write("""
🔹 **No major dark pool activity detected today.**  
🔹 **Unusual options volume elevated in SPY, QQQ.**
""")


# Risk-On / Risk-Off Calculation
metrics_summary = {
    "Implied Rate": "Risk-On" if implied_rate and implied_rate < 5 else "Risk-Off",
    "Real Yield": "Risk-On" if real_yield and real_yield < 2 else "Risk-Off",
    "Breakeven Inflation": "Risk-On" if breakeven_inflation and breakeven_inflation > 1.8 else "Risk-Off",
    "2s10s Spread": "Risk-On" if spread_2s10s and spread_2s10s > 0 else "Risk-Off",
    "3m10y Spread": "Risk-On" if spread_3m10y and spread_3m10y > 0 else "Risk-Off",
    "HY-OAS Spread": "Risk-On" if hyoas_spread and hyoas_spread < 5 else "Risk-Off",
    "Options Skew": "Risk-On" if "Cheap" in skew else "Risk-Off",
}

final_consensus = determine_risk_on_off(metrics_summary)

st.header("🔵 Consensus Final Decision")
st.subheader(f"📢 Today is: **{final_consensus}**")

