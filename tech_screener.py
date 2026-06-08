from utils.cache_fetcher import get_cached_ohlc
from utils.indicator_engine import add_swing_indicators

df = get_cached_ohlc("RELIANCE")

df = add_swing_indicators(df)

print(
    df[
        [
            "Close",
            "EMA21",
            "EMA50",
            "EMA200",
            "RSI",
            "ADX",
            "ATR",
            "VolumeRatio",
            "HHV10"
        ]
    ].tail()
)
