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
import numpy as np

from gspread_dataframe import set_with_dataframe

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
    - Uses Streamlit Secrets on cloud
    - Uses local JSON file on desktop
    """

    if "gcp_service_account" in st.secrets:
        return gspread.service_account_from_dict(
            dict(st.secrets["gcp_service_account"])
        )
    else:
        return gspread.service_account(
            filename="data/google_credentials.json"
        )


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

        worksheet.batch_clear(["A2:M1000"])

        set_with_dataframe(
            worksheet,
            dataframe,
            row=2,
            col=1,
            include_column_header=False
        )

        return True

    except Exception as e:

        print(f"❌ Failed to update Google Sheet: {e}")

        return False


# =========================================
# SAFE FLOAT CONVERTER
# =========================================
def safe_float(value, default=0):

    try:

        if value is None:
            return default

        if pd.isna(value):
            return default

        return float(value)

    except:
        return default


# =========================================
# FETCH STOCK DATA
# =========================================
def fetch_stock_data(ticker):

    try:

        print("\n===================")
        print(f"Fetching: {ticker}")

        yf_ticker = f"{ticker}.NS"

        # =========================================
        # OHLC DATA
        # =========================================

        hist = get_cached_ohlc(ticker)

        if hist is None or hist.empty or len(hist) < 100:
            hist = get_cached_ohlc(yf_ticker)

        if hist is None or hist.empty or len(hist) < 100:

            print(f"⚠️ Cache missing. Fetching live OHLC for {yf_ticker}...")

            stock = yf.Ticker(yf_ticker)

            hist = stock.history(period="1y")

        if hist is None or hist.empty or len(hist) < 100:

            print(f"❌ Not enough OHLC data for {ticker}")

            return None

        # =========================================
        # CLEAN DATA
        # =========================================

        hist = hist.copy()

        hist = hist.dropna(subset=["Close", "Volume"])

        if hist.empty:
            return None

        # =========================================
        # FUNDAMENTALS
        # =========================================

        fund_df = get_fundamental_cache()

        base_ticker = ticker.replace(".NS", "")

        stock_row = pd.DataFrame()

        if fund_df is not None and not fund_df.empty:

            stock_row = fund_df[
                fund_df["Ticker"].isin(
                    [ticker, base_ticker, yf_ticker]
                )
            ]

        if stock_row.empty:

            print(f"⚠️ Cache missing. Fetching live Fundamentals for {yf_ticker}...")

            raw_info = yf.Ticker(yf_ticker).info

            info = {
                "Market Cap": raw_info.get("marketCap", 0),
                "Trailing PE": raw_info.get("trailingPE", 0),

                "ROE": (
                    raw_info.get("returnOnEquity", 0) * 100
                    if raw_info.get("returnOnEquity")
                    else 0
                ),

                "ROCE": 0,

                "OPM": (
                    raw_info.get("operatingMargins", 0) * 100
                    if raw_info.get("operatingMargins")
                    else 0
                ),

                "Sales Growth": (
                    raw_info.get("revenueGrowth", 0) * 100
                    if raw_info.get("revenueGrowth")
                    else 0
                ),

                "Debt/Equity": (
                    raw_info.get("debtToEquity", 0) / 100
                    if raw_info.get("debtToEquity")
                    else 0
                ),

                "Trailing EPS": raw_info.get("trailingEps", 0),

                "Sector": raw_info.get("sector", "N/A"),

                "Industry": raw_info.get("industry", "N/A")
            }

        else:

            info = stock_row.iloc[0].to_dict()

        # =========================================
        # TECHNICAL INDICATORS
        # =========================================

        # RSI
        hist["RSI"] = ta.momentum.RSIIndicator(
            close=hist["Close"],
            window=14
        ).rsi()

        # RSI Momentum
        hist["RSI_Slope"] = hist["RSI"].diff()

        # Moving Averages
        hist["SMA20"] = hist["Close"].rolling(20).mean()

        hist["SMA50"] = hist["Close"].rolling(50).mean()

        # Volume Averages
        hist["AvgVol20"] = hist["Volume"].rolling(20).mean()

        hist["AvgVol50"] = hist["Volume"].rolling(50).mean()

        # Relative Volume
        hist["VolumeRatio"] = np.where(
            hist["AvgVol20"] > 0,
            hist["Volume"] / hist["AvgVol20"],
            0
        )

        # Short-Term Strength
        hist["PriceChange5D"] = (
            hist["Close"].pct_change(5) * 100
        )

        # 52 Week Low
        hist["52WLow"] = hist["Low"].rolling(252).min()

        # Clean NaNs
        hist = hist.replace([np.inf, -np.inf], np.nan)

        hist = hist.fillna(0)

        print(f"✅ Data Ready: {ticker}")

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

        debt_to_equity = safe_float(
            info.get("Debt/Equity", 999),
            999
        )

        return all([
            market_cap > 1000,
            sales_growth > 5,
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

        if all_time_high <= 0:
            price_ratio = 0
        else:
            price_ratio = current_price / all_time_high

        fundamentals_ok = fundamentals_pass(info)

        # =========================================
        # VOLUME ACCUMULATION
        # =========================================

        vol_buildup = (
            latest["AvgVol20"] > (latest["AvgVol50"] * 1.2)
            and latest["VolumeRatio"] > 1.3
        )

        # =========================================
        # RSI RECOVERY
        # =========================================

        rsi_recovery = (
            latest["RSI"] > 45
            and latest["RSI"] < 70
            and latest["RSI_Slope"] > 0
        )

        # =========================================
        # TREND REVERSAL
        # =========================================

        trend_reversal = (
            current_price > latest["SMA20"]
            and latest["SMA20"] > latest["SMA50"]
        )

        # =========================================
        # SHORT TERM STRENGTH
        # =========================================

        price_strength = latest["PriceChange5D"] > 0

        # =========================================
        # AVOID FALLING KNIVES
        # =========================================

        far_from_low = (
            current_price > (latest["52WLow"] * 1.15)
            if latest["52WLow"] > 0
            else False
        )

        # =========================================
        # FINAL TECH CONFIRMATION
        # =========================================

        tech_confirm = all([
            vol_buildup,
            rsi_recovery,
            trend_reversal,
            price_strength,
            far_from_low
        ])

        # =========================================
        # STATUS LOGIC
        # =========================================

        if fundamentals_ok:

            # Deep value accumulation zone
            if 0.30 <= price_ratio <= 0.45:

                if tech_confirm:
                    status = "🚀 STRONG BUY"
                else:
                    status = "🔥 PASS"

            # Early recovery zone
            elif 0.70 <= price_ratio < 0.80:

                status = "👀 WATCH"

            else:

                status = "WAIT (Price)"

        else:

            status = "WAIT (Fund)"

        # =========================================
        # RETURN OUTPUT
        # =========================================

        return {
            "Ticker": data["ticker"],

            "Market Cap": safe_float(
                info.get("Market Cap", 0)
            ),

            "Current Price": round(current_price, 2),

            "PE": round(
                safe_float(info.get("Trailing PE", 0)),
                2
            ),

            "ROE": round(
                safe_float(info.get("ROE", 0)),
                2
            ),

            "ROCE": round(
                safe_float(info.get("ROCE", 0)),
                2
            ),

            "OPM": round(
                safe_float(info.get("OPM", 0)),
                2
            ),

            "Sales Growth": round(
                safe_float(info.get("Sales Growth", 0)),
                2
            ),

            "Debt/Equity": round(
                safe_float(info.get("Debt/Equity", 0)),
                2
            ),

            "EPS": round(
                safe_float(info.get("Trailing EPS", 0)),
                2
            ),

            "Sector": info.get("Sector", "N/A"),

            "Industry": info.get("Industry", "N/A"),

            "Notes": status
        }

    except Exception as e:

        print(f"❌ Status Engine Error: {e}")

        return {
            "Ticker": data.get("ticker", "UNKNOWN"),
            "Market Cap": "",
            "Current Price": "",
            "PE": "",
            "ROE": "",
            "ROCE": "",
            "OPM": "",
            "Sales Growth": "",
            "Debt/Equity": "",
            "EPS": "",
            "Sector": "ERROR",
            "Industry": "ERROR",
            "Notes": "ERROR"
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
                "Ticker": ticker,
                "Market Cap": "",
                "Current Price": "",
                "PE": "",
                "ROE": "",
                "ROCE": "",
                "OPM": "",
                "Sales Growth": "",
                "Debt/Equity": "",
                "EPS": "",
                "Sector": "-",
                "Industry": "-",
                "Notes": "FETCH FAILED"
            }

        results.append(result)

        time.sleep(1)

    return pd.DataFrame(results)


# =========================================
# STREAMLIT DASHBOARD
# =========================================

st.title("📊 Screener 1 - Fundamental Scanner")

current_market_key = get_market_rollover_key()

st.write(f"Data locked for trading day: {current_market_key}")

with st.spinner("Scanning stocks from Google Sheets..."):

    results_df = run_screener(current_market_key)

if results_df.empty:

    st.warning(
        "No stocks found. Check your Google Sheet connection."
    )

else:

    if "sheet_updated" not in st.session_state:

        with st.spinner("Pushing results to Google Sheets..."):

            success = update_google_sheet(results_df)

            if success:

                st.session_state.sheet_updated = True

                st.success(
                    "✅ Google Sheet Auto-Updated Successfully!"
                )

            else:

                st.error(
                    "❌ Failed to update Google Sheet."
                )

    else:

        st.success("✅ Google Sheet is up to date.")

    if st.button("🔄 Force Refresh Sheets"):

        update_google_sheet(results_df)

        st.toast("Sheets Refreshed!")

    st.divider()

    execution_ready = results_df[
        results_df["Notes"] == "🚀 STRONG BUY"
    ]

    early_warning = results_df[
        results_df["Notes"] == "👀 WATCH"
    ]

    fundamentals_pass_df = results_df[
        results_df["Notes"] == "🔥 PASS"
    ]

    no_quality = results_df[
        results_df["Notes"].isin([
            "WAIT (Fund)",
            "WAIT (Price)",
            "FETCH FAILED",
            "ERROR"
        ])
    ]

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "🚀 Execution Ready",
        len(execution_ready)
    )

    col2.metric(
        "👀 Early Warning",
        len(early_warning)
    )

    col3.metric(
        "🔥 Fundamentals Pass",
        len(fundamentals_pass_df)
    )

    col4.metric(
        "❌ No Quality",
        len(no_quality)
    )

    st.divider()

    st.subheader("🚀 Execution Ready")
    st.dataframe(execution_ready, use_container_width=True)

    st.subheader("👀 Early Warning")
    st.dataframe(early_warning, use_container_width=True)

    st.subheader("🔥 Fundamentals Pass")
    st.dataframe(fundamentals_pass_df, use_container_width=True)

    st.subheader("❌ No Quality / Failed")
    st.dataframe(no_quality, use_container_width=True)
