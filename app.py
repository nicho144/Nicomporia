import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import datetime
from fredapi import Fred
import plotly.graph_objs as go

# Your FRED API key
fred = Fred(api_key='YOUR_FRED_API_KEY')

# Fallback function for fetching FRED data
def get_fred_data_with_fallback(series_id):
    try:
        data = fred.get_series(series_id)
        if data.empty:
            raise ValueError(f"Data for {series_id} is empty.")
        return data
    except Exception as e:
        st.error(f"Error fetching FRED data for {series_id}: {e}")
        # Returning a fallback series (empty or last known value)
        fallback_data = pd.Series([0] * 30)  # Or use a default historical value
        return fallback_data

# Fallback for VIX data
def get_vix_data_with_fallback():
    try:
        vix_data = yf.download("^VIX", period="1d", interval="1m")
        vix_volatility = vix_data['Adj Close'].iloc[-1]
        return vix_volatility
    except (KeyError, IndexError, ValueError) as e:
        st.error(f"Error fetching VIX data: {e}")
        return 15  # Default fallback value for VIX (neutral state, example)

# Fallback for Fed Funds data
def get_fed_funds_data_with_fallback():
    try:
        effr = get_fred_data_with_fallback("EFFR")
        fed_funds_futures = yf.download("FF=F", period="1d", interval="1m")  # Example for Fed Funds Futures
        if fed_funds_futures.empty:
            raise ValueError("Fed Funds Futures data is empty.")
        real_interest_rate = effr.tail(1).iloc[0]
        implied_rate = fed_funds_futures['Adj Close'].iloc[0]  # Implied rate
        return real_interest_rate, implied_rate
    except Exception as e:
        st.error(f"Error fetching Fed Funds data: {e}")
        return None, None

# Risk-On or Risk-Off calculation
def calculate_risk_on_off_with_fallback(previous_value, current_value):
    if previous_value is None or current_value is None:
        st.warning("Data for risk calculation is unavailable, using default 'Neutral' state.")
        return "Neutral"
    if current_value > previous_value:
        return "Risk-On"
    elif current_value < previous_value:
        return "Risk-Off"
    return "Neutral"

# Get Treasury yield curve data with fallback
def get_treasury_yield_curve():
    try:
        dgs2 = get_fred_data_with_fallback("DGS2")  # 2-Year Yield
        dgs5 = get_fred_data_with_fallback("DGS5")  # 5-Year Yield
        dgs30 = get_fred_data_with_fallback("DGS30")  # 30-Year Yield

        yield_diff_2_5 = dgs2 - dgs5
        yield_diff_5_30 = dgs5 - dgs30
        return dgs2, dgs5, dgs30, yield_diff_2_5, yield_diff_5_30
    except Exception as e:
        st.error(f"Error fetching Treasury Yield Curve data: {e}")
        return None, None, None, None, None

# Fetch and calculate VIX Premium (IV/RV)
def calculate_vix_premium():
    # Placeholder: actual logic to calculate IV and RV should be implemented here.
    iv = 18  # Placeholder value for Implied Volatility
    rv = 16  # Placeholder value for Realized Volatility
    vix_premium = iv - rv
    return iv, rv, vix_premium

# Get Premarket data for SPY and Futures
def get_spy_premarket_data():
    spy_data = yf.download("SPY", period="1d", interval="1m")
    return spy_data['Adj Close'].iloc[-1]

# Fetch Futures data (ES, DXY, Gold)
def get_futures_data():
    try:
        es_futures = yf.download("ES=F", period="1d", interval="1m")
        dxy_futures = yf.download("DX=F", period="1d", interval="1m")
        gold_futures = yf.download("GC=F", period="1d", interval="1m")
        
        return es_futures, dxy_futures, gold_futures
    except Exception as e:
        st.error(f"Error fetching Futures data: {e}")
        return None, None, None

# Main application
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
        risk_condition = calculate_risk_on_off_with_fallback(effr.iloc[-2], effr.iloc[-1])
        if risk_condition == "Risk-On":
            risk_on_count += 1
        elif risk_condition == "Risk-Off":
            risk_off_count += 1
        st.write(f"Risk Condition: {risk_condition}")

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
    st.header("📉 VIX Premium and Futures")
    vix_volatility = get_vix_data_with_fallback()
    st.write(f"VIX Volatility: {vix_volatility}")
    
    iv, rv, vix_premium = calculate_vix_premium()
    st.write(f"IV/RV Premium: {vix_premium}")

    # Section 4: Fed Funds Data and Calculations
    st.header("💵 Fed Funds Rate Calculations")
    real_interest_rate, implied_rate = get_fed_funds_calculations()
    if real_interest_rate is not None and implied_rate is not None:
        st.write(f"Real Interest Rate (EFFR): {real_interest_rate}")
        st.write(f"Implied Interest Rate (Fed Futures): {implied_rate}")
    
    # Section 5: Risk-On/Risk-Off Calculation
    st.header("📊 Risk-On vs Risk-Off Summary")
    consensus_risk = "Risk-On" if risk_on_count > risk_off_count else "Risk-Off"
    st.write(f"Overall Risk Condition: {consensus_risk}")

    # Section 6: Premarket Data
    st.header("🕒 Premarket Data")
    premarket_spy = get_spy_premarket_data()
    st.write(f"SPY Premarket Price: {premarket_spy}")

    es_futures, dxy_futures, gold_futures = get_futures_data()
    if es_futures is not None:
        st.write(f"ES Futures Price: {es_futures['Adj Close'].iloc[-1]}")
    
    if dxy_futures is not None:
        st.write(f"DXY Futures Price: {dxy_futures['Adj Close'].iloc[-1]}")
    
    if gold_futures is not None:
        st.write(f"Gold Futures Price: {gold_futures['Adj Close'].iloc[-1]}")
    
    # Section 7: Final Sentiment Analysis
    st.header("💬 Economic Sentiment Analysis")
    st.write("Sentiment analysis from news (using external APIs)")

    # Final aggregation of all factors
    st.write(f"Risk-On Count: {risk_on_count}")
    st.write(f"Risk-Off Count: {risk_off_count}")
    st.write(f"Consensus: {consensus_risk}")
    
# Call the application to run
if __name__ == "__main__":
    app()
