import yfinance as yf
import pandas as pd


def fetch_data(ticker, period, interval):
    """Downloads historical OHLCV data."""
    df = yf.download(ticker, period=period, interval=interval, progress=False)

    if df.empty:
        raise ValueError(f"No data found for {ticker}")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    return df


def fetch_market_cap(ticker):
    """Fetches the market cap separately."""
    try:
        info = yf.Ticker(ticker).info
        return info.get('marketCap', 'N/A')
    except Exception:
        return 'N/A'
