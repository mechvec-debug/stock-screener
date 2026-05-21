# =========================================
# FILE: screener_1.py
# =========================================

import streamlit as st
import pandas as pd
import ta
import time
import gspread
import yfinance as yf
import datetime
import pytz
from gspread_dataframe import set_with_dataframe

from utils.cache_fetcher import (
    get_cached_ohlc,
    get_fundamental_cache
)


# =========================================
# SMART DAILY CACHE KEY
# =========================
def get_market_rollover_key():
    """Changes the cache key only at 4:00 PM IST daily."""
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(ist)
    shifted_time = now - datetime.timedelta(hours=16)
    return shifted_time.strftime('%Y-%m-%d')


# =========================================
# GOOGLE SHEETS READ/WRITE FUNCTIONS
# =========================================
def get_tickers_from_sheet():
    try:
        gc = gspread.service_account(filename="data/google_credentials.json")
        sh = gc.open("Stock_List")
        worksheet = sh.worksheet("Fundamentals")
        tickers = worksheet.col_values(1)[1:]
        return [t.strip() for t in tickers if t.strip()]
    except Exception as e:
        print(f"❌ Failed to read Google Sheet: {e}")
        return []


def update_google_sheet(dataframe):
    try:
        gc = gspread.service_account(filename="data/google_credentials.json")
        sh = gc.open("Stock_List")
        worksheet = sh.worksheet("Fundamentals")
        worksheet.batch_clear(["A2:M1000"])
        set_with_dataframe(worksheet, dataframe, row=2, col=1, include_column_header=False)
        return True
    except Exception as e:
        print(f"❌ Failed to update Google Sheet: {e}")
        return False


# =========================================
# FETCH STOCK DATA
# =========================================
def fetch_stock_data(ticker):
    try:
        print(f"\n===================")
        print(f"Fetching: {ticker}")

        yf_ticker = f"{ticker}.NS"

        # OHLC
        hist = get_cached_ohlc(ticker)
        if hist is None or hist.empty or len(hist) < 100:
            hist = get_cached_ohlc(yf_ticker)

        if hist is None or hist.empty or len(hist) < 100:
            print(f"⚠️ Cache missing. Fetching live OHLC for {yf_ticker}...")
            stock = yf.Ticker(yf_ticker)
            hist = stock.history(period="1y")

        if hist is None or hist.empty or len(hist) < 100:
            return None

        # Fundamentals
        fund_df = get_fundamental_cache()
        base_ticker = ticker.replace(".NS", "")
        stock_row = pd.DataFrame()

        if fund_df is not None and not fund_df.empty:
            stock_row = fund_df[fund_df["Ticker"].isin([ticker, base_ticker, yf_ticker])]

        if stock_row.empty:
            print(f"⚠️ Cache missing. Fetching live Fundamentals for {yf_ticker}...")
            raw_info = yf.Ticker(yf_ticker).info
            info = {
                "Market Cap": raw_info.get("marketCap", 0),
                "Trailing PE": raw_info.get("trailingPE", 0),
                "ROE": raw_info.get("returnOnEquity", 0) * 100 if raw_info.get("returnOnEquity") else 0,
                "ROCE": 0,
                "OPM": raw_info.get("operatingMargins", 0) * 100 if raw_info.get("operatingMargins") else 0,
                "Sales Growth": raw_info.get("revenueGrowth", 0) * 100 if raw_info.get("revenueGrowth") else 0,
                "Debt/Equity": raw_info.get("debtToEquity", 0) / 100 if raw_info.get("debtToEquity") else 0,
                "Trailing EPS": raw_info.get("trailingEps", 0),
                "Sector": raw_info.get("sector", "N/A"),
                "Industry": raw_info.get("industry", "N/A")
            }
        else:
            info = stock_row.iloc[0].to_dict()

        # Indicators
        hist["RSI"] = ta.momentum.RSIIndicator(close=hist["Close"], window=14).rsi()
        hist["RSI_Slope"] = hist["RSI"].diff()
        hist["AvgVolume"] = hist["Volume"].rolling(20).mean()
        hist["VolumeRatio"] = hist["Volume"] / hist["AvgVolume"]

        print(f"✅ Data Ready: {ticker}")
        return {"ticker": ticker, "hist": hist, "info": info}

    except Exception as e:
        print(f"❌ Fetch Error {ticker}: {e}")
        return None


# =========================================
# FILTERS & STATUS ENGINE
# =========================================
def fundamentals_pass(info):
    try:
        market_cap = float(info.get("Market Cap", 0))
        sales_growth = float(info.get("Sales Growth", 0))
        opm = float(info.get("OPM", 0))
        roe = float(info.get("ROE", 0))
        debt_to_equity = float(info.get("Debt/Equity", 999))

        return all([market_cap > 1000, sales_growth > 5, opm > 10, roe > 10, debt_to_equity < 1.5])
    except:
        return False


def get_status(data):
    try:
        hist = data["hist"]
        info = data["info"]
        latest = hist.iloc[-1]

        current_price = latest["Close"]
        all_time_high = hist["High"].max()
        price_ratio = current_price / all_time_high

        fundamentals_ok = fundamentals_pass(info)
        vol_buildup = latest["VolumeRatio"] > 1.1
        rsi_increasing = latest["RSI_Slope"] > 0

        if fundamentals_ok:
            if 0.75 <= price_ratio <= 0.95:
                status = "🚀 STRONG BUY" if (vol_buildup and rsi_increasing) else "🔥 PASS"
            elif 0.65 <= price_ratio < 0.75:
                status = "👀 WATCH"
            else:
                status = "WAIT (Price)"
        else:
            status = "WAIT (Fund)"

        return {
            "Ticker": data["ticker"],
            "Market Cap": info.get("Market Cap", ""),
            "Current Price": round(current_price, 2),
            "PE": round(info.get("Trailing PE", 0), 2) if info.get("Trailing PE") else "",
            "ROE": round(info.get("ROE", 0), 2) if info.get("ROE") else "",
            "ROCE": info.get("ROCE", ""),
            "OPM": round(info.get("OPM", 0), 2) if info.get("OPM") else "",
            "Sales Growth": round(info.get("Sales Growth", 0), 2) if info.get("Sales Growth") else "",
            "Debt/Equity": round(info.get("Debt/Equity", 0), 2) if info.get("Debt/Equity") else "",
            "EPS": round(info.get("Trailing EPS", 0), 2) if info.get("Trailing EPS") else "",
            "Sector": info.get("Sector", "N/A"),
            "Industry": info.get("Industry", "N/A"),
            "Notes": status
        }
    except Exception as e:
        return {
            "Ticker": data["ticker"], "Market Cap": "", "Current Price": "", "PE": "",
            "ROE": "", "ROCE": "", "OPM": "", "Sales Growth": "", "Debt/Equity": "",
            "EPS": "", "Sector": "ERROR", "Industry": "ERROR", "Notes": "ERROR"
        }


# =========================================
# MAIN SCREENER (USING DAILY KEY INSTEAD OF TTL)
# =========================================
@st.cache_data(show_spinner=False)
def run_screener(cache_key):
    results = []
    tickers = get_tickers_from_sheet()

    if not tickers:
        return pd.DataFrame()

    for ticker in tickers:
        data = fetch_stock_data(ticker)
        if data:
            result = get_status(data)
        else:
            result = {
                "Ticker": ticker, "Market Cap": "", "Current Price": "", "PE": "",
                "ROE": "", "ROCE": "", "OPM": "", "Sales Growth": "", "Debt/Equity": "",
                "EPS": "", "Sector": "-", "Industry": "-", "Notes": "FETCH FAILED"
            }
        results.append(result)
        time.sleep(1)

    return pd.DataFrame(results)


# =========================================
# STREAMLIT DASHBOARD
# =========================================
st.title("📊 Screener 1 - Fundamental Scanner")

# Generate the daily key and run the screener
current_market_key = get_market_rollover_key()
st.write(f"Data locked for trading day: {current_market_key}")

with st.spinner("Scanning stocks from Google Sheets..."):
    results_df = run_screener(current_market_key)

if results_df.empty:
    st.warning("No stocks found. Check your Google Sheet connection.")
else:
    if "sheet_updated" not in st.session_state:
        with st.spinner("Pushing results to Google Sheets..."):
            success = update_google_sheet(results_df)
            if success:
                st.session_state.sheet_updated = True
                st.success("✅ Google Sheet Auto-Updated Successfully!")
            else:
                st.error("❌ Failed to update Google Sheet.")
    else:
        st.success("✅ Google Sheet is up to date.")

    if st.button("🔄 Force Refresh Sheets"):
        update_google_sheet(results_df)
        st.toast("Sheets Refreshed!")

    st.divider()

    execution_ready = results_df[results_df["Notes"] == "🚀 STRONG BUY"]
    early_warning = results_df[results_df["Notes"] == "👀 WATCH"]
    fundamentals_pass = results_df[results_df["Notes"] == "🔥 PASS"]
    no_quality = results_df[results_df["Notes"].isin(["WAIT (Fund)", "WAIT (Price)", "FETCH FAILED", "ERROR"])]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🚀 Execution Ready", len(execution_ready))
    col2.metric("👀 Early Warning", len(early_warning))
    col3.metric("🔥 Fundamentals Pass", len(fundamentals_pass))
    col4.metric("❌ No Quality", len(no_quality))

    st.divider()

    st.subheader("🚀 Execution Ready")
    st.dataframe(execution_ready, width="stretch")

    st.subheader("👀 Early Warning")
    st.dataframe(early_warning, width="stretch")

    st.subheader("🔥 Fundamentals Pass")
    st.dataframe(fundamentals_pass, width="stretch")

    st.subheader("❌ No Quality / Failed")
    st.dataframe(no_quality, width="stretch")