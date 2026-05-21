# =========================================
# FILE: screener_2.py
# =========================================

import pandas as pd
import streamlit as st
import ta
import yfinance as yf
import gspread
import datetime
import pytz

from utils.data_fetcher import get_price_data
from utils.market_phase import get_market_phase


# =========================
# SMART DAILY CACHE KEY
# =========================
def get_market_rollover_key():
    """Changes the cache key only at 4:00 PM IST daily."""
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(ist)
    shifted_time = now - datetime.timedelta(hours=16)
    return shifted_time.strftime('%Y-%m-%d')


# =========================
# PAGE HEADER
# =========================
phase = get_market_phase()

st.title("📊 Scanner 2 - 20-Day Breakout")
st.subheader(f"Current Market Phase: {phase}")

current_market_key = get_market_rollover_key()
st.write(f"Data locked for trading day: {current_market_key}")


# =========================================
# GOOGLE SHEETS CONNECTION
# =========================================
def get_google_client():
    if "gcp_service_account" in st.secrets:
        return gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
    else:
        return gspread.service_account(filename="data/google_credentials.json")

@st.cache_data(show_spinner=False)
def get_tickers_from_sheet(cache_key):
    try:
        gc = get_google_client()
        sh = gc.open("Stock_List")
        worksheet = sh.worksheet("Fundamentals")
        tickers = worksheet.col_values(1)[1:]
        return [t.strip() for t in tickers if t.strip()]
    except Exception as e:
        st.error(f"❌ Failed to read Google Sheet: {e}")
        return []

# =========================
# SMART CACHING ENGINE
# =========================
@st.cache_data(show_spinner=False)
def fetch_raw_stock_data(ticker, cache_key):
    try:
        yf_ticker = f"{ticker}.NS" if not ticker.endswith(".NS") else ticker

        # FIX 1: Try .NS FIRST to prevent the Yahoo Finance "delisted" terminal spam
        df = get_price_data(yf_ticker)

        # Ultimate live fallback if the custom fetcher fails
        if df is None or df.empty or len(df) < 60:
            df = yf.Ticker(yf_ticker).history(period="1y")

        if df is None or df.empty or len(df) < 60:
            return None, None

        info = yf.Ticker(yf_ticker).info
        return df, info
    except Exception:
        return None, None


@st.cache_data(show_spinner=False)
def get_benchmark_return(cache_key):
    try:
        nifty_df = get_price_data("^NSEI")

        if nifty_df is None or nifty_df.empty:
            nifty_df = yf.Ticker("^NSEI").history(period="1y")

        nifty_close = nifty_df["Close"].squeeze()
        nifty_return = ((nifty_close.iloc[-1] - nifty_close.iloc[-20]) / nifty_close.iloc[-20]) * 100
        return nifty_return
    except:
        return 0


# =========================
# SIDEBAR CONTROLS
# =========================
st.sidebar.header("⚙️ Scanner Settings")

rsi_threshold = st.sidebar.slider("RSI Threshold", min_value=40, max_value=80, value=55)
volume_threshold = st.sidebar.slider("Volume Ratio Threshold", min_value=1.0, max_value=3.0, value=1.5, step=0.1)
breakout_days = st.sidebar.slider("Breakout Days", min_value=10, max_value=60, value=20)
holding_period = st.sidebar.slider("Holding Period", min_value=10, max_value=60, value=30)
run_optimization = st.sidebar.checkbox("Run Parameter Optimization")

if run_optimization:
    rsi_test_values = [50, 55, 60]
    volume_test_values = [1.2, 1.5, 2.0]
else:
    rsi_test_values = [rsi_threshold]
    volume_test_values = [volume_threshold]

# =========================
# INITIALIZE DATA
# =========================
tickers = get_tickers_from_sheet(current_market_key)
nifty_return_val = get_benchmark_return(current_market_key)

results = []
optimization_results = []

if not tickers:
    st.warning("No tickers found in Google Sheet. Please check your connection.")
    st.stop()

# =========================
# PRE-FETCH ALL DATA
# =========================
cached_market_data = {}

with st.spinner("Loading End-of-Day market data..."):
    for stock in tickers:
        df, info = fetch_raw_stock_data(stock, current_market_key)
        if df is not None:
            cached_market_data[stock] = {"df": df.copy(), "info": info}

# =========================
# STOCK SCAN LOOP
# =========================
with st.spinner("Running calculations..."):
    for rsi_value in rsi_test_values:
        for volume_value in volume_test_values:
            for stock, data in cached_market_data.items():
                try:
                    df = data["df"]
                    info = data["info"]

                    # FIX 2: Use "or 0" / "or 999" to catch explicit 'None' values from Yahoo
                    # Finance and prevent Arrow Serialization crashes in Streamlit
                    market_cap = info.get("marketCap") or 0
                    roe = info.get("returnOnEquity") or 0
                    profit_margin = info.get("profitMargins") or 0
                    revenue_growth = info.get("revenueGrowth") or 0
                    debt_to_equity = info.get("debtToEquity") or 999
                    pe_ratio = info.get("trailingPE") or 999

                    if not (
                            market_cap > 50000000000 and roe > 0.15 and profit_margin > 0.10 and revenue_growth > 0 and debt_to_equity < 1 and pe_ratio < 50):
                        continue

                    # Price & Indicators
                    close_series = df["Close"].squeeze()
                    volume_series = df["Volume"].squeeze()

                    df["50DMA"] = close_series.rolling(50).mean()
                    df["RSI"] = ta.momentum.RSIIndicator(close=close_series, window=14).rsi()
                    df["AvgVolume"] = volume_series.rolling(20).mean()
                    df["BreakoutHigh"] = close_series.rolling(breakout_days).max()
                    df["DailyRange"] = ((df["High"] - df["Low"]) / df["Close"]) * 100

                    latest = df.iloc[-1]
                    close_price = latest["Close"].item()
                    dma50 = latest["50DMA"].item()
                    rsi = latest["RSI"].item()
                    current_volume = latest["Volume"].item()
                    avg_volume = latest["AvgVolume"].item()
                    breakout_level = df["BreakoutHigh"].iloc[-2].item()

                    # Calculations
                    distance_from_dma = ((close_price - dma50) / dma50) * 100
                    volume_ratio = (current_volume / avg_volume) if avg_volume > 0 else 0
                    breakout_strength = ((close_price - breakout_level) / breakout_level) * 100

                    stock_return = ((close_series.iloc[-1] - close_series.iloc[-20]) / close_series.iloc[-20]) * 100
                    relative_strength = stock_return - nifty_return_val
                    avg_range = df["DailyRange"].rolling(10).mean().iloc[-1]

                    # Scoring
                    score = 0
                    score += min(rsi, 100) * 0.20
                    score += min(volume_ratio * 20, 100) * 0.25
                    score += min(max(relative_strength * 5, 0), 100) * 0.30
                    score += min(distance_from_dma * 5, 100) * 0.25

                    # Backtesting Metrics
                    future_return = 0
                    if len(df) > holding_period:
                        future_close = df["Close"].iloc[-1]
                        past_close = df["Close"].iloc[-holding_period]
                        future_return = ((future_close - past_close) / past_close) * 100

                    # Adaptive Logic
                    trend_condition = (close_price > dma50)

                    if phase == "BULL":
                        momentum_condition = (rsi > rsi_value)
                        volume_condition = (volume_ratio > volume_value)
                        breakout_condition = (close_price > breakout_level)
                        relative_strength_condition = (relative_strength > 5)
                        volatility_condition = (avg_range < 3)
                    elif phase == "BEAR":
                        momentum_condition = (rsi > (rsi_value - 10))
                        volume_condition = (volume_ratio > (volume_value - 0.3))
                        breakout_condition = (close_price > dma50)
                        relative_strength_condition = (relative_strength > 0)
                        volatility_condition = (avg_range < 2)
                    else:
                        momentum_condition = (rsi > (rsi_value - 5))
                        volume_condition = (volume_ratio > (volume_value - 0.2))
                        breakout_condition = (close_price > breakout_level)
                        relative_strength_condition = (relative_strength > 2)
                        volatility_condition = (avg_range < 2.5)

                    # Final Signal
                    if (trend_condition and momentum_condition and volume_condition and
                            breakout_condition and relative_strength_condition and volatility_condition):

                        if run_optimization:
                            optimization_results.append({
                                "RSI Threshold": rsi_value,
                                "Volume Threshold": volume_value,
                                "Stock": stock,
                                "Score": round(score, 2),
                                "Future Return": round(future_return, 2)
                            })

                        if rsi_value == rsi_threshold and volume_value == volume_threshold:
                            results.append({
                                "Stock": stock,
                                "Close": round(close_price, 2),
                                "Breakout Level": round(breakout_level, 2),
                                "Breakout %": round(breakout_strength, 2),
                                "RSI": round(rsi, 2),
                                "% Above 50DMA": round(distance_from_dma, 2),
                                "Volume Ratio": round(volume_ratio, 2),
                                "ROE": round(roe * 100, 2),
                                "Profit Margin": round(profit_margin * 100, 2),
                                "Revenue Growth": round(revenue_growth * 100, 2),
                                "Debt/Equity": round(debt_to_equity, 2),
                                "PE Ratio": round(pe_ratio, 2),
                                "Relative Strength": round(relative_strength, 2),
                                "Score": round(score, 2),
                                "30D Return %": round(future_return, 2),
                                "Signal": "20D BREAKOUT ✅"
                            })
                except Exception as e:
                    pass

# =========================
# DISPLAY RESULTS
# =========================
# Explicitly force dataframe to clean itself of any remaining missing values before Streamlit draws it
results_df = pd.DataFrame(results).fillna(0)

if results_df.empty:
    st.warning("No breakout stocks found today with current settings.")
else:
    results_df = results_df.sort_values(by="Score", ascending=False)
    st.dataframe(results_df, width="stretch")

    st.subheader("📈 Backtest Summary")

    avg_return = results_df["30D Return %"].mean()
    win_rate = (len(results_df[results_df["30D Return %"] > 0]) / len(results_df)) * 100
    best_trade = results_df["30D Return %"].max()
    worst_trade = results_df["30D Return %"].min()
    avg_score = results_df["Score"].mean()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Win Rate", f"{round(win_rate, 2)}%")
    col2.metric("Avg 30D Return", f"{round(avg_return, 2)}%")
    col3.metric("Best Trade", f"{round(best_trade, 2)}%")
    col4.metric("Worst Trade", f"{round(worst_trade, 2)}%")
    col5.metric("Avg Score", round(avg_score, 2))

# =========================
# OPTIMIZATION RESULTS
# =========================
if run_optimization:
    st.divider()
    st.subheader("🛠️ Optimization Results")
    optimization_df = pd.DataFrame(optimization_results).fillna(0)

    if not optimization_df.empty:
        optimization_summary = (
            optimization_df.groupby(["RSI Threshold", "Volume Threshold"])
            .agg({"Score": "mean", "Future Return": "mean", "Stock": "count"})
            .reset_index()
        )
        optimization_summary.columns = ["RSI", "Volume", "Avg Score", "Avg Return", "Signals Found"]
        optimization_summary = optimization_summary.sort_values(by="Avg Return", ascending=False)
        st.dataframe(optimization_summary, width="stretch")
    else:
        st.warning("No optimization results yielded any signals.")