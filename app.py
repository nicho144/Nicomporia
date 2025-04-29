import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
from fredapi import Fred
import plotly.graph_objects as go

# --- FRED API Setup ---
FRED_API_KEY = "f693521d3101f329c121220251a424b3"  # <<<<<<<<<<< PLACE YOUR KEY
fred = Fred(api_key=FRED_API_KEY)

# --- Fetching Functions ---

def fetch_yield_curve():
    today = datetime.datetime.today()
    two_year = fred.get_series('GS2', today - datetime.timedelta(days=7), today).dropna().iloc[-1]
    five_year = fred.get_series('GS5', today - datetime.timedelta(days=7), today).dropna().iloc[-1]
    ten_year = fred.get_series('GS10', today - datetime.timedelta(days=7), today).dropna().iloc[-1]
    thirty_year = fred.get_series('GS30', today - datetime.timedelta(days=7), today).dropna().iloc[-1]
    
    data = {
        '2Y': two_year,
        '5Y': five_year,
        '10Y': ten_year,
        '30Y': thirty_year
    }
    return data

def fetch_yield_spreads(yield_data):
    spread_2s5s = yield_data['2Y'] - yield_data['5Y']
    spread_2s10s = yield_data['2Y'] - yield_data['10Y']
    spread_2s30s = yield_data['2Y'] - yield_data['30Y']
    return spread_2s5s, spread_2s10s, spread_2s30s

def fetch_fed_funds_expectation():
    try:
        zq = yf.download('ZQ=F', period="5d", interval="1d")
        implied_rate = 100 - zq['Adj Close'].iloc[-1]
        return implied_rate
    except:
        return None

def fetch_inflation_expectation():
    today = datetime.datetime.today()
    try:
        inflation = fred.get_series('T5YIE', today - datetime.timedelta(days=7), today).dropna().iloc[-1]
        return inflation
    except:
        return None

def fetch_vix_data():
    vix = fetch_price('^VIX')
    vix9d = fetch_price('^VIX9D')
    vix3m = fetch_price('^VIX3M')
    return vix, vix9d, vix3m

def fetch_skew_index():
    return fetch_price('^SKEW')

def fetch_price(ticker):
    try:
        df = yf.download(ticker, period='5d', interval='1d')
        return df['Adj Close'].iloc[-1]
    except:
        return None

def fetch_iv_rv():
    vix = fetch_price('^VIX')
    spx = yf.download('^GSPC', period="30d", interval="1d")
    if not spx.empty:
        returns = spx['Adj Close'].pct_change().dropna()
        realized_vol = returns.std() * (252 ** 0.5) * 100
        return vix, realized_vol
    else:
        return None, None

def fetch_futures_implied_open():
    es = fetch_price('ES=F')
    spx = fetch_price('^GSPC')
    if es and spx:
        return es - spx
    return None

def calculate_atm_straddle_range():
    spx = yf.Ticker('^GSPC')
    today_price = spx.history(period='1d')['Close'].iloc[-1]
    options = spx.option_chain(spx.options[0])
    calls = options.calls
    if not calls.empty:
        atm = calls.iloc[(calls['strike']-today_price).abs().argsort()[:1]]
        iv = atm['impliedVolatility'].values[0]
        expected_move = today_price * iv * (1/12)**0.5  # 1 month expiry assumed
        return expected_move
    return None

# --- Plotting Functions ---

def plot_yield_curve(yield_data):
    fig = go.Figure()
    tenors = ['2Y', '5Y', '10Y', '30Y']
    yields = [yield_data[t] for t in tenors]
    fig.add_trace(go.Scatter(x=tenors, y=yields, mode='lines+markers', name='Yield Curve'))
    fig.update_layout(title="Treasury Yield Curve", xaxis_title="Maturity", yaxis_title="Yield (%)")
    return fig

def plot_vix_curve(vix_spot, vix9d, vix3m):
    fig = go.Figure()
    tenors = ['9D', 'Spot', '3M']
    values = [vix9d, vix_spot, vix3m]
    fig.add_trace(go.Scatter(x=tenors, y=values, mode='lines+markers', name='VIX Term Structure'))
    fig.update_layout(title="VIX Term Structure", xaxis_title="Maturity", yaxis_title="Volatility (%)")
    return fig

# --- Streamlit App ---

def main():
    st.title("🌐 Full Macro and Volatility Dashboard")

    with st.spinner('Fetching data...'):

        # Fetch all
        yield_data = fetch_yield_curve()
        spread_2s5s, spread_2s10s, spread_2s30s = fetch_yield_spreads(yield_data)
        fed_funds = fetch_fed_funds_expectation()
        inflation = fetch_inflation_expectation()
        vix_spot, vix9d, vix3m = fetch_vix_data()
        skew = fetch_skew_index()
        implied_vol, realized_vol = fetch_iv_rv()
        implied_open = fetch_futures_implied_open()
        straddle_range = calculate_atm_straddle_range()

    # Display Results

    st.header("1. 📈 Yield Curve")
    st.plotly_chart(plot_yield_curve(yield_data))
    st.write(f"2s5s Spread: {spread_2s5s:.2f} bp")
    st.write(f"2s10s Spread: {spread_2s10s:.2f} bp")
    st.write(f"2s30s Spread: {spread_2s30s:.2f} bp")

    st.header("2. 🏦 Fed & Inflation Expectations")
    st.write(f"Implied Fed Funds Rate: {fed_funds:.2f}%")
    st.write(f"5-Year Inflation Expectation: {inflation:.2f}%")

    st.header("3. ⚡ VIX Term Structure")
    st.plotly_chart(plot_vix_curve(vix_spot, vix9d, vix3m))
    if vix_spot and vix3m:
        if vix_spot < vix3m:
            st.success("VIX Curve is in **Contango** → Risk On")
        else:
            st.error("VIX Curve is in **Backwardation** → Risk Off")

    st.header("4. 🎯 Volatility Measures")
    st.write(f"Implied Volatility (VIX): {implied_vol:.2f}%")
    st.write(f"Realized Volatility (30D SPX): {realized_vol:.2f}%")
    if implied_vol and realized_vol:
        st.write(f"Volatility Risk Premium (IV - RV): {implied_vol - realized_vol:.2f}")

    st.header("5. 📊 SKEW Index")
    st.write(f"SKEW Index: {skew:.2f}")

    st.header("6. 🕗 Implied Futures Open (Fair Value)")
    st.write(f"Implied Open (ES vs SPX): {implied_open:.2f}")

    st.header("7. 🎲 ATM Straddle Expected Move")
    st.write(f"1-day Expected Move from ATM SPX Straddle: ±{straddle_range:.2f}")

    st.success('✅ Dashboard Loaded!')

# Run
if __name__ == "__main__":
    main()
