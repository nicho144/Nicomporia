import pandas as pd
import yfinance as yf
import streamlit as st
from fredapi import Fred
import numpy as np
import matplotlib.pyplot as plt

# Set the correct FRED API key
fred_api_key = "31934d0584960301655194d067cc9399"
fred = Fred(api_key=fred_api_key)

# Fetch FRED data for core interest rates and treasury yields
def get_fred_data(series_id):
    try:
        data = fred.get_series(series_id)
        return data
    except Exception as e:
        st.error(f"Error fetching FRED data for {series_id}: {e}")
        return None

# Fetch core interest rates
def get_core_interest_rates():
    effr = get_fred_data("EFFR")  # Effective Federal Funds Rate
    t10yie = get_fred_data("T10YIE")  # 10Y Inflation-Indexed Treasury Yield
    dgs10 = get_fred_data("DGS10")  # 10 Year Treasury Constant Maturity Rate
    return effr, t10yie, dgs10

# Fetch volatility index (VIX) and relevant metrics
def get_vix_data():
    vix_data = yf.download("^VIX", period="1d", interval="1m")
    try:
        vix_volatility = vix_data['Adj Close'].iloc[-1]
        return vix_volatility
    except KeyError:
        st.error("Error fetching VIX data: Missing 'Adj Close' column.")
        return None

# Fetch futures data (ES, DXY, Gold)
def get_futures_data():
    es_futures = yf.download("ES=F", period="1d", interval="1m")
    dxy_futures = yf.download("DX=F", period="1d", interval="1m")
    gold_futures = yf.download("GC=F", period="1d", interval="1m")
    return es_futures, dxy_futures, gold_futures

# Fetch premarket data for SPY (S&P 500 ETF)
def get_spy_premarket_data():
    spy_data = yf.download("SPY", period="1d", interval="1m")
    try:
        premarket_price = spy_data['Adj Close'].iloc[0]  # Getting first pre-market price
        return premarket_price
    except KeyError:
        st.error("Error fetching SPY pre-market data: Missing 'Adj Close' column.")
        return None

# Function to calculate VIX Premium (IV/RV) and skew
def calculate_vix_premium():
    vix_data = yf.download("^VIX", period="1d", interval="1m")
    vix_future_data = yf.download("^VIXF", period="1d", interval="1m")  # VIX Futures
    if vix_data is not None and vix_future_data is not None:
        iv = vix_data['Adj Close'].iloc[-1]
        rv = vix_future_data['Adj Close'].iloc[-1]
        vix_premium = iv - rv
        return iv, rv, vix_premium
    else:
        return None, None, None

# Function to calculate the fair price and implied open for ES Futures
def calculate_es_futures():
    es_futures, _, _ = get_futures_data()
    if es_futures is not None:
        es_open = es_futures['Open'].iloc[0]  # Opening price of ES futures
        es_close = es_futures['Adj Close'].iloc[-1]  # Close price of ES futures
        fair_price = (es_open + es_close) / 2  # Fair price estimate
        implied_open = es_close - es_open  # Implied open (discount/premium)
        contango = "Contango" if es_open < es_close else "Backwardation"
        return fair_price, implied_open, contango
    else:
        return None, None, None

# Fed Funds calculations: real interest rate and implied rate
def get_fed_funds_calculations():
    effr = get_fred_data("EFFR")  # Federal funds rate
    if effr is not None:
        real_interest_rate = effr.tail(1).iloc[0]
        implied_rate = real_interest_rate + 0.25  # Assume implied rate is 0.25% higher (example)
        return real_interest_rate, implied_rate
    return None, None

# Calculate risk-on or risk-off for a given variable
def calculate_risk_on_off(previous_value, current_value):
    if current_value > previous_value:
        return "Risk-On"
    elif current_value < previous_value:
        return "Risk-Off"
    return "Neutral"

# Section for treasury yield curve and steepening/flattening
def get_treasury_yield_curve():
    dgs2 = get_fred_data("DGS2")  # 2 Year Treasury Constant Maturity Rate
    dgs5 = get_fred_data("DGS5")  # 5 Year Treasury Constant Maturity Rate
    dgs30 = get_fred_data("DGS30")  # 30 Year Treasury Constant Maturity Rate

    if dgs2 is not None and dgs5 is not None and dgs30 is not None:
        yield_diff_2_5 = dgs5 - dgs2
        yield_diff_5_30 = dgs30 - dgs5
        return dgs2, dgs5, dgs30, yield_diff_2_5, yield_diff_5_30
    else:
        return None, None, None, None, None

# Function to display the financial dashboard
def app():
    st.title("Comprehensive Financial Dashboard")

    # Initialize variables for risk-on and risk-off
    risk_on_count = 0
    risk_off_count = 0

    # Section 1: Core Interest Rate Data
    st.header("🔵 Core Interest Rate Data")
    effr, t10yie, dgs10 = get_core_interest_rates()
    
    if effr is not None:
        st.subheader("Effective Federal Funds Rate (EFFR)")
        st.line_chart(effr.tail(30))  # Display latest values
        risk_condition = calculate_risk_on_off(effr.iloc[-2], effr.iloc[-1])
        if risk_condition == "Risk-On":
            risk_on_count += 1
        elif risk_condition == "Risk-Off":
            risk_off_count += 1
        st.write(f"Risk Condition: {risk_condition}")

    if t10yie is not None:
        st.subheader("10Y Inflation-Indexed Treasury Yield (T10YIE)")
        st.line_chart(t10yie.tail(30))

    if dgs10 is not None:
        st.subheader("10 Year Treasury Yield (DGS10)")
        st.line_chart(dgs10.tail(30))

    # Section 2: Treasury Yield Curve and Steepening/Flattening
    st.header("📈 Treasury Yield Curve and Steepening/Flattening")
    dgs2, dgs5, dgs30, yield_diff_2_5, yield_diff_5_30 = get_treasury_yield_curve()

    if dgs2 is not None and dgs5 is not None and dgs30 is not None:
        st.subheader("Treasury Yields")
        st.write(f"2 Year Yield (DGS2): {dgs2.iloc[-1]}")
        st.write(f"5 Year Yield (DGS5): {dgs5.iloc[-1]}")
        st.write(f"30 Year Yield (DGS30): {dgs30.iloc[-1]}")
        
        # Display steepening/flattening analysis
        st.subheader("Yield Curve Steepening/Flattening")
        st.write(f"2-5 Year Yield Spread: {yield_diff_2_5.iloc[-1]}")
        st.write(f"5-30 Year Yield Spread: {yield_diff_5_30.iloc[-1]}")

    # Section 3: VIX Premium, Skew, and Futures
    st.header("🔥 VIX and Volatility Metrics")
    iv, rv, vix_premium = calculate_vix_premium()
    st.write(f"VIX: {iv}")
    st.write(f"VIX Futures: {rv}")
    st.write(f"VIX Premium: {vix_premium}")

    # Section 4: ES Futures and Risk-On/Risk-Off
    st.header("📈 ES Futures Data")
    fair_price, implied_open, contango = calculate_es_futures()
    st.write(f"Fair Price: {fair_price}")
    st.write(f"Implied Open: {implied_open}")
    st.write(f"Contango Status: {contango}")

    # Section 5: Risk-On / Risk-Off Consensus
    st.header("⚖️ Risk-On / Risk-Off Consensus")
    st.write(f"Risk-On Count: {risk_on_count}")
    st.write(f"Risk-Off Count: {risk_off_count}")
    if risk_on_count > risk_off_count:
        st.write("Consensus: Risk-On")
    else:
        st.write("Consensus: Risk-Off")

# Run the app
if __name__ == "__main__":
    app()
