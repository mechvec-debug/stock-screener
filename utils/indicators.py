import pandas as pd
import ta

def add_indicators(df):
    df["50DMA"] = df["Close"].rolling(50).mean()
    df["200DMA"] = df["Close"].rolling(200).mean()
    df["RSI"] = ta.momentum.RSIIndicator(df["Close"], window=14).rsi()
    df["AvgVolume"] = df["Volume"].rolling(20).mean()
    return df