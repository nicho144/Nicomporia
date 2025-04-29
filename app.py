import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from fredapi import Fred
import yfinance as yf
from alpha_vantage.timeseries import TimeSeries
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Load secrets
try:
    FRED_API_KEY = st.secrets["FRED_API_KEY"]
    ALPHA_VANTAGE_API_KEY = st.secrets["ALPHA_VANTAGE_API_KEY"]
except KeyError:
    st.error("API keys not found in secrets. Please provide them below.")
    FRED_API_KEY = st.text_input("FRED API Key", type="password")
    ALPHA_VANTAGE_API_KEY = st.text_input("Alpha Vantage API Key", type="password")

# Initialize APIs
fred = Fred(api_key=FRED_API_KEY)
ts = TimeSeries(key=ALPHA_VANTAGE_API_KEY, output_format='pandas')

# Cache data
@st.cache_data(ttl=3600)
def get_fred_data(series_id, name):
    try:
        data = fred.get_series(series_id)
        return data[-1], data[-2]
    except Exception as e:
        st.error(f"Failed to fetch {name}: {str(e)}")
        return None, None

@st.cache_data(ttl=3600)
def get_yield_curve():
    yields = {}
    tenors = {'DGS2': '2Y', 'DGS5': '5Y', 'DGS10': '10Y'}
    for series, tenor in tenors.items():
        latest, previous = get_fred_data(series, tenor)
        yields[tenor] = {'latest': latest, 'previous': previous}
    return yields

# Sidebar navigation
st.sidebar.title("Risk-On/Risk-Off Dashboard")
section = st.sidebar.radio("Select Section", [
    "Overview", "Fed Funds Rate", "Treasury Yield Curve", "Risk Assessment"
])

# Main app
st.title("Financial Risk Dashboard")
st.write(f"Date: {datetime.now().strftime('%Y-%m-%d')}")

if section == "Overview":
    st.write("Welcome to the Risk-On/Risk-Off Dashboard. Navigate using the sidebar.")

elif section == "Fed Funds Rate":
    with st.spinner("Fetching Fed data..."):
        fed_rate, _ = get_fred_data('FEDFUNDS', 'Fed Funds Rate')
        inflation, _ = get_fred_data('CPIAUCSL', 'CPI')
        real_rate = fed_rate - inflation if fed_rate and inflation else None
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"Implied Fed Funds Rate: {fed_rate:.2f}%" if fed_rate else "N/A")
    with col2:
        st.write(f"Real Rate: {real_rate:.2f}%" if real_rate else "N/A")
    st.write(f"Risk: {'Risk-Off' if real_rate and real_rate > 2 else 'Risk-On'}")

elif section == "Treasury Yield Curve":
    with st.spinner("Fetching yield curve..."):
        yields = get_yield_curve()
        df_yields = pd.DataFrame({
            'Tenor': [t for t in yields.keys()],
            'Yield': [yields[t]['latest'] for t in yields.keys()],
            'Previous': [yields[t]['previous'] for t in yields.keys()]
        })
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_yields['Tenor'], y=df_yields['Yield'], name='Today'))
    fig.add_trace(go.Scatter(x=df_yields['Tenor'], y=df_yields['Previous'], name='Previous'))
    fig.update_layout(title='Yield Curve', xaxis_title='Tenor', yaxis_title='Yield (%)', margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig)

elif section == "Risk Assessment":
    st.write("Calculating overall risk status...")
    # Placeholder for full risk assessment
    st.write("Risk Status: Calculating...")