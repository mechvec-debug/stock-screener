# =========================================
# FILE: screener_1.py (Enhanced & Robust)
# =========================================

import streamlit as st
import pandas as pd
import ta
import time
import gspread
import yfinance as yf
import datetime
import pytz
import numpy as np
import json
from google.oauth2.service_account import Credentials

from utils.cache_fetcher import (
    get_cached_ohlc,
    get_fundamental_cache
)


# =========================================
# SMART DAILY CACHE KEY
# =========================================
def get_market_rollover_key():
    """
    Changes the cache key only at 4:00 PM IST daily.
    """
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(ist)
    shifted_time = now - datetime.timedelta(hours=16)
    return shifted_time.strftime('%Y-%m-%d')


# =========================================
# GOOGLE SHEETS READ/WRITE FUNCTIONS
# =========================================
def get_google_client():
    """
    Smart auth:
    - Safely tries Streamlit Secrets on cloud
    - Falls back to local JSON file on desktop
    """
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

    # Safely check for Streamlit secrets without crashing if the file is missing
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            return gspread.authorize(Credentials.from_service_account_info(creds_dict, scopes=scope))
    except FileNotFoundError:
        pass  # No secrets.toml found, move on to the local fallback

    # Fallback to local JSON file
    return gspread.authorize(Credentials.from_service_account_file("data/google_credentials.json", scopes=scope))


def get_tickers_from_sheet():
    try:
        gc = get_google_client()
        sh = gc.open("Stock_List")
        worksheet = sh.worksheet("Fundamentals")
        tickers = worksheet.col_values(1)[1:]
        return [t.strip() for t in tickers if t.strip()]
    except Exception as e:
        print(f"❌ Failed to read Google Sheet: {e}")
        return []


def update_google_sheet(dataframe):
    try:
        gc = get_google_client()
        sh = gc.open("Stock_List")
        worksheet = sh.worksheet("Fundamentals")

        # Robust update mechanism from File 1
        worksheet.clear()

        # Ensure no NaNs or Infs break the JSON payload
        df_clean = dataframe.replace([np.inf, -np.inf], np.nan).fillna(0)

        # Push headers and data
        worksheet.update([df_clean.columns.values.tolist()] + df_clean.values.tolist())
        return True
    except Exception as e:
        print(f"❌ Failed to update Google Sheet: {e}")
        return False


# =========================================
# SAFE FLOAT & METRIC EXTRACTION
# =========================================
def safe_float(value, default=0):
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except:
        return default


def safe_get(df, keys):
    """Try multiple keys to find a financial metric in yfinance dataframes."""
    if df is None or df.empty: return 0
    for key in keys:
        if key in df.index:
            val = df.loc[key].iloc[0]
            return val if pd.notnull(val) else 0
    return 0


# =========================================
# FETCH STOCK DATA
# =========================================
def fetch_stock_data(ticker):
    try:
        print("\n===================")
        print(f"Fetching: {ticker}")

        yf_ticker = f"{ticker}.NS" if "." not in ticker else ticker

        # --- OHLC DATA ---
        hist = get_cached_ohlc(ticker)
        if hist is None or hist.empty or len(hist) < 100:
            hist = get_cached_ohlc(yf_ticker)

        stock = yf.Ticker(yf_ticker)

        if hist is None or hist.empty or len(hist) < 100:
            print(f"⚠️ Cache missing. Fetching live OHLC for {yf_ticker}...")
            hist = stock.history(period="1y")

        if hist is None or hist.empty or len(hist) < 100:
            print(f"❌ Not enough OHLC data for {ticker}")
            return None

        # Clean Data
        hist = hist.copy().dropna(subset=["Close", "Volume"])
        if hist.empty:
            return None

        # --- ROBUST FUNDAMENTALS ---
        raw_info = stock.info
        income = stock.income_stmt
        balance = stock.balance_sheet

        # Deep Financial Calculations
        mcap = raw_info.get("marketCap", 0) / 10000000  # Convert to Crores

        net_income = safe_get(income, ['Net Income', 'Net Income Common Stockholders',
                                       'Net Income From Continuing Operation Net Minority Interest'])
        ebit = safe_get(income, ['EBIT', 'Operating Income', 'Pretax Income'])
        equity = safe_get(balance,
                          ['Stockholders Equity', 'Total Equity Gross Minority Interest', 'Common Stock Equity'])
        assets = safe_get(balance, ['Total Assets'])
        curr_liab = safe_get(balance, ['Total Current Liabilities'])

        roe = (net_income / equity * 100) if equity != 0 else 0
        roce = (ebit / (assets - curr_liab) * 100) if (assets - curr_liab) != 0 else 0

        info = {
            "Market Cap": mcap,
            "Trailing PE": raw_info.get("trailingPE", 0),
            "ROE": roe,
            "ROCE": roce,
            "OPM": raw_info.get("operatingMargins", 0) * 100 if raw_info.get("operatingMargins") else 0,
            "Sales Growth": raw_info.get("revenueGrowth", 0) * 100 if raw_info.get("revenueGrowth") else 0,
            "Debt/Equity": raw_info.get("debtToEquity", 0) / 100 if raw_info.get("debtToEquity") else 0,
            "Trailing EPS": raw_info.get("trailingEps", 0),
            "Sector": raw_info.get("sector", "N/A"),
            "Industry": raw_info.get("industry", "N/A")
        }

        # --- TECHNICAL INDICATORS ---
        hist["RSI"] = ta.momentum.RSIIndicator(close=hist["Close"], window=14).rsi()
        hist["RSI_Slope"] = hist["RSI"].diff()

        hist["SMA20"] = hist["Close"].rolling(20).mean()
        hist["SMA50"] = hist["Close"].rolling(50).mean()

        hist["AvgVol20"] = hist["Volume"].rolling(20).mean()
        hist["AvgVol50"] = hist["Volume"].rolling(50).mean()

        hist["VolumeRatio"] = np.where(hist["AvgVol20"] > 0, hist["Volume"] / hist["AvgVol20"], 0)
        hist["PriceChange5D"] = (hist["Close"].pct_change(5) * 100)
        hist["52WLow"] = hist["Low"].rolling(252).min()

        # Clean NaNs
        hist = hist.replace([np.inf, -np.inf], np.nan).fillna(0)

        print(f"✅ Data Ready: {ticker} (ROE: {round(roe, 1)}%, ROCE: {round(roce, 1)}%)")

        # Sleep to prevent rate limits during deep fetching
        time.sleep(1.2)

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
        market_cap = safe_float(info.get("Market Cap", 0))
        sales_growth = safe_float(info.get("Sales Growth", 0))
        opm = safe_float(info.get("OPM", 0))
        roe = safe_float(info.get("ROE", 0))
        debt_to_equity = safe_float(info.get("Debt/Equity", 999), 999)

        return all([
            market_cap > 1000,
            sales_growth > 10,
            opm > 10,
            roe > 8,
            debt_to_equity < 1.5
        ])
    except:
        return False


# =========================================
# STATUS ENGINE
# =========================================
def get_status(data):
    try:
        hist = data["hist"]
        info = data["info"]
        latest = hist.iloc[-1]
        current_price = safe_float(latest["Close"])
        all_time_high = safe_float(hist["High"].max())

        price_ratio = (current_price / all_time_high) if all_time_high > 0 else 0
        fundamentals_ok = fundamentals_pass(info)

        # --- TECHNICAL LOGIC ---
        vol_buildup = (latest["AvgVol20"] > (latest["AvgVol50"] * 1.2) and latest["VolumeRatio"] > 1.3)
        rsi_recovery = (latest["RSI"] > 45 and latest["RSI"] < 70 and latest["RSI_Slope"] > 0)
        trend_reversal = (current_price > latest["SMA20"] and latest["SMA20"] > latest["SMA50"])
        price_strength = latest["PriceChange5D"] > 0
        far_from_low = (current_price > (latest["52WLow"] * 1.15)) if latest["52WLow"] > 0 else False

        tech_confirm = all([vol_buildup, rsi_recovery, trend_reversal, price_strength, far_from_low])

        # --- STATUS LOGIC ---
        if fundamentals_ok:
            if 0.30 <= price_ratio <= 0.45:
                status = "🚀 STRONG BUY" if tech_confirm else "🔥 PASS"
            elif 0.70 <= price_ratio < 0.80:
                status = "👀 WATCH"
            else:
                status = "WAIT (Price)"
        else:
            status = "WAIT (Fund)"

        # Strip .NS for display
        display_ticker = data["ticker"].split('.')[0]

        return {
            "Ticker": display_ticker,
            "Market Cap": round(safe_float(info.get("Market Cap", 0)), 2),
            "Current Price": round(current_price, 2),
            "PE": round(safe_float(info.get("Trailing PE", 0)), 2),
            "ROE": round(safe_float(info.get("ROE", 0)), 2),
            "ROCE": round(safe_float(info.get("ROCE", 0)), 2),
            "OPM": round(safe_float(info.get("OPM", 0)), 2),
            "Sales Growth": round(safe_float(info.get("Sales Growth", 0)), 2),
            "Debt/Equity": round(safe_float(info.get("Debt/Equity", 0)), 2),
            "EPS": round(safe_float(info.get("Trailing EPS", 0)), 2),
            "Sector": info.get("Sector", "N/A"),
            "Industry": info.get("Industry", "N/A"),
            "Notes": status
        }

    except Exception as e:
        print(f"❌ Status Engine Error: {e}")
        return {
            "Ticker": data.get("ticker", "UNKNOWN").split('.')[0],
            "Market Cap": "", "Current Price": "", "PE": "", "ROE": "",
            "ROCE": "", "OPM": "", "Sales Growth": "", "Debt/Equity": "",
            "EPS": "", "Sector": "ERROR", "Industry": "ERROR", "Notes": "ERROR"
        }


# =========================================
# MAIN SCREENER
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
                "Ticker": ticker.split('.')[0], "Market Cap": "", "Current Price": "",
                "PE": "", "ROE": "", "ROCE": "", "OPM": "", "Sales Growth": "",
                "Debt/Equity": "", "EPS": "", "Sector": "-", "Industry": "-",
                "Notes": "FETCH FAILED"
            }
        results.append(result)

    return pd.DataFrame(results)


# =========================================
# STREAMLIT DASHBOARD
# =========================================
st.title("📊 Screener 1 - Fundamental Scanner")

current_market_key = get_market_rollover_key()
st.write(f"Data locked for trading day: {current_market_key}")

with st.spinner("Scanning stocks and extracting deep financials..."):
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
    fundamentals_pass_df = results_df[results_df["Notes"] == "🔥 PASS"]
    no_quality = results_df[results_df["Notes"].isin(["WAIT (Fund)", "WAIT (Price)", "FETCH FAILED", "ERROR"])]

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("🚀 Execution Ready", len(execution_ready))
    col2.metric("👀 Early Warning", len(early_warning))
    col3.metric("🔥 Fundamentals Pass", len(fundamentals_pass_df))
    col4.metric("❌ No Quality", len(no_quality))

    st.divider()

    st.subheader("🚀 Execution Ready")
    st.dataframe(execution_ready, use_container_width=True)

    st.subheader("👀 Early Warning")
    st.dataframe(early_warning, use_container_width=True)

    st.subheader("🔥 Fundamentals Pass")
    st.dataframe(fundamentals_pass_df, use_container_width=True)

    st.subheader("❌ No Quality / Failed")
    st.dataframe(no_quality, use_container_width=True)
