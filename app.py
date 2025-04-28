import pandas as pd
import yfinance as yf
import requests
import plotly.graph_objs as go
import streamlit as st
from datetime import datetime, timedelta

# API Key for FRED
API_KEY = 'f693521d3101f329c121220251a424b3'
FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"

# Function to fetch FRED data
def fetch_fred_data(series_id, start_date, end_date):
    try:
        params = {
            'api_key': API_KEY,
            'series_id': series_id,
            'start_date': start_date,
            'end_date': end_date,
            'file_type': 'json'
        }
        response = requests.get(FRED_API_URL, params=params)
        data = response.json()
        if 'observations' in data:
            df = pd.DataFrame(data['observations'])
            df['date'] = pd.to_datetime(df['date'])
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            return df[['date', 'value']]
        else:
            raise Exception(f"Error fetching FRED data for {series_id}")
    except Exception as e:
        print(f"Error fetching FRED data for {series_id}: {e}")
        return None

# Fetch treasury yields from FRED (DGS2, DGS5, DGS30)
def fetch_treasury_yields():
    start_date = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')
    end_date = datetime.today().strftime('%Y-%m-%d')

    # Fetch data for 2-year, 5-year, and 30-year treasury yields
    dgs2 = fetch_fred_data('DGS2', start_date, end_date)
    dgs5 = fetch_fred_data('DGS5', start_date, end_date)
    dgs30 = fetch_fred_data('DGS30', start_date, end_date)

    return dgs2, dgs5, dgs30

# Fetch Fed Funds data (effective rate and implied rate)
def fetch_fed_funds():
    start_date = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')
    end_date = datetime.today().strftime('%Y-%m-%d')

    # Fetch data for the effective Fed Funds rate (DFF)
    dff = fetch_fred_data('DFF', start_date, end_date)
    # Fetch data for implied Fed Funds rate (from futures)
    dff_implied = fetch_fred_data('DFF_IMPLIED', start_date, end_date)

    return dff, dff_implied

# Fetch VIX data (volatility index)
def fetch_vix_data():
    try:
        vix = yf.download('^VIX', period='5d', interval='1d')
        vix['Implied_Volatility'] = vix['Close'] / vix['Close'].shift(1) - 1
        return vix
    except Exception as e:
        print(f"Error fetching VIX data: {e}")
        return None

# Calculate the implied open, discount, and premium of ES futures
def calculate_es_futures():
    try:
        es_futures = yf.download('ES=F', period='1d', interval='1d')
        es_premarket = es_futures.iloc[-1]['Close']  # Last close as the premarket
        return es_premarket
    except Exception as e:
        print(f"Error fetching ES futures data: {e}")
        return None

# Calculate risk-on or risk-off condition based on treasury yield curve
def calculate_risk_condition(dgs2, dgs5, dgs30):
    if dgs2['value'].iloc[-1] < dgs5['value'].iloc[-1] and dgs5['value'].iloc[-1] < dgs30['value'].iloc[-1]:
        return 'Risk Off'  # Yield curve is steepening
    else:
        return 'Risk On'  # Yield curve is flattening or inverted

# Function to analyze all factors and determine consensus risk-on/risk-off
def analyze_all_factors():
    # Fetch necessary data
    dgs2, dgs5, dgs30 = fetch_treasury_yields()
    dff, dff_implied = fetch_fed_funds()
    vix = fetch_vix_data()
    es_premarket = calculate_es_futures()

    # Calculate risk conditions
    treasury_condition = calculate_risk_condition(dgs2, dgs5, dgs30)

    # Further risk conditions based on Fed Funds rate and VIX data
    fed_condition = 'Risk On' if dff['value'].iloc[-1] > dff_implied['value'].iloc[-1] else 'Risk Off'
    vix_condition = 'Risk On' if vix['Implied_Volatility'].iloc[-1] < 0 else 'Risk Off'  # If implied volatility is decreasing

    # Final consensus risk condition
    total_conditions = {
        'Treasury Yield Curve': treasury_condition,
        'Fed Funds Condition': fed_condition,
        'VIX Condition': vix_condition,
        'Premarket ES Futures': 'Risk On' if es_premarket > 0 else 'Risk Off',
    }

    risk_on_count = sum(1 for condition in total_conditions.values() if condition == 'Risk On')
    risk_off_count = len(total_conditions) - risk_on_count

    consensus = 'Risk On' if risk_on_count > risk_off_count else 'Risk Off'

    return total_conditions, consensus

# Streamlit app display logic
def display_dashboard():
    # Get data and analysis
    total_conditions, consensus = analyze_all_factors()

    # Show dashboard
    st.title("Financial Risk Dashboard")

    # Display consensus
    st.subheader(f"Consensus for the day: {consensus}")

    # Display risk conditions
    for condition, status in total_conditions.items():
        st.write(f"{condition}: {status}")

    # Show more detailed data if needed
    dgs2, dgs5, dgs30 = fetch_treasury_yields()
    st.write("Treasury Yields (2Y, 5Y, 30Y):")
    st.write(f"2Y Yield: {dgs2['value'].iloc[-1]}")
    st.write(f"5Y Yield: {dgs5['value'].iloc[-1]}")
    st.write(f"30Y Yield: {dgs30['value'].iloc[-1]}")

    st.write("Fed Funds Data:")
    st.write(f"Effective Rate: {dff['value'].iloc[-1]}")
    st.write(f"Implied Rate: {dff_implied['value'].iloc[-1]}")

    st.write("VIX Data:")
    st.write(vix.tail(5))

    st.write("ES Futures Premarket Price:")
    st.write(f"Premarket Price: {calculate_es_futures()}")

# Run the Streamlit app
if __name__ == '__main__':
    display_dashboard()
