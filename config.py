NIFTY_TICKER = "^NSEI"

RSI_PERIOD = 14
VOLUME_MULTIPLIER = 1.5

FUNDAMENTAL_FILTERS = {
    "roe": 15,
    "revenue_growth": 10,
    "profit_growth": 10,
    "de_ratio": 1
}
OPTIMIZED_PARAMS = {
    "breakout_period": 20,
    "volume_multiplier": 1.5,
    "stop_loss": 0.05,
    "target": 0.10
}
# Market Data Settings
PERIOD = "2y"
INTERVAL = "1d"

# Strategy Params
EMA_FAST = 21
EMA_MEDIUM = 50
EMA_SLOW = 200
RSI_PERIOD = 14
VOL_MA_PERIOD = 20
ATR_PERIOD = 14
