import streamlit as st
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
import numpy as np
import logging

# Constants
FRED_API_KEY = 'f693521d3101f329c121220251a424b3'
FRED_API_URL = 'https://api.stlouisfed.org/fred/series/observations'
RETRY_COUNT = 3
TIMEOUT = 10
FALLBACK_DATA_PATH = "fallback_data.json"

# External data sources
EXTERNAL_SOURCES = {
    "vix": "https://api.polygon.io/v2/aggs/ticker/VIX/prev?adjusted=true&apiKey=YOUR_POLYGON_KEY",
    "gold": "https://www.goldapi.io/api/XAU/USD",
    "dxy": "https://api.exchangerate.host/latest?base=USD",
    "es_futures": "https://finnhub.io/api/v1/quote?symbol=ES=F&token=YOUR_FINNHUB_KEY"
}

# Logging
logging.basicConfig(level=logging.INFO)

async def fetch_data(url, params=None, retries=RETRY_COUNT, timeout=TIMEOUT):
    attempt = 0
    while attempt < retries:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=timeout) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logging.error(f"API error: {response.status} - {await response.text()}")
                        return {"error": f"API returned status code {response.status}"}
        except asyncio.TimeoutError:
            logging.warning("Timeout Error. Retrying...")
            attempt += 1
        except aiohttp.ClientError as e:
            logging.error(f"API Request Error: {str(e)}")
            return {"error": f"API Request Error: {str(e)}"}
    return {"error": "Max retries reached, data fetch failed."}

def load_fallback_data():
    try:
        with open(FALLBACK_DATA_PATH, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {"error": "Fallback data file not found."}

async def fetch_fred_yield_data():
    params = {
        'series_id': 'GS10',
        'api_key': FRED_API_KEY,
        'file_type': 'json'
    }
    return await fetch_data(FRED_API_URL, params)

async def fetch_fred_inflation_data():
    params = {
        'series_id': 'CPIAUCNS',
        'api_key': FRED_API_KEY,
        'file_type': 'json'
    }
    return await fetch_data(FRED_API_URL, params)

async def fetch_external_sources():
    tasks = [fetch_data(url) for url in EXTERNAL_SOURCES.values()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return dict(zip(EXTERNAL_SOURCES.keys(), results))

def calculate_yield_curve_steepening(flat_2_10, yield_2y, yield_10y):
    spread = yield_10y - yield_2y
    if spread > flat_2_10:
        return "Steepening", spread
    elif spread < flat_2_10:
        return "Flattening", spread
    else:
        return "Neutral", spread

def calculate_iv_rv(spy_iv, spy_rv):
    if spy_iv > spy_rv:
        return "Implied Volatility above Realized (Selling Volatility)", spy_iv - spy_rv
    elif spy_iv < spy_rv:
        return "Realized Volatility above Implied (Buying Volatility)", spy_rv - spy_iv
    else:
        return "Neutral Volatility", 0

async def main():
    st.title("Enhanced Financial Dashboard")
    tasks = [
        fetch_fred_yield_data(),
        fetch_fred_inflation_data(),
        fetch_external_sources()
    ]
    results = await asyncio.gather(*tasks)
    yield_data, inflation_data, external_data = results

    if "error" in yield_data or "error" in inflation_data:
        st.warning(f"Error fetching data: {yield_data.get('error', '')} | {inflation_data.get('error', '')}")
        fallback = load_fallback_data()
        st.json(fallback)
    else:
        try:
            yield_2y = float(yield_data['observations'][0]['value'])
            yield_10y = float(yield_data['observations'][1]['value'])
            cpi_data = inflation_data['observations']
            inflation_rate = float(cpi_data[-1]['value'])
        except (KeyError, IndexError, ValueError) as e:
            st.warning(f"Error parsing yield or inflation data: {str(e)}")
            return

        real_interest_rate = yield_10y - inflation_rate
        flat_2_10 = 0.25
        curve_status, curve_spread = calculate_yield_curve_steepening(flat_2_10, yield_2y, yield_10y)

        st.write(f"Real Interest Rate (10-year Yield - Inflation): {real_interest_rate:.2f}%")
        st.write(f"Curve Status: {curve_status} (Spread: {curve_spread:.2f})")

        if curve_status == "Steepening":
            st.write("Risk-On: Positive sentiment in the market")
        elif curve_status == "Flattening":
            st.write("Risk-Off: Negative sentiment in the market")
        else:
            st.write("Neutral: Market sentiment is stable")

        spy_iv, spy_rv = 15, 12
        volatility_status, volatility_spread = calculate_iv_rv(spy_iv, spy_rv)
        st.write(f"Volatility Status: {volatility_status} (Spread: {volatility_spread:.2f})")

        st.subheader("Additional Market Indicators")
        for key, data in external_data.items():
            if isinstance(data, dict):
                st.write(f"{key.upper()}: {json.dumps(data, indent=2)}")
            else:
                st.write(f"{key.upper()}: Error fetching data")

if __name__ == "__main__":
    st.spinner('Fetching data, please wait...')
    asyncio.run(main())
