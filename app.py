import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
from fredapi import Fred

# FRED API setup (Insert your API key here)
api_key = "abcdefghijklmnopqrstuvwxyz123456"  # Replace with your actual FRED API key
fred = Fred(api_key=api_key)

# Function to fetch FRED data
def get_fred_data(series_id):
    try:
        data = fred.get_series(series_id)
        return data
    except Exception as e:
        st.error(f"Error fetching FRED data for {series_id}: {e}")
        return None

# Fetching core interest rate data from FRED
def get_fed_funds_rate():
    return get_fred_data('EFFR')

def get_inflation_rate():
    return get_fred_data('T10YIE')

# Function to fetch implied rate from Yahoo Finance (Fed Funds Futures Example)
def get_implied_rate(symbol):
    try:
        data = yf.download(symbol, period="5d", interval="1d")
        implied_rate = 100 - data['Adj Close'].iloc[-1]  # Implied rate is 100 minus price
        return implied_rate
    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {e}")
        return None

# Function to fetch Yield Curve data (example for 10Y Treasury)
def get_yield_curve_data():
    # Example: Fetching 10 Year Treasury yield
    return get_fred_data('DGS10')

# Fetching Treasury Yield Curve data from FRED
def get_10yr_yield():
    return get_yield_curve_data()

# Volatility Gauges and Risk On/Risk Off Indicators
def get_volatility_index():
    # Example: Using VIX for volatility measure
    vix_data = yf.download("^VIX", period="5d", interval="1d")
    vix_volatility = vix_data['Adj Close'].iloc[-1]
    return vix_volatility

def get_sp500_volatility():
    sp500_data = yf.download('^GSPC', period="5d", interval="1d")
    sp500_volatility = np.std(sp500_data['Adj Close'])
    return sp500_volatility

# Breakeven Inflation and Yield Curve Spreads
def get_breakeven_inflation():
    inflation_data = get_fred_data('T10YIB')
    if inflation_data is not None:
        return inflation_data.iloc[-1]
    return None

def get_credit_spread():
    credit_spread_data = get_fred_data('BAMLH0A0HYM2')
    if credit_spread_data is not None:
        return credit_spread_data.iloc[-1]
    return None

# Plotting the Yield Curve
def plot_yield_curve():
    date_today = datetime.datetime.today().strftime('%Y-%m-%d')
    yield_data = {
        '2-Year': get_fred_data('DGS2'),
        '5-Year': get_fred_data('DGS5'),
        '10-Year': get_fred_data('DGS10'),
        '30-Year': get_fred_data('DGS30')
    }
    
    # Plot the yield curve for available data
    plt.figure(figsize=(10, 6))
    for label, data in yield_data.items():
        if data is not None:
            plt.plot(data.index, data.values, label=label)
    
    plt.title(f"US Treasury Yield Curve as of {date_today}")
    plt.xlabel("Date")
    plt.ylabel("Yield (%)")
    plt.legend()
    st.pyplot(plt)

# Streamlit UI
def app():
    st.title("Risk-On / Risk-Off Consensus Dashboard")
    
    # Core Interest Rates and Implied Rates
    st.header("🔵 Core Interest Rate Data")
    fed_funds_rate = get_fed_funds_rate()
    if fed_funds_rate is not None:
        st.subheader("Federal Funds Rate")
        st.line_chart(fed_funds_rate)

    inflation_rate = get_inflation_rate()
    if inflation_rate is not None:
        st.subheader("Inflation Rate (10Y Expected)")
        st.line_chart(inflation_rate)

    # Implied Fed Funds Rate (from Fed Futures)
    implied_rate = get_implied_rate('ZQ=F')
    if implied_rate is not None:
        st.subheader("Implied Fed Funds Rate")
        st.write(f"Implied Rate: {implied_rate:.2f}%")

    # 10Y Treasury Yield
    ten_year_yield = get_10yr_yield()
    if ten_year_yield is not None:
        st.subheader("10-Year Treasury Yield")
        st.write(f"10Y Yield: {ten_year_yield[-1]:.2f}%")
    
    # Volatility Gauges
    st.header("🔥 Volatility Gauges")
    vix_volatility = get_volatility_index()
    if vix_volatility is not None:
        st.write(f"VIX Volatility Index: {vix_volatility:.2f}")
    
    sp500_volatility = get_sp500_volatility()
    if sp500_volatility is not None:
        st.write(f"SP500 Volatility: {sp500_volatility:.2f}")

    # Breakeven Inflation
    breakeven_inflation = get_breakeven_inflation()
    if breakeven_inflation is not None:
        st.write(f"Breakeven Inflation (10Y): {breakeven_inflation:.2f}%")

    # Credit Spreads
    credit_spread = get_credit_spread()
    if credit_spread is not None:
        st.write(f"Credit Spread (BAML HYM2): {credit_spread:.2f}%")

    # Yield Curve & Credit Spread Data Plot
    st.header("📈 Yield Curve & Credit Spread Data")
    plot_yield_curve()

# Run the Streamlit app
if __name__ == "__main__":
    app()
