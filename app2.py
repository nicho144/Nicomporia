import streamlit as st
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
import numpy as np
import logging
import matplotlib.pyplot as plt
from io import BytesIO

# Constants
FRED_API_KEY = 'f693521d3101f329c121220251a424b3'
FRED_API_URL = 'https://api.stlouisfed.org/fred/series/observations'
RETRY_COUNT = 3
TIMEOUT = 10
FALLBACK_DATA_PATH = "fallback_data.json"

# External data sources (replace with valid API keys)
EXTERNAL_SOURCES = {
    "vix": "https://api.polygon.io/v2/aggs/ticker/VIX/prev?adjusted=true&apiKey=YOUR_POLYGON_KEY",
    "gold": "https://www.goldapi.io/api/XAU/USD?apikey=YOUR_GOLDAPI_KEY",
    "dxy": "https://api.exchangerate.host/latest?base=USD",
    "es_futures": "https://finnhub.io/api/v1/quote?symbol=ES=F&token=YOUR_FINNHUB_KEY",
    "fed_funds_future": "https://api.stlouisfed.org/fred/series/observations?series_id=FF4WK&api_key=f693521d3101f329c121220251a424b3&file_type=json"
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

async def fetch_fred_series(series_id):
    params = {
        'series_id': series_id,
        'api_key': FRED_API_KEY,
        'file_type': 'json'
    }
    return await fetch_data(FRED_API_URL, params)

async def fetch_external_sources():
    tasks = [fetch_data(url) for url in EXTERNAL_SOURCES.values()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return dict(zip(EXTERNAL_SOURCES.keys(), results))

def calculate_steepening_change(today, yesterday):
    diffs = [t - y for t, y in zip(today, yesterday)]
    slope = np.polyfit(range(len(diffs)), diffs, 1)[0]
    return "Steepening" if slope > 0 else "Flattening"

def interpret_market_signals(real_rate, curve_trend, gold_data, vix_data, dxy_data, es_data):
    sentiments = {}

    sentiments['Fed Rate'] = "Bullish" if real_rate < 0 else "Bearish"

    sentiments['Yield Curve'] = "Risk-On" if curve_trend == "Steepening" else "Risk-Off"

    if isinstance(gold_data, dict):
        change = float(gold_data.get("ch", 0))
        sentiments['Gold'] = "Risk-Off" if change > 0 else "Risk-On"

    if isinstance(vix_data, dict):
        vix = float(vix_data.get("results", [{}])[0].get("c", 0))
        sentiments['VIX'] = "Risk-Off" if vix > 17 else "Risk-On"

    if isinstance(dxy_data, dict):
        usd_eur = float(dxy_data.get("rates", {}).get("EUR", 1))
        sentiments['DXY'] = "Risk-Off" if usd_eur < 0.91 else "Risk-On"

    if isinstance(es_data, dict):
        es_change = float(es_data.get("dp", 0))
        sentiments['Equities'] = "Risk-On" if es_change > 0 else "Risk-Off"

    return sentiments

def plot_curve(today, yesterday):
    fig, ax = plt.subplots()
    ax.plot(today, label="Today", marker='o')
    ax.plot(yesterday, label="Yesterday", marker='x')
    ax.set_title("Yield Curve Comparison")
    ax.legend()
    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    return buf

async def main():
    st.title("Enhanced Financial Dashboard")

    with st.spinner('Fetching data, please wait...'):
        tasks = [
            fetch_fred_series('GS2'), fetch_fred_series('GS5'), fetch_fred_series('GS10'),
            fetch_fred_series('CPIAUCNS'), fetch_fred_series('FF4WK'), fetch_external_sources()
        ]
        results = await asyncio.gather(*tasks)
        gs2, gs5, gs10, cpi, fed_futures, external = results

    try:
        yields_today = [float(gs2['observations'][-1]['value']),
                        float(gs5['observations'][-1]['value']),
                        float(gs10['observations'][-1]['value'])]

        yields_yesterday = [float(gs2['observations'][-2]['value']),
                            float(gs5['observations'][-2]['value']),
                            float(gs10['observations'][-2]['value'])]

        inflation = float(cpi['observations'][-1]['value'])
        fed_fut_price = float(fed_futures['observations'][-1]['value'])
        implied_fed_rate = 100 - fed_fut_price
        real_fed_rate = implied_fed_rate - inflation

        st.subheader("Rates & Inflation")
        st.write(f"Implied Fed Funds Rate (Futures): {implied_fed_rate:.2f}%")
        st.write(f"Inflation Rate (CPI): {inflation:.2f}%")
        st.write(f"Real Fed Funds Rate: {real_fed_rate:.2f}%")

        curve_trend = calculate_steepening_change(yields_today, yields_yesterday)
        st.write(f"Yield Curve Status: {curve_trend}")

        buf = plot_curve(yields_today, yields_yesterday)
        st.image(buf)

        sentiments = interpret_market_signals(real_fed_rate, curve_trend,
                                              external.get("gold", {}),
                                              external.get("vix", {}),
                                              external.get("dxy", {}),
                                              external.get("es_futures", {}))

        st.subheader("Market Sentiment Breakdown")
        for key, value in sentiments.items():
            st.write(f"{key}: {value}")

        st.subheader("Overall Market Verdict")
        bullish_signals = list(sentiments.values()).count("Risk-On") + list(sentiments.values()).count("Bullish")
        if bullish_signals >= 4:
            st.success("✅ Overall Sentiment: Risk-On")
        else:
            st.error("❌ Overall Sentiment: Risk-Off")

        st.subheader("Raw External Indicators")
        for key, data in external.items():
            if isinstance(data, dict):
                st.write(f"{key.upper()}: {json.dumps(data, indent=2)}")
            else:
                st.write(f"{key.upper()}: Error fetching data")

    except Exception as e:
        st.warning(f"Data processing failed: {e}")
        fallback = load_fallback_data()
        st.json(fallback)

if __name__ == "__main__":
    asyncio.run(main())
