# =========================================
# FILE: utils/indicator_engine.py
# =========================================

import pandas as pd
import numpy as np
import ta


# =========================================
# SAFE NUMERIC CONVERSION
# =========================================

def safe_numeric(df):

    numeric_cols = [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume"
    ]

    for col in numeric_cols:

        if col in df.columns:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

    return df


# =========================================
# ADD ALL SWING INDICATORS
# =========================================

def add_swing_indicators(df):

    try:

        if df is None or df.empty:

            return pd.DataFrame()

        df = df.copy()

        df = safe_numeric(df)

        df = df.dropna(
            subset=[
                "Open",
                "High",
                "Low",
                "Close",
                "Volume"
            ]
        )

        if len(df) < 220:

            return pd.DataFrame()

        # =====================================
        # TREND INDICATORS
        # =====================================

        df["EMA21"] = ta.trend.EMAIndicator(
            close=df["Close"],
            window=21
        ).ema_indicator()

        df["EMA50"] = ta.trend.EMAIndicator(
            close=df["Close"],
            window=50
        ).ema_indicator()

        df["EMA200"] = ta.trend.EMAIndicator(
            close=df["Close"],
            window=200
        ).ema_indicator()

        # =====================================
        # MOMENTUM
        # =====================================

        df["RSI"] = ta.momentum.RSIIndicator(
            close=df["Close"],
            window=14
        ).rsi()

        df["RSI_Slope"] = (
            df["RSI"]
            .diff()
        )

        # =====================================
        # ADX
        # =====================================

        adx = ta.trend.ADXIndicator(
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            window=14
        )

        df["ADX"] = adx.adx()

        # =====================================
        # ATR
        # =====================================

        atr = ta.volatility.AverageTrueRange(
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            window=14
        )

        df["ATR"] = (
            atr.average_true_range()
        )

        df["ATR_MA20"] = (
            df["ATR"]
            .rolling(20)
            .mean()
        )

        # =====================================
        # VOLUME
        # =====================================

        df["AvgVol20"] = (
            df["Volume"]
            .rolling(20)
            .mean()
        )

        df["AvgVol50"] = (
            df["Volume"]
            .rolling(50)
            .mean()
        )

        df["VolumeRatio"] = np.where(
            df["AvgVol20"] > 0,
            df["Volume"] / df["AvgVol20"],
            0
        )

        # =====================================
        # BREAKOUT LEVELS
        # =====================================

        df["HHV10"] = (
            df["High"]
            .shift(1)
            .rolling(10)
            .max()
        )

        df["HHV20"] = (
            df["High"]
            .shift(1)
            .rolling(20)
            .max()
        )

        df["LLV10"] = (
            df["Low"]
            .shift(1)
            .rolling(10)
            .min()
        )

        # =====================================
        # PRICE STRENGTH
        # =====================================

        df["PriceChange5D"] = (
            df["Close"]
            .pct_change(5)
            * 100
        )

        df["PriceChange20D"] = (
            df["Close"]
            .pct_change(20)
            * 100
        )

        # =====================================
        # TRADED VALUE
        # =====================================

        df["TradedValue"] = (
            df["Close"]
            * df["Volume"]
        )

        df["AvgTradedValue20"] = (
            df["TradedValue"]
            .rolling(20)
            .mean()
        )

        # =====================================
        # DISTANCE FROM EMA21
        # =====================================

        df["DistanceEMA21"] = (
            (
                df["Close"]
                - df["EMA21"]
            )
            /
            df["EMA21"]
        ) * 100

        # =====================================
        # TREND SCORE
        # =====================================

        df["TrendScore"] = np.where(
            (
                (df["EMA21"] > df["EMA50"])
                &
                (df["EMA50"] > df["EMA200"])
            ),
            100,
            0
        )

        # =====================================
        # CLEANUP
        # =====================================

        df = (
            df
            .replace(
                [np.inf, -np.inf],
                np.nan
            )
            .fillna(0)
        )

        return df

    except Exception as e:

        print(
            f"❌ Indicator Engine Error: {e}"
        )

        return pd.DataFrame()
