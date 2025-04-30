"""
Financial Dashboard App with Hardcoded FRED API Key
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from fredapi import Fred
import plotly.express as px
import requests
from datetime import datetime, timedelta

# --- Hardcoded FRED API Key ---
FRED_API_KEY = "dceb19d6ccadfb4115c3ac2493b7d5ed"

# Initialize Fred API
try:
    fred = Fred(api_key=FRED_API_KEY)
except Exception as e:
    st.error(f"Failed to connect to FRED API: {e}")
    st.stop()

# --- Helper Functions ---

@st.cache_data(ttl="1d")
def get_treasury_yields():
    try:
        return {
            'DGS2': round(fred.get_series('DGS2')[-1], 2),
            'DGS5': round(fred.get_series('DGS5')[-1], 2),
            'DGS10': round(fred.get_series('DGS10')[-1], 2)
        }
    except Exception as e:
        st.warning("Failed to fetch yields from FRED.")
        return {'DGS2': None, 'DGS5': None, 'DGS10': None}

@st.cache_data(ttl="1d")
def get_fed_funds_rate():
    return round(fred.get_series('DFF')[-1], 2)

@st.cache_data(ttl="1d")
def get_cpi():
    return round(fred.get_series('CPIAUCSL', observation_start='2023-01-01')[-1], 2)

def get_spreads(yields):
    return {
        '2Y-5Y': round(yields['DGS2'] - yields['DGS5'], 2),
        '2Y-10Y': round(yields['DGS2'] - yields['DGS10'], 2)
    }

def get_bullish_signal(change):
    if change > 0:
        return "Bullish"
    elif change < 0:
        return "Bearish"
    else:
        return "Neutral"

@st.cache_data(ttl="1h")
def get_market_data(tickers=['SPY', 'GLD', 'DX-Y.NYB', 'ES=F']):
    data = {}
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2d")
            today = hist.iloc[-1]['Close']
            yesterday = hist.iloc[-2]['Close']
            change = today - yesterday
            data[ticker] = {"close": round(today, 2), "change": round(change, 2)}
        except Exception as e:
            data[ticker] = {"close": "N/A", "change": 0}
    return data

@st.cache_data(ttl="1h")
def get_vix_term_structure():
    url = "https://cdn.cboe.com/api/global/us_indices/dashboard/volatility_dashboard_data.json"
    try:
        response = requests.get(url).json()
        vix_spot = response["data"]["vix"]
        vix_futures = response["data"]["vix_futures"]
        return {
            "spot": round(vix_spot, 2),
            "futures": [{"name": f["label"], "value": round(f["value"], 2)} for f in vix_futures]
        }
    except Exception as e:
        st.warning("Could not fetch VIX data.")
        return {"spot": "N/A", "futures": []}

def analyze_vix_curve(vix_data):
    if not vix_data["futures"]:
        return "N/A"
    front = vix_data["futures"][0]["value"]
    back = vix_data["futures"][1]["value"]
    spread = back - front
    if spread > 0:
        return "Contango (Risk On)"
    else:
        return "Backwardation (Risk Off)"

def risk_on_off_signals(bond_signal, equity_signal, vix_signal):
    score = 0
    if bond_signal == "Bearish":
        score += 1  # rising yields = risk on
    if equity_signal == "Bullish":
        score += 1
    if vix_signal == "Contango (Risk On)":
        score += 1
    
    if score >= 2:
        return "🟢 Risk On"
    else:
        return "🔴 Risk Off"

def gold_vs_bonds_signal(real_rate_change, gold_price_change, bond_yield_change):
    if real_rate_change is None or gold_price_change is None or bond_yield_change is None:
        return "⚪ Neutral"

    if real_rate_change < 0 and bond_yield_change < 0 and gold_price_change > 0:
        return "🟡 Gold More Attractive Today"
    elif real_rate_change > 0 and bond_yield_change > 0:
        return "🟢 Bonds More Attractive"
    else:
        return "⚪ Neutral"

# --- Dashboard UI ---

st.set_page_config(layout="wide", page_title="📈 Financial Dashboard", page_icon="📊")

# Sidebar
st.sidebar.markdown("### Last Updated: " + str(datetime.now().strftime("%Y-%m-%d %H:%M")))
st.sidebar.markdown("#### About")
st.sidebar.info("Tracks Treasury Yields, VIX Term Structure, Market Futures, "
                "and predicts Institutional Money Flow.")

st.title("📊 Financial Market Sentiment Dashboard")

# Yields
with st.expander("📉 Treasury Yield Curve", expanded=True):
    yields = get_treasury_yields()
    if all(yields.values()):
        spreads = get_spreads(yields)

        col1, col2, col3 = st.columns(3)
        col1.metric("2-Year Yield", f"{yields['DGS2']:.2f}%")
        col2.metric("5-Year Yield", f"{yields['DGS5']:.2f}%")
        col3.metric("10-Year Yield", f"{yields['DGS10']:.2f}%")

        df = pd.DataFrame({
            "Tenor": ["2Y", "5Y", "10Y"],
            "Yield": [yields['DGS2'], yields['DGS5'], yields['DGS10']]
        })
        fig = px.line(df, x="Tenor", y="Yield", title="Treasury Yield Curve")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Spreads")
        st.write(f"2Y–5Y: {spreads['2Y-5Y']:.2f}% → {get_bullish_signal(spreads['2Y-5Y'])}")
        st.write(f"2Y–10Y: {spreads['2Y-10Y']:.2f}% → {get_bullish_signal(spreads['2Y-10Y'])}")
    else:
        st.error("Could not load treasury yield data.")

# Fed Funds Rate
with st.expander("🏦 Fed Funds & Real Interest Rate"):
    try:
        fed_rate = get_fed_funds_rate()
        cpi = get_cpi()
        real_rate = fed_rate - cpi

        col1, col2, col3 = st.columns(3)
        col1.metric("Fed Funds Rate", f"{fed_rate:.2f}%")
        col2.metric("CPI (YoY)", f"{cpi:.2f}%")
        col3.metric("Real Interest Rate", f"{real_rate:.2f}%")
    except:
        st.error("Error loading interest rate data.")

# VIX Term Structure
with st.expander("📉 VIX Term Structure"):
    vix_data = get_vix_term_structure()
    vix_signal = analyze_vix_curve(vix_data)

    if vix_data["spot"] != "N/A":
        st.write(f"Spot VIX: {vix_data['spot']:.2f}")
        st.write(f"Front Future: {vix_data['futures'][0]['value']:.2f}")
        st.write(f"Next Future: {vix_data['futures'][1]['value']:.2f}")
        st.write(f"Signal: **{vix_signal}**")
    else:
        st.error("Could not retrieve VIX data.")

# Market Futures
with st.expander("💱 Market Futures (SPY, GLD, DXY, ES)", expanded=True):
    market_data = get_market_data(['SPY', 'GLD', 'DX-Y.NYB', 'ES=F'])

    cols = st.columns(len(market_data))
    for i, (ticker, info) in enumerate(market_data.items()):
        cols[i].metric(ticker, f"${info['close']}", delta=f"{info['change']:.2f}")

# Risk Mode
with st.expander("🧠 Risk-On / Risk-Off Signal", expanded=True):
    bond_signal = get_bullish_signal(market_data['GLD']['change'])
    equity_signal = get_bullish_signal(market_data['SPY']['change'])
    risk_mode = risk_on_off_signals(bond_signal, equity_signal, vix_signal)

    st.markdown(f"### Final Risk Signal: **{risk_mode}**")

# Institutional Flow Signal
with st.expander("🏦 Gold vs Bonds Flow Prediction"):
    prev_yields = {
        'DGS10': round(fred.get_series('DGS10', observation_end=datetime.today() - timedelta(days=1))[-1], 2)
    }
    bond_yield_change = round(yields['DGS10'] - prev_yields['DGS10'], 2) if yields['DGS10'] else None
    real_rate_change = None  # Placeholder logic
    gold_price_change = market_data['GLD']['change']

    flow_signal = gold_vs_bonds_signal(real_rate_change, gold_price_change, bond_yield_change)
    st.markdown(f"### 💡 Money Flow Signal: **{flow_signal}**")

# Footer
st.markdown("---")
st.markdown("📌 *Data sources: FRED, Yahoo Finance, CBOE* | "
            "🛠️ *Dashboard built with Python + Streamlit*")