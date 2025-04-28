import pandas as pd
import yfinance as yf
import streamlit as st
from fredapi import Fred
import numpy as np
import matplotlib.pyplot as plt

# Set your correct FRED API key
fred_api_key = "7607ca41e2ca69163937ebf6b879d0ce"
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

# Fetch volatility index (VIX)
def get_volatility_index():
    vix_data = yf.download("^VIX", period="1d", interval="1m")
    try:
        vix_volatility = vix_data['Adj Close'].iloc[-1]
        return vix_volatility
    except KeyError:
        st.error("Error fetching VIX data: Missing 'Adj Close' column.")
        return None

# Fetch pre-market data for SPY (S&P 500 ETF)
def get_spy_premarket_data():
    spy_data = yf.download("SPY", period="1d", interval="1m")
    try:
        premarket_price = spy_data['Adj Close'].iloc[0]  # Getting first pre-market price
        return premarket_price
    except KeyError:
        st.error("Error fetching SPY pre-market data: Missing 'Adj Close' column.")
        return None

# Straddle calculation - ATM Expected Range
def calculate_atm_straddle(expected_move, strike_price):
    call_price = expected_move
    put_price = expected_move
    total_straddle_cost = call_price + put_price
    expected_range = (strike_price - total_straddle_cost, strike_price + total_straddle_cost)
    return expected_range

# Fetch and calculate the treasury yield curve and steepening/flattening
def get_treasury_yield_curve():
    dgs2 = get_fred_data("DGS2")  # 2 Year Treasury Constant Maturity Rate
    dgs5 = get_fred_data("DGS5")  # 5 Year Treasury Constant Maturity Rate
    dgs30 = get_fred_data("DGS30")  # 30 Year Treasury Constant Maturity Rate

    if dgs2 is not None and dgs5 is not None and dgs30 is not None:
        # Calculate steepening/flattening
        yield_diff_2_5 = dgs5 - dgs2
        yield_diff_5_30 = dgs30 - dgs5
        return dgs2, dgs5, dgs30, yield_diff_2_5, yield_diff_5_30
    else:
        return None, None, None, None, None

# Function to calculate and display market sentiment (Breathe Indicators)
def market_sentiment():
    vix_volatility = get_volatility_index()
    if vix_volatility is None:
        return "Error fetching VIX"
    elif vix_volatility < 20:
        return "Risk-On (Low Volatility)"
    elif vix_volatility >= 20 and vix_volatility <= 30:
        return "Neutral"
    else:
        return "Risk-Off (High Volatility)"

# Function to display the financial dashboard
def app():
    st.title("Comprehensive Financial Dashboard")

    # Section: Core Interest Rate Data
    st.header("🔵 Core Interest Rate Data")
    effr, t10yie, dgs10 = get_core_interest_rates()
    
    if effr is not None:
        st.subheader("Effective Federal Funds Rate (EFFR)")
        st.line_chart(effr.tail(30))  # Display latest values

    if t10yie is not None:
        st.subheader("10Y Inflation-Indexed Treasury Yield (T10YIE)")
        st.line_chart(t10yie.tail(30))

    if dgs10 is not None:
        st.subheader("10 Year Treasury Yield (DGS10)")
        st.line_chart(dgs10.tail(30))

    # Section: Treasury Yield Curve and Steepening/Flattening
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

    # Section: Volatility Gauges
    st.header("🔥 Volatility Gauges")
    vix_volatility = get_volatility_index()
    
    if vix_volatility is not None:
        st.subheader(f"VIX Volatility Index: {vix_volatility}")
        sentiment = market_sentiment()
        st.write(f"Market Sentiment: {sentiment}")

    # Section: Pre-market Data for SPY
    st.header("📈 Pre-market Data for SPY")
    premarket_price = get_spy_premarket_data()
    
    if premarket_price is not None:
        st.subheader(f"Pre-market SPY Price: {premarket_price}")

    # Section: ATM Straddle Expected Range
    st.header("📊 ATM Straddle Expected Range Calculation")
    if premarket_price is not None:
        expected_move = 2  # Example of expected move in points (you can adjust this logic)
        strike_price = premarket_price
        expected_range = calculate_atm_straddle(expected_move, strike_price)
        st.write(f"Expected ATM Straddle Range: {expected_range}")

# Run the app
if __name__ == "__main__":
    app()
