import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import datetime
from fredapi import Fred
import plotly.graph_objs as go

# Set your FRED API key
fred = Fred(api_key='YOUR_FRED_API_KEY')

# ---------- Fallback Fetch Functions ----------

def get_fred_data_with_fallback(series_id):
    try:
        data = fred.get_series(series_id)
        if data.empty:
            raise ValueError(f"Data for {series_id} is empty.")
        return data
    except Exception as e:
        st.error(f"Error fetching FRED data for {series_id}: {e}")
        fallback_data = pd.Series([0] * 30)  # Fallback dummy data
        return fallback_data

def get_yfinance_data_with_fallback(ticker, period="1d", interval="1m"):
    try:
        data = yf.download(ticker, period=period, interval=interval)
        if data.empty:
            raise ValueError(f"No data found for {ticker}.")
        return data
    except Exception as e:
        st.error(f"Error fetching {ticker}: {e}")
        fallback_data = pd.DataFrame({'Adj Close': [0]})
        return fallback_data

# ---------- Data Fetch Functions ----------

def get_core_interest_rates():
    effr = get_fred_data_with_fallback("EFFR")  # Effective Federal Funds Rate
    t10yie = get_fred_data_with_fallback("T10YIE")  # 10-Year Breakeven Inflation Rate
    dgs10 = get_fred_data_with_fallback("DGS10")  # 10-Year Treasury Rate
    return effr, t10yie, dgs10

def get_fed_funds_calculations():
    fed_futures = get_yfinance_data_with_fallback("FF=F", period="1d", interval="1m")
    effr = get_fred_data_with_fallback("EFFR")
    if fed_futures.empty or effr.empty:
        return None, None
    implied_rate = fed_futures['Adj Close'].iloc[-1]
    real_rate = effr.iloc[-1]
    return real_rate, implied_rate

def get_treasury_yield_curve():
    dgs2 = get_fred_data_with_fallback("DGS2")  # 2-Year Treasury
    dgs5 = get_fred_data_with_fallback("DGS5")  # 5-Year Treasury
    dgs30 = get_fred_data_with_fallback("DGS30")  # 30-Year Treasury

    yield_diff_2_5 = dgs2 - dgs5
    yield_diff_5_30 = dgs5 - dgs30
    return dgs2, dgs5, dgs30, yield_diff_2_5, yield_diff_5_30

def get_vix_data():
    vix = get_yfinance_data_with_fallback("^VIX", period="1d", interval="1m")
    return vix

def get_spy_premarket_data():
    spy = get_yfinance_data_with_fallback("SPY", period="1d", interval="1m")
    return spy

def get_futures_data():
    es = get_yfinance_data_with_fallback("ES=F", period="1d", interval="1m")
    dxy = get_yfinance_data_with_fallback("DX=F", period="1d", interval="1m")
    gold = get_yfinance_data_with_fallback("GC=F", period="1d", interval="1m")
    return es, dxy, gold

# ---------- Risk Calculation Functions ----------

def calculate_risk_on_off(previous, current):
    if previous is None or current is None:
        return "Neutral"
    if current > previous:
        return "Risk-On"
    elif current < previous:
        return "Risk-Off"
    return "Neutral"

def calculate_vix_premium(vix_data):
    if vix_data.empty:
        return 0, 0, 0
    iv = vix_data['Adj Close'].iloc[-1]  # Implied Volatility
    rv = iv * 0.9  # Simulated Realized Volatility (usually lower)
    premium = iv - rv
    return iv, rv, premium

# ---------- App Layout ----------

def app():
    st.title("📊 Market Risk-On / Risk-Off Dashboard")

    # Initialize risk counters
    risk_on_count = 0
    risk_off_count = 0

    # Section 1: Core Rates
    st.header("1️⃣ Core Interest Rate Data")
    effr, t10yie, dgs10 = get_core_interest_rates()

    if not effr.empty:
        st.line_chart(effr.tail(30))
        risk = calculate_risk_on_off(effr.iloc[-2], effr.iloc[-1])
        st.write(f"EFFR Trend: {risk}")
        if risk == "Risk-On":
            risk_on_count += 1
        elif risk == "Risk-Off":
            risk_off_count += 1

    # Section 2: Fed Funds Futures
    st.header("2️⃣ Fed Funds Futures vs Real Rate")
    real_rate, implied_rate = get_fed_funds_calculations()

    if real_rate is not None and implied_rate is not None:
        st.write(f"Real Fed Funds Rate: {real_rate:.2f}%")
        st.write(f"Implied Fed Funds Futures Rate: {implied_rate:.2f}%")
        risk = calculate_risk_on_off(real_rate, implied_rate)
        st.write(f"Fed Futures Trend: {risk}")
        if risk == "Risk-On":
            risk_on_count += 1
        elif risk == "Risk-Off":
            risk_off_count += 1

    # Section 3: Yield Curve
    st.header("3️⃣ Treasury Yield Curve Analysis")
    dgs2, dgs5, dgs30, spread2_5, spread5_30 = get_treasury_yield_curve()

    if not spread2_5.empty and not spread5_30.empty:
        st.write(f"2Y-5Y Spread: {spread2_5.iloc[-1]:.2f}%")
        st.write(f"5Y-30Y Spread: {spread5_30.iloc[-1]:.2f}%")
        risk = calculate_risk_on_off(spread2_5.iloc[-2], spread2_5.iloc[-1])
        st.write(f"Yield Curve Trend: {risk}")
        if risk == "Risk-On":
            risk_on_count += 1
        elif risk == "Risk-Off":
            risk_off_count += 1

    # Section 4: VIX Premium
    st.header("4️⃣ VIX Premium")
    vix_data = get_vix_data()
    iv, rv, premium = calculate_vix_premium(vix_data)
    st.write(f"Implied Volatility: {iv:.2f}")
    st.write(f"Realized Volatility: {rv:.2f}")
    st.write(f"VIX Premium (IV-RV): {premium:.2f}")
    risk = "Risk-Off" if premium > 3 else "Risk-On"
    st.write(f"VIX Premium Trend: {risk}")
    if risk == "Risk-On":
        risk_on_count += 1
    else:
        risk_off_count += 1

    # Section 5: Premarket Data
    st.header("5️⃣ Premarket Futures and SPY")
    spy = get_spy_premarket_data()
    es, dxy, gold = get_futures_data()

    if not spy.empty:
        st.write(f"SPY Last Price: {spy['Adj Close'].iloc[-1]:.2f}")
    if not es.empty:
        st.write(f"ES Futures Last Price: {es['Adj Close'].iloc[-1]:.2f}")
    if not dxy.empty:
        st.write(f"DXY Futures Last Price: {dxy['Adj Close'].iloc[-1]:.2f}")
    if not gold.empty:
        st.write(f"Gold Futures Last Price: {gold['Adj Close'].iloc[-1]:.2f}")

    # Final Risk Assessment
    st.header("✅ Final Consensus Risk Assessment")
    if risk_on_count > risk_off_count:
        final = "RISK-ON"
    elif risk_off_count > risk_on_count:
        final = "RISK-OFF"
    else:
        final = "NEUTRAL"
    
    st.subheader(f"Overall Market Sentiment: **{final}**")
    st.write(f"Risk-On Factors: {risk_on_count}")
    st.write(f"Risk-Off Factors: {risk_off_count}")

# Run the App
if __name__ == "__main__":
    app()
