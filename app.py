import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf
import plotly.graph_objs as go

# === CONFIG ===
FRED_API_KEY = 'f693521d3101f329c121220251a424b3'
ALPHA_VANTAGE_API_KEY = '31934d0584960301655194d067cc9399'

# === HELPER FUNCTIONS ===

def fetch_fred_series(series_id):
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={FRED_API_KEY}&file_type=json"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data['observations'])
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df['date'] = pd.to_datetime(df['date'])
        return df[['date', 'value']]
    else:
        st.error(f"Error fetching FRED data for {series_id}: {response.text}")
        return pd.DataFrame()

def fetch_yfinance_data(ticker, period='5d', interval='1d'):
    data = yf.download(ticker, period=period, interval=interval, progress=False)
    if not data.empty:
        data.reset_index(inplace=True)
    return data

def calculate_risk_condition(current, previous, direction='up'):
    if direction == 'up':
        return 'Risk On' if current > previous else 'Risk Off'
    else:
        return 'Risk Off' if current > previous else 'Risk On'

def fetch_premarket_price(ticker):
    data = yf.Ticker(ticker)
    premarket_price = data.info.get('preMarketPrice')
    return premarket_price

# === FETCH DATA ===

def get_all_data():
    fred_data = {
        '2Y': fetch_fred_series('DGS2'),
        '5Y': fetch_fred_series('DGS5'),
        '30Y': fetch_fred_series('DGS30'),
        'FEDFUNDS': fetch_fred_series('FEDFUNDS')
    }

    market_data = {
        'SPY': fetch_yfinance_data('SPY'),
        'VIX': fetch_yfinance_data('^VIX'),
        'DXY': fetch_yfinance_data('DX-Y.NYB'),
        'ES=F': fetch_yfinance_data('ES=F'),
        'GC=F': fetch_yfinance_data('GC=F')
    }

    premarket_prices = {
        'SPY': fetch_premarket_price('SPY'),
        'ES': fetch_premarket_price('ES=F'),
        'DXY': fetch_premarket_price('DX-Y.NYB'),
        'Gold': fetch_premarket_price('GC=F')
    }

    return fred_data, market_data, premarket_prices

# === ANALYSIS FUNCTIONS ===

def analyze_risk_conditions(fred_data, market_data, premarket_prices):
    risk_factors = {}

    # Yield Curve
    try:
        spread_2s30s = fred_data['30Y']['value'].iloc[-1] - fred_data['2Y']['value'].iloc[-1]
        risk_factors['Yield Curve 2s30s'] = 'Risk On' if spread_2s30s > 0 else 'Risk Off'
    except:
        risk_factors['Yield Curve 2s30s'] = 'Data Error'

    # Fed Funds Rate (Real & Implied)
    try:
        real_rate = fred_data['FEDFUNDS']['value'].iloc[-1]
        implied_rate = fred_data['2Y']['value'].iloc[-1]
        risk_factors['Fed Funds Spread'] = calculate_risk_condition(implied_rate, real_rate, 'up')
    except:
        risk_factors['Fed Funds Spread'] = 'Data Error'

    # SPY Premarket
    try:
        yesterday_close = market_data['SPY']['Close'].iloc[-2]
        premarket_spy = premarket_prices['SPY']
        risk_factors['SPY Premarket'] = calculate_risk_condition(premarket_spy, yesterday_close, 'up')
    except:
        risk_factors['SPY Premarket'] = 'Data Error'

    # VIX Movement
    try:
        yesterday_vix = market_data['VIX']['Close'].iloc[-2]
        today_vix = market_data['VIX']['Close'].iloc[-1]
        risk_factors['VIX Movement'] = calculate_risk_condition(yesterday_vix, today_vix, 'down')
    except:
        risk_factors['VIX Movement'] = 'Data Error'

    # DXY Premarket
    try:
        yesterday_dxy = market_data['DXY']['Close'].iloc[-2]
        premarket_dxy = premarket_prices['DXY']
        risk_factors['DXY Premarket'] = calculate_risk_condition(premarket_dxy, yesterday_dxy, 'up')
    except:
        risk_factors['DXY Premarket'] = 'Data Error'

    # Gold Futures
    try:
        yesterday_gold = market_data['GC=F']['Close'].iloc[-2]
        premarket_gold = premarket_prices['Gold']
        risk_factors['Gold Premarket'] = calculate_risk_condition(premarket_gold, yesterday_gold, 'up')
    except:
        risk_factors['Gold Premarket'] = 'Data Error'

    # ES Futures
    try:
        yesterday_es = market_data['ES=F']['Close'].iloc[-2]
        premarket_es = premarket_prices['ES']
        risk_factors['ES Premarket'] = calculate_risk_condition(premarket_es, yesterday_es, 'up')
    except:
        risk_factors['ES Premarket'] = 'Data Error'

    # Consensus Calculation
    risk_on_count = sum(1 for v in risk_factors.values() if v == 'Risk On')
    risk_off_count = sum(1 for v in risk_factors.values() if v == 'Risk Off')

    consensus = 'RISK ON' if risk_on_count > risk_off_count else 'RISK OFF'

    return risk_factors, consensus

# === STREAMLIT FRONTEND ===

def display_dashboard():
    st.title('Financial Risk Dashboard')
    st.subheader('Live Analysis of Market Risk Conditions')

    fred_data, market_data, premarket_prices = get_all_data()
    risk_factors, consensus = analyze_risk_conditions(fred_data, market_data, premarket_prices)

    st.header(f"Today's Consensus: {consensus}")

    st.subheader('Risk Factor Breakdown:')
    for factor, status in risk_factors.items():
        st.write(f"{factor}: {status}")

    st.subheader('Selected Charts')

    if not market_data['SPY'].empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=market_data['SPY']['Date'], y=market_data['SPY']['Close'], mode='lines', name='SPY Close'))
        fig.update_layout(title='SPY Price', xaxis_title='Date', yaxis_title='Price')
        st.plotly_chart(fig)

    if not market_data['VIX'].empty:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=market_data['VIX']['Date'], y=market_data['VIX']['Close'], mode='lines', name='VIX Close'))
        fig2.update_layout(title='VIX Index', xaxis_title='Date', yaxis_title='VIX')
        st.plotly_chart(fig2)

# === MAIN ===
if __name__ == '__main__':
    display_dashboard()