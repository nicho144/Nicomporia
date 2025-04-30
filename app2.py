import streamlit as st
import yfinance as yf
import pandas as pd
from pandas_datareader import data as pdr
import numpy as np
import datetime

# FRED API Key (You should store this securely, e.g., using Streamlit secrets)
FRED_API_KEY = "f693521d3101f329c121220251a424b3"

# --- Data Fetching Functions ---
@st.cache_data(ttl=600)
def fetch_yf_data(ticker, period="2d", interval="1d"):
    """Fetches data from Yahoo Finance."""
    data = yf.download(ticker, period=period, interval=interval)
    if len(data) < 2:
        return None, None, None, None
    current = data.iloc[-1]['Close']
    previous = data.iloc[-2]['Close']
    change = current - previous
    change_percent = (change / previous) * 100
    return current, previous, change, change_percent

@st.cache_data(ttl=3600)
def fetch_fred_data(series_id):
    """Fetches data from FRED."""
    try:
        data = pdr.get_data_fred(series_id)
        if not data.empty:
            current = data.iloc[-1][series_id]
            previous = data.iloc[-2][series_id] if len(data) > 1 else None
            change = current - previous if previous is not None else None
            return current, previous, change
        else:
            return None, None, None
    except Exception as e:
        st.error(f"Error fetching FRED data for {series_id}: {e}")
        return None, None, None

@st.cache_data(ttl=3600)
def fetch_treasury_yields():
    """Fetches current and previous day's Treasury yield curve data."""
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    two_days_ago = today - datetime.timedelta(days=2)

    try:
        today_yields = pdr.get_data_fred(['T2Y', 'T5Y', 'T10Y'], start=today, end=today)
        yesterday_yields = pdr.get_data_fred(['T2Y', 'T5Y', 'T10Y'], start=yesterday, end=yesterday)
        two_days_ago_yields = pdr.get_data_fred(['T2Y', 'T5Y', 'T10Y'], start=two_days_ago, end=two_days_ago)

        current_yields = today_yields.iloc[-1] if not today_yields.empty else None
        previous_yields = yesterday_yields.iloc[-1] if not yesterday_yields.empty else None

        # Handle cases where data might not be available for the exact previous day
        if previous_yields is None:
            previous_yields = two_days_ago_yields.iloc[-1] if not two_days_ago_yields.empty else None

        return current_yields, previous_yields
    except Exception as e:
        st.error(f"Error fetching Treasury yield data: {e}")
        return None, None

# --- Indicator Calculation Functions ---
def calculate_yield_spread(yield1, yield2):
    """Calculates the spread between two yields."""
    if yield1 is not None and yield2 is not None:
        return yield1 - yield2
    return None

def determine_risk_sentiment(vix_change_percent, spread_change):
    """Simple logic to determine risk sentiment."""
    if vix_change_percent is not None and spread_change is not None:
        if vix_change_percent < -1 and spread_change < -0.02:  # Example thresholds
            return "Risk On"
        elif vix_change_percent > 1 and spread_change > 0.02:
            return "Risk Off"
        else:
            return "Neutral"
    return "Neutral"

def determine_bullish_bearish(asset_change_percent):
    """Simple logic for bullish/bearish based on price change."""
    if asset_change_percent is not None:
        if asset_change_percent > 0.5:
            return "Bullish"
        elif asset_change_percent < -0.5:
            return "Bearish"
        else:
            return "Neutral"
    return "Neutral"

# --- Main Streamlit App ---
st.title("Financial Market Dashboard")

# --- Section 1: Futures Data ---
st.header("Futures Data")
col1, col2, col3, col4 = st.columns(4)

# Fetch futures data
vix_current, vix_prev, vix_change, vix_change_percent = fetch_yf_data("VX1!")
spy_current, spy_prev, spy_change, spy_change_percent = fetch_yf_data("ES1!")
gold_current, gold_prev, gold_change, gold_change_percent = fetch_yf_data("GC1!")
dxy_current, dxy_prev, dxy_change, dxy_change_percent = fetch_yf_data("DX1!")

col1.metric("VIX Futures", f"{vix_current:.2f}" if vix_current is not None else "N/A",
            f"{vix_change_percent:.2f}%" if vix_change_percent is not None else "N/A")
col2.metric("S\&P 500 Futures", f"{spy_current:.2f}" if spy_current is not None else "N/A",
            f"{spy_change_percent:.2f}%" if spy_change_percent is not None else "N/A")
col3.metric("Gold Futures", f"{gold_current:.2f}" if gold_current is not None else "N/A",
            f"{gold_change_percent:.2f}%" if gold_change_percent is not None else "N/A")
col4.metric("USD Index Futures", f"{dxy_current:.2f}" if dxy_current is not None else "N/A",
            f"{dxy_change_percent:.2f}%" if dxy_change_percent is not None else "N/A")

# --- Section 2: Implied Rates Change (Data availability is limited) ---
st.header("Implied Rates Change (Limited Data)")
st.info("Reliable day-over-day implied rates change data is not consistently available through common free APIs. This section may require integration with specialized financial data providers.")
# You would ideally fetch this from a source like CME FedWatch Tool's historical data if accessible via API.
# For now, we'll provide a placeholder.
implied_rate_change = None  # Replace with actual data fetching if possible
implied_rate_change_prev = None

col_implied = st.columns(1)
col_implied[0].metric("Implied Rate Change (vs Prev Day)",
                      f"{implied_rate_change:.2f}%" if implied_rate_change is not None else "N/A",
                      f"{implied_rate_change - implied_rate_change_prev:.2f}%" if implied_rate_change is not None and implied_rate_change_prev is not None else "N/A")

# --- Section 3: Fed Funds Rate and Real Interest Rates ---
st.header("Fed Funds Rate and Real Interest Rates")
eff_fed_funds_current, eff_fed_funds_prev, eff_fed_funds_change = fetch_fred_data("EFFR")

# Inflation data is needed for real interest rates - using a placeholder
inflation_rate_current = None
inflation_rate_prev = None

real_rate_current = eff_fed_funds_current - inflation_rate_current if eff_fed_funds_current is not None and inflation_rate_current is not None else None
real_rate_prev = eff_fed_funds_prev - inflation_rate_prev if eff_fed_funds_prev is not None and inflation_rate_prev is not None else None
real_rate_change = real_rate_current - real_rate_prev if real_rate_current is not None and real_rate_prev is not None else None

col_ffr = st.columns(3)
col_ffr[0].metric("Effective Fed Funds Rate", f"{eff_fed_funds_current:.2f}%" if eff_fed_funds_current is not None else "N/A",
                 f"{eff_fed_funds_change:.2f}%" if eff_fed_funds_change is not None else "N/A")
col_ffr[1].metric("Real Interest Rate (Est.)", f"{real_rate_current:.2f}%" if real_rate_current is not None else "N/A",
                 f"{real_rate_change:.2f}%" if real_rate_change is not None else "N/A")

# --- Section 4: Treasury Yield Spreads ---
st.header("Treasury Yield Spreads")
current_yields, previous_yields = fetch_treasury_yields()

if current_yields is not None and previous_yields is not None:
    spread_2y5y_current = calculate_yield_spread(current_yields['T5Y'], current_yields['T2Y'])
    spread_2y10y_current = calculate_yield_spread(current_yields['T10Y'], current_yields['T2Y'])
    spread_2y5y_prev = calculate_yield_spread(previous_yields['T5Y'], previous_yields['T2Y'])
    spread_2y10y_prev = calculate_yield_spread(previous_yields['T10Y'], previous_yields['T2Y'])

    change_2y5y = spread_2y5y_current - spread_2y5y_prev if spread_2y5y_current is not None and spread_2y5y_prev is not None else None
    change_2y10y = spread_2y10y_current - spread_2y10y_prev if spread_2y10y_current is not None and spread_2y10y_prev is not None else None

    col_spreads = st.columns(2)
    col_spreads[0].metric("2yr vs 5yr Spread", f"{spread_2y5y_current:.2f}%" if spread_2y5y_current is not None else "N/A",
                         f"{change_2y5y:.2f}%" if change_2y5y is not None else "N/A")
    col_spreads[1].metric("2yr vs 10yr Spread", f"{spread_2y10y_current:.2f}%" if spread_2y10y_current is not None else "N/A",
                         f"{change_2y10y:.2f}%" if change_2y10y is not None else "N/A")

    # Risk On/Off based on yield spread changes
    spread_risk_sentiment = determine_risk_sentiment(vix_change_percent, change_2y10y)
    st.subheader(f"Risk Sentiment (Based on VIX & 2yr-10yr Spread): {spread_risk_sentiment}")

    # Bullish/Bearish for Gold, Bonds, Indexes
    st.subheader("Bullish/Bearish Signals")
    col_bb = st.columns(3)
    col_bb[0].metric("Gold", determine_bullish_bearish(gold_change_percent))
    col_bb[1].metric("Bonds (10yr Yield Change)", determine_bullish_bearish(- (current_yields['T10Y'] - previous_yields['T10Y']) * 100 if current_yields is not None and previous_yields is not None else None)) # Inverse relationship
    col_bb[2].metric("Indexes (SPY Futures)", determine_bullish_bearish(spy_change_percent))

    # --- Section 5: Entire Treasury Yield Term Structure Spread ---
    st.subheader("Treasury Yield Term Structure")
    if current_yields is not None and previous_yields is not None:
        yield_data = pd.DataFrame({
            "Maturity": ["2Y", "5Y", "10Y"],
            "Current": [current_yields['T2Y'], current_yields['T5Y'], current_yields['T10Y']],
            "Previous": [previous_yields['T2Y'], previous_yields['T5Y'], previous_yields['T10Y']]
        })
        yield_data['Change'] = yield_data['Current'] - yield_data['Previous']
        st.dataframe(yield_data)

        # Simple interpretation of yield curve change for SPY
        yield_curve_change_sentiment = "Neutral"
        if yield_data['Change'].mean() > 0.01:
            yield_curve_change_sentiment = "Potentially Bearish for SPY"
        elif yield_data['Change'].mean() < -0.01:
            yield_curve_change_sentiment = "Potentially Bullish for SPY"
        st.info(f"Yield Curve Shift Sentiment for SPY: {yield_curve_change_sentiment}")

        # ... (Further analysis of yield curve shape and changes can be added)
    else:
        st.warning("Could not fetch Treasury yield curve data.")

# --- Section 6: VIX Analysis ---
st.header("VIX Analysis")
col_vix_analysis = st.columns(2)

# VIX Term Structure (Requires more complex data fetching - using placeholder)
vix_term_structure_data = {
    "1 MTH": None,
    "3 MTH": None,
    "6 MTH": None
}
col_vix_analysis[0].subheader("VIX Term Structure (Illustrative)")
st.dataframe(pd.DataFrame.from_dict(vix_term_structure_data, orient='index', columns=['Price']))
st.info("Real-time VIX term structure data often requires specialized APIs.")

col_vix_analysis[1].subheader("VIX Price Levels")
st.metric("VIX Index", f"{vix_current:.2f}" if vix_current is not None else "N/A",
            f"{vix_change:.2f}" if vix_change is not None else "N/A")

# VIX Premium (Requires Realized Volatility)
st.subheader("VIX Premium (IV/RV) - Requires Realized Volatility Data")
st.info("Calculating VIX premium requires Realized Volatility (RV) data, which needs additional calculations based on historical S\&P 500 prices.")

# VIX Skew (Requires Options Chain Data)
st.subheader("VIX Skew - Requires Options Chain Data")
st.info("Analyzing VIX skew requires access to options chain data, which is not available through basic APIs.")

# --- Section 7: Gold vs Bonds - Big Money Flow (Risk Off Scenario) ---
st.header("Gold vs Bonds - Big Money Flow (Risk Off Scenario)")
st.info("This is a simplified gauge based on general risk-off behavior. Actual 'big money' flow is complex to track directly.")

risk_off_scenario = (spread_risk_sentiment == "Risk Off" or (vix_change_percent is not None and vix_change_percent > 1))

if risk_off_scenario:
    st.markdown("### Potential Big Money Flow (Risk Off Day)")
    gold_attractiveness = 0
    bond_attractiveness = 0

    # Simple logic based on price changes in a hypothetical risk-off
    if gold_change_percent is not None and gold_change_percent > 0:
        gold_attractiveness += 1
    if current_yields is not None and previous_yields is not None and current_yields['T10Y'] < previous_yields['T10Y']: # Yields down, price up
        bond_attractiveness += 1

    if gold_attractiveness > bond_attractiveness:
        st.success("Gauge: Big money potentially more likely to flow into Gold.")
    elif bond_attractiveness > gold_attractiveness:
        st.success("Gauge: Big money potentially more likely to flow into Bonds.")
    else:
        st.info("Gauge: Indeterminate - both Gold and Bonds may see inflows.")
else:
    st.info("This gauge is most relevant in a 'Risk Off' scenario.")

# --- Final Notes ---
st.sidebar.info("Data is updated periodically based on caching settings. Real-time data may require specialized subscriptions.")
st.sidebar.warning("Risk sentiment and bullish/bearish indicators are based on simplified logic and should not be considered definitive trading advice.")