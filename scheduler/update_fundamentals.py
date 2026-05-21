# =========================================
# FILE: screener_1.py
# =========================================

import streamlit as st
import pandas as pd
import ta
import time
import gspread
from gspread_dataframe import set_with_dataframe

from data.stock_list import NIFTY_50
from utils.cache_fetcher import (
    get_cached_ohlc,
    get_fundamental_cache
)

# =========================================
# GOOGLE SHEETS UPDATE FUNCTION
# =========================================
def update_google_sheet(dataframe):
    try:
        # 1. Authenticate (Make sure credentials.json is in your root folder)
        gc = gspread.service_account(filename="credentials.json")

        # 2. Open the specific Google Sheet and Worksheet
        sh = gc.open("Stock_List")
        worksheet = sh.worksheet("Fundamentals")

        # 3. Clear the existing data to prevent overlap from previous runs
        worksheet.clear()

        # 4. Batch update all data at once
        set_with_dataframe(worksheet, dataframe)
        return True

    except Exception as e:
        print(f"❌ Failed to update Google Sheet: {e}")
        return False

# =========================================
# FETCH STOCK DATA
# =========================================
def fetch_stock_data(ticker):
    try:
        print(f"\nFetching: {ticker}")

        # --- LOAD OHLC CACHE ---
        hist = get_cached_ohlc(ticker)
        if hist.empty or len(hist) < 100:
            print(f"❌ No Cached Data: {ticker}")
            return None

        # --- LOAD FUNDAMENTAL CACHE ---
        fund_df = get_fundamental_cache()
        stock_row = fund_df[fund_df["Ticker"] == ticker]

        if stock_row.empty:
            print(f"❌ No Fundamental Data: {ticker}")
            return None

        info = stock_row.iloc[0].to_dict()

        # --- INDICATORS ---
        hist["RSI"] = ta.momentum.RSIIndicator(
            close=hist["Close"],
            window=14
        ).rsi()

        hist["RSI_Slope"] = hist["RSI"].diff()
        hist["AvgVolume"] = hist["Volume"].rolling(20).mean()
        hist["VolumeRatio"] = hist["Volume"] / hist["AvgVolume"]

        print(f"✅ Cache Loaded: {ticker}")

        return {
            "ticker": ticker,
            "hist": hist,
            "info": info
        }

    except Exception as e:
        print(f"❌ Fetch Error {ticker}: {e}")
        return None

# =========================================
# FUNDAMENTAL FILTERS
# =========================================
def fundamentals_pass(info):
    try:
        market_cap = float(info.get("Market Cap", 0))
        sales_growth = float(info.get("Sales Growth", 0))
        opm = float(info.get("OPM", 0))
        roe = float(info.get("ROE", 0))
        roce = float(info.get("ROCE", 0))
        debt_to_equity = float(info.get("Debt/Equity", 999))

        return all([
            market_cap > 1000,
            sales_growth > 5,
            opm > 10,
            roe > 10,
            roce > 10,
            debt_to_equity < 1.5
        ])
    except Exception as e:
        print(f"Fundamental Error: {e}")
        return False

# =========================================
# STATUS ENGINE
# =========================================
def get_status(data):
    try:
        hist = data["hist"]
        info = data["info"]
        latest = hist.iloc[-1]

        # --- PRICE DATA ---
        current_price = latest["Close"]
        all_time_high = hist["High"].max()
        price_ratio = current_price / all_time_high

        # --- FUNDAMENTALS ---
        fundamentals_ok = fundamentals_pass(info)

        # --- TECHNICAL CONDITIONS ---
        vol_buildup = latest["VolumeRatio"] > 1.1
        rsi_increasing = latest["RSI_Slope"] > 0

        # --- STATUS LOGIC ---
        if fundamentals_ok:
            if 0.75 <= price_ratio <= 0.95:
                if vol_buildup and rsi_increasing:
                    status = "🚀 STRONG BUY"
                else:
                    status = "🔥 PASS"
            elif 0.65 <= price_ratio < 0.75:
                status = "👀 WATCH"
            else:
                status = "WAIT (Price)"
        else:
            status = "WAIT (Fund)"

        # --- DEBUG OUTPUT ---
        print(f"\nTicker: {data['ticker']}\nPrice: {round(current_price, 2)}\nATH: {round(all_time_high, 2)}\nPrice Ratio: {round(price_ratio, 2)}\nFundamentals OK: {fundamentals_ok}\nVolume Buildup: {vol_buildup}\nRSI Increasing: {rsi_increasing}\nSTATUS: {status}\n")

        return {
            "Ticker": data["ticker"],
            "Market Cap": round(info.get("marketCap", 0) / 10000000, 2),
            "Current Price": round(current_price, 2),
            "Status": status
        }

    except Exception as e:
        print(f"❌ Status Error: {e}")
        return {
            "Ticker": data["ticker"],
            "Market Cap": 0,
            "Current Price": 0,
            "Status": "ERROR"
        }

# =========================================
# MAIN SCREENER
# =========================================
@st.cache_data(ttl=900)
def run_screener():
    results = []
    for ticker in NIFTY_50:
        print(f"\n===================")
        print(f"Processing: {ticker}")
        print(f"===================")

        data = fetch_stock_data(ticker)
        if data:
            result = get_status(data)
            results.append(result)
            print(f"✅ Added: {ticker}")
        else:
            print(f"❌ Failed: {ticker}")
        time.sleep(1)

    return pd.DataFrame(results)

# =========================================
# STREAMLIT DASHBOARD
# =========================================
st.title("📊 Screener 1 - Fundamental Scanner")
st.write("Scanning stocks...")

# Run Screener (Uses 15-minute cache)
results_df = run_screener()

if results_df.empty:
    st.warning("No stocks found.")
else:
    # --- GOOGLE SHEETS UPDATE VIA BUTTON ---
    # Placing this behind a button prevents you from exhausting your Google Sheets API quota
    # every time you click a tab or interact with the Streamlit app.
    if st.button("🔄 Push Latest Data to Google Sheets"):
        with st.spinner("Updating Google Sheets..."):
            success = update_google_sheet(results_df)
            if success:
                st.success("✅ Google Sheet updated successfully!")
            else:
                st.error("❌ Failed to update Google Sheet. Check console logs.")

    st.divider()

    # --- CATEGORY FILTERS ---
    execution_ready = results_df[results_df["Status"] == "🚀 STRONG BUY"]
    early_warning = results_df[results_df["Status"] == "👀 WATCH"]
    fundamentals_pass = results_df[results_df["Status"] == "🔥 PASS"]
    no_quality = results_df[results_df["Status"].isin(["WAIT (Fund)", "WAIT (Price)", "ERROR"])]

    # --- TOP METRICS ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🚀 Execution Ready", len(execution_ready))
    col2.metric("👀 Early Warning", len(early_warning))
    col3.metric("🔥 Fundamentals Pass", len(fundamentals_pass))
    col4.metric("❌ No Quality", len(no_quality))

    st.divider()

    # --- DATA TABLES ---
    st.subheader("🚀 Execution Ready")
    st.dataframe(execution_ready, width="stretch")

    st.subheader("👀 Early Warning")
    st.dataframe(early_warning, use_container_width=True)

    st.subheader("🔥 Fundamentals Pass")
    st.dataframe(fundamentals_pass, use_container_width=True)

    st.subheader("❌ No Quality")
    st.dataframe(no_quality, use_container_width=True)