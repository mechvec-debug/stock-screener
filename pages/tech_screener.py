# =========================================
# FILE: pages/tech_screener.py
# =========================================

import streamlit as st
import pandas as pd
import numpy as np
import datetime
import pytz
import gspread

from google.oauth2.service_account import Credentials

from utils.cache_fetcher import get_cached_ohlc
from utils.indicator_engine import add_swing_indicators


# =========================================
# CONFIGURATION
# =========================================

CONFIG = {

    "RSI_RESET": 40,
    "RSI_RECOVERY": 55,

    "ADX_MIN": 25,

    "VOL_MULTIPLIER": 2.0,

    "MIN_PRICE": 100,

    "MIN_TRADED_VALUE": 100000000,

    "MAX_DISTANCE_EMA21": 8,

    "ATR_SL": 1.5,

    "ATR_TP1": 1.5,

    "ATR_TP2": 3.0
}


# =========================================
# MARKET DATE
# =========================================

def get_market_rollover_key():

    ist = pytz.timezone("Asia/Kolkata")

    now = datetime.datetime.now(ist)

    shifted_time = now - datetime.timedelta(hours=16)

    return shifted_time.strftime("%Y-%m-%d")


# =========================================
# GOOGLE SHEETS
# =========================================

def get_google_client():

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    try:

        if "gcp_service_account" in st.secrets:

            creds_dict = dict(
                st.secrets["gcp_service_account"]
            )

            return gspread.authorize(
                Credentials.from_service_account_info(
                    creds_dict,
                    scopes=scope
                )
            )

    except Exception:
        pass

    return gspread.authorize(
        Credentials.from_service_account_file(
            "data/google_credentials.json",
            scopes=scope
        )
    )


def get_tickers_from_sheet():

    try:

        gc = get_google_client()

        sh = gc.open("Stock_List")

        worksheet = sh.worksheet(
            "Fundamentals"
        )

        tickers = worksheet.col_values(1)[1:]

        return [
            t.strip()
            for t in tickers
            if t.strip()
        ]

    except Exception as e:

        print(e)

        return []


# =========================================
# MARKET FILTER
# =========================================

def get_market_mode():

    try:

        nifty = get_cached_ohlc("^NSEI")

        if nifty.empty:
            return "UNKNOWN"

        nifty = add_swing_indicators(nifty)

        latest = nifty.iloc[-1]

        if latest["Close"] > latest["EMA200"]:

            return "BULLISH"

        return "WEAK"

    except:

        return "UNKNOWN"


# =========================================
# SCORE ENGINE
# =========================================

def calculate_score(latest):

    score = (

        latest["ADX"] * 0.30

        +

        latest["RSI"] * 0.20

        +

        latest["VolumeRatio"] * 15

        +

        latest["TrendScore"] * 0.20

    )

    return round(score, 2)


# =========================================
# ACTIVE SIGNAL
# =========================================

def get_swing_signal(ticker, df, market_mode):

    try:

        latest = df.iloc[-1]

        close = latest["Close"]

        trend = (

            close > latest["EMA200"]

            and

            latest["EMA21"] >
            latest["EMA50"]

            and

            latest["EMA50"] >
            latest["EMA200"]

        )

        rsi_reset = (

            df["RSI"]
            .tail(10)
            .min()

            < CONFIG["RSI_RESET"]

        )

        rsi_recovery = (

            latest["RSI"]
            > CONFIG["RSI_RECOVERY"]

        )

        adx_ok = (

            latest["ADX"]
            > CONFIG["ADX_MIN"]

        )

        volume_ok = (

            latest["VolumeRatio"]
            > CONFIG["VOL_MULTIPLIER"]

        )

        breakout = (

            close >
            latest["HHV10"]

        )

        atr_ok = (

            latest["ATR"]
            >
            latest["ATR_MA20"]

        )

        liquidity_ok = (

            latest["AvgTradedValue20"]
            >
            CONFIG["MIN_TRADED_VALUE"]

        )

        price_ok = (

            close >
            CONFIG["MIN_PRICE"]

        )

        distance_ok = (

            latest["DistanceEMA21"]
            <
            CONFIG["MAX_DISTANCE_EMA21"]

        )

        signal = all([

            trend,

            rsi_reset,

            rsi_recovery,

            adx_ok,

            volume_ok,

            breakout,

            atr_ok,

            liquidity_ok,

            price_ok,

            distance_ok

        ])

        if not signal:

            return None

        atr = latest["ATR"]

        entry = close

        stoploss = (
            entry -
            (CONFIG["ATR_SL"] * atr)
        )

        target1 = (
            entry +
            (CONFIG["ATR_TP1"] * atr)
        )

        target2 = (
            entry +
            (CONFIG["ATR_TP2"] * atr)
        )

        risk_pct = round(
            ((entry - stoploss) / entry) * 100,
            2
        )

        reward_pct = round(
            ((target2 - entry) / entry) * 100,
            2
        )

        rr = round(
            reward_pct / risk_pct,
            2
        )

        score = calculate_score(
            latest
        )

        grade = "B"

        if score >= 90:
            grade = "A+"

        elif score >= 80:
            grade = "A"

        return {

            "Ticker": ticker,

            "Market": market_mode,

            "Grade": grade,

            "Score": score,

            "Price": round(entry, 2),

            "RSI": round(
                latest["RSI"], 2
            ),

            "ADX": round(
                latest["ADX"], 2
            ),

            "Volume Ratio": round(
                latest["VolumeRatio"], 2
            ),

            "ATR": round(
                atr, 2
            ),

            "Entry": round(
                entry, 2
            ),

            "SL": round(
                stoploss, 2
            ),

            "TP1": round(
                target1, 2
            ),

            "TP2": round(
                target2, 2
            ),

            "Risk %": risk_pct,

            "Reward %": reward_pct,

            "RR": rr

        }

    except Exception as e:

        print(
            f"{ticker}: {e}"
        )

        return None


# =========================================
# WATCHLIST
# =========================================

def get_watchlist_signal(ticker, df):

    latest = df.iloc[-1]

    trend = (
        latest["EMA21"] >
        latest["EMA50"] >
        latest["EMA200"]
    )

    watch = (

        trend

        and

        latest["RSI"] > 50

        and

        latest["ADX"] > 20

        and

        latest["VolumeRatio"] > 1.5

        and

        latest["Close"] <= latest["HHV10"]

    )

    if watch:

        return {

            "Ticker": ticker,

            "Price": round(
                latest["Close"], 2
            ),

            "RSI": round(
                latest["RSI"], 2
            ),

            "ADX": round(
                latest["ADX"], 2
            ),

            "Volume Ratio": round(
                latest["VolumeRatio"], 2
            )

        }

    return None


# =========================================
# RUN SCANNER
# =========================================

@st.cache_data(show_spinner=False)

def run_scanner(cache_key):

    active = []

    watchlist = []

    tickers = get_tickers_from_sheet()

    market_mode = get_market_mode()

    for ticker in tickers:

        df = get_cached_ohlc(ticker)

        if df.empty:
            continue

        df = add_swing_indicators(df)

        if df.empty:
            continue

        active_signal = get_swing_signal(
            ticker,
            df,
            market_mode
        )

        if active_signal:

            active.append(
                active_signal
            )

        else:

            watch = get_watchlist_signal(
                ticker,
                df
            )

            if watch:

                watchlist.append(
                    watch
                )

    active_df = pd.DataFrame(active)

    watch_df = pd.DataFrame(watchlist)

    if not active_df.empty:

        active_df = (
            active_df
            .sort_values(
                "Score",
                ascending=False
            )
        )

    return active_df, watch_df


# =========================================
# STREAMLIT UI
# =========================================

st.title(
    "🚀 Swing Engine Scanner"
)

market_key = (
    get_market_rollover_key()
)

active_df, watch_df = run_scanner(
    market_key
)

market_mode = get_market_mode()

st.info(
    f"Market Mode: {market_mode}"
)

col1, col2 = st.columns(2)

col1.metric(
    "🚀 Active Signals",
    len(active_df)
)

col2.metric(
    "👀 Watchlist",
    len(watch_df)
)

st.divider()

st.subheader(
    "🚀 Active Signals"
)

st.dataframe(
    active_df,
    use_container_width=True
)

st.divider()

st.subheader(
    "👀 Watchlist Candidates"
)

st.dataframe(
    watch_df,
    use_container_width=True
)
