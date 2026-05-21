import pandas as pd
from config import OPTIMIZED_PARAMS
from utils.data_fetcher import get_price_data
from utils.indicators import add_indicators
from utils.market_phase import get_market_phase

def generate_signals(stock_list):

    phase = get_market_phase()
    signals = []

    for stock in stock_list:
        df = get_price_data(stock, period="6mo")
        df = add_indicators(df)

        latest = df.iloc[-1]

        breakout_level = df["Close"].rolling(
            OPTIMIZED_PARAMS["breakout_period"]
        ).max().iloc[-2]

        breakout = latest["Close"] > breakout_level

        volume_spike = latest["Volume"] > (
            OPTIMIZED_PARAMS["volume_multiplier"] * latest["AvgVolume"]
        )

        trend = latest["Close"] > latest["50DMA"]

        if phase == "BULL" and breakout and volume_spike and trend:
            signals.append({
                "Stock": stock,
                "Signal": "BUY",
                "Price": round(latest["Close"], 2)
            })

    return pd.DataFrame(signals), phase