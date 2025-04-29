import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from fredapi import Fred
import os

# FRED setup
FRED_API_KEY = os.getenv("FRED_API_KEY") or "f693521d3101f329c121220251a424b3"
fred = Fred(api_key=FRED_API_KEY)

def fetch_yield_curve():
    today = datetime.today().date()
    start_date = today - timedelta(days=30)
    try:
        two_year = fred.get_series('GS2', start_date, today).dropna().iloc[-1]
        five_year = fred.get_series('GS5', start_date, today).dropna().iloc[-1]
        ten_year = fred.get_series('GS10', start_date, today).dropna().iloc[-1]
        return {'2Y': two_year, '5Y': five_year, '10Y': ten_year}
    except IndexError:
        st.error("Yield data not available from FRED. Try again later.")
        return {'2Y': None, '5Y': None, '10Y': None}

def calculate_spreads(yield_data):
    try:
        spread_2y5y = yield_data['2Y'] - yield_data['5Y']
        spread_2y10y = yield_data['2Y'] - yield_data['10Y']
        return spread_2y5y, spread_2y10y
    except:
        return None, None

def fetch_vix_term_structure():
    tickers = ['^VIX', '^VIX9D', '^VIX3M']
    data = yf.download(tickers, period="5d", interval="1d")
    try:
        close = data['Adj Close'].iloc[-1]
        return close['^VIX'], close['^VIX9D'], close['^VIX3M']
    except (IndexError, KeyError):
        st.error("VIX data unavailable.")
        return None, None, None

def fetch_iv_rv(symbol='SPY'):
    data = yf.download(symbol, period="60d", interval="1d")
    returns = data['Adj Close'].pct_change().dropna()
    rv = np.std(returns) * np.sqrt(252)
    iv = yf.Ticker(symbol).info.get('impliedVolatility', np.nan)
    return iv, rv, iv - rv

def fetch_straddle_expected_range(symbol='SPY'):
    opt = yf.Ticker(symbol).option_chain()
    atm = opt.calls.iloc[(opt.calls['strike'] - yf.Ticker(symbol).info['regularMarketPrice']).abs().argmin()]
    return atm['impliedVolatility'] * yf.Ticker(symbol).info['regularMarketPrice'] * np.sqrt(1/12)

def fetch_es_futures_data():
    es = yf.Ticker('ES=F')
    spot = yf.Ticker('SPY').info['regularMarketPrice']
    fut_price = es.history(period='1d')['Close'].iloc[-1]
    return fut_price, spot, fut_price - spot

def main():
    st.title("Comprehensive Market Risk Dashboard")

    st.header("Yield Curve")
    yields = fetch_yield_curve()
    if yields['2Y'] is not None:
        st.write("Yields:", yields)
        spread_2y5y, spread_2y10y = calculate_spreads(yields)
        st.write("2Y-5Y Spread:", spread_2y5y)
        st.write("2Y-10Y Spread:", spread_2y10y)

    st.header("Volatility Measures")
    iv, rv, vrp = fetch_iv_rv()
    st.write("Implied Volatility:", iv)
    st.write("Realized Volatility:", rv)
    st.write("Volatility Risk Premium:", vrp)

    st.header("VIX Term Structure")
    vix, vix9d, vix3m = fetch_vix_term_structure()
    if vix and vix9d and vix3m:
        st.write("VIX Spot:", vix)
        st.write("VIX 9D:", vix9d)
        st.write("VIX 3M:", vix3m)
        st.write("Contango/Backwardation:", "Contango" if vix3m > vix else "Backwardation")

    st.header("Expected Move from ATM Straddle")
    expected_range = fetch_straddle_expected_range()
    st.write("1-month expected move:", expected_range)

    st.header("ES Futures vs Spot (Fair Value)")
    fut, spot, diff = fetch_es_futures_data()
    st.write("Futures:", fut)
    st.write("Spot:", spot)
    st.write("Discount/Premium:", diff)

if __name__ == "__main__":
    main()
