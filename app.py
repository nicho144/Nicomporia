# Financial Dashboard with Streamlit

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns
import datetime
from fredapi import Fred

# Streamlit configuration
st.set_page_config(page_title="Financial Dashboard", layout="wide")

# Initialize FRED API
fred = Fred(api_key='f693521d3101f329c121220251a424b3')

# Set plot styles
sns.set(style="whitegrid")

# Define key symbols
symbols = {
    'DXY': 'DX-Y.NYB',
    'GC': 'GC=F',
    'ES': 'ES=F',
    'VIX': '^VIX',
    '10Y': '^TNX',
    'ZB': 'ZB=F'  # 30-year bond futures
}

# Function to fetch premarket prices
def fetch_prices():
    data = {}
    for label, ticker in symbols.items():
        price = yf.Ticker(ticker).history(period='2d', interval='1d')
        data[label] = price
    return data

# Function to get Fed Funds Futures implied rate
def fed_funds_implied():
    future_price = fred.get_series('EFFR')[-1]  # Effective Fed Funds Rate
    implied_rate = 100 - future_price
    return implied_rate

# Function to calculate real interest rate (after inflation)
def real_interest_rate():
    nominal_rate = fred.get_series('DTB3')[-1]  # 3-month Treasury Bill
    cpi = fred.get_series('CPIAUCSL').pct_change()[-1] * 100
    real_rate = nominal_rate - cpi
    return real_rate

# Function to get the full treasury yield curve
def get_yield_curve():
    tenors = ['GS1', 'GS2', 'GS3', 'GS5', 'GS7', 'GS10', 'GS20', 'GS30']
    today_curve = [fred.get_series(ticker)[-1] for ticker in tenors]
    yesterday_curve = [fred.get_series(ticker)[-2] for ticker in tenors]
    return today_curve, yesterday_curve

# Function to check yield curve shape

def describe_curve(today, yesterday):
    delta = np.array(today) - np.array(yesterday)
    slope_today = today[-1] - today[0]
    slope_yesterday = yesterday[-1] - yesterday[0]
    if slope_today > slope_yesterday:
        shape = "Steepening"
    else:
        shape = "Flattening"
    return shape, slope_today, slope_yesterday

# Expected Range for SPY from VIX

def spy_expected_range(vix, spy_price):
    daily_move_pct = vix / np.sqrt(252) / 100
    range_ = spy_price * daily_move_pct
    return range_

# Plotting function for term structure (placeholder)
def plot_term_structure(symbol):
    contracts = [symbol + str(m) for m in ['M24', 'U24', 'Z24', 'H25']]
    prices = [yf.Ticker(c).history(period='1d')['Close'][-1] for c in contracts]
    fig, ax = plt.subplots()
    ax.plot(contracts, prices, marker='o')
    ax.set_title(f"{symbol} Term Structure")
    ax.set_xlabel("Contract")
    ax.set_ylabel("Price")
    st.pyplot(fig)

# Gold contango interpretation (placeholder)
def gold_contango_status():
    front = yf.Ticker('GC=F').history(period='1d')['Close'][-1]
    back = yf.Ticker('GCQ24.CMX').history(period='1d')['Close'][-1]
    if back > front:
        return "Contango widening: Potential inflationary signal"
    else:
        return "Backwardation: May signal tight supply or deflation fears"

# Placeholder for IV/RV and skew data
def implied_vs_realized_vol():
    return "IV > RV = Risk-Off | IV < RV = Risk-On"

# Aggregate risk sentiment
def aggregate_risk_signal():
    implied = fed_funds_implied()
    real_rate = real_interest_rate()
    today_curve, yesterday_curve = get_yield_curve()
    curve_shape, slope_t, slope_y = describe_curve(today_curve, yesterday_curve)
    gold_signal = gold_contango_status()

    signals = []
    if real_rate < 0:
        signals.append("Risk-On: Negative Real Rates")
    else:
        signals.append("Risk-Off: Positive Real Rates")

    if curve_shape == "Steepening":
        signals.append("Risk-On: Curve Steepening")
    else:
        signals.append("Risk-Off: Curve Flattening")

    signals.append(gold_signal)
    return signals

# Streamlit UI
st.title("Macro Financial Risk Dashboard")

st.subheader("Market Signals")
data = fetch_prices()
signals = aggregate_risk_signal()
for s in signals:
    st.markdown(f"- {s}")

vix_val = data['VIX']["Close"][-1]
spy_price = yf.Ticker("SPY").history(period="1d")["Close"][-1]
spy_range = spy_expected_range(vix_val, spy_price)

st.subheader("SPY Expected Range")
st.metric("SPY Expected Daily Range", f"±{spy_range:.2f}")

st.subheader("Gold Term Structure")
plot_term_structure('GC')

st.subheader("S&P 500 Term Structure")
plot_term_structure('ES')

st.subheader("VIX Term Structure")
plot_term_structure('VX')

st.subheader("Yield Curve Slope")
today_curve, yesterday_curve = get_yield_curve()
fig2, ax2 = plt.subplots()
ax2.plot(today_curve, label="Today")
ax2.plot(yesterday_curve, label="Yesterday")
ax2.set_title("Treasury Yield Curve")
ax2.set_xlabel("Maturities")
ax2.set_ylabel("Yield %")
ax2.legend()
st.pyplot(fig2)

st.subheader("IV vs RV Commentary")
st.markdown(implied_vs_realized_vol())
