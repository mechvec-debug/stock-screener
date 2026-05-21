import yfinance as yf

def get_market_phase():

    nifty = yf.download("^NSEI", period="1y", progress=False)

    nifty["50DMA"] = nifty["Close"].rolling(50).mean()
    nifty["200DMA"] = nifty["Close"].rolling(200).mean()

    latest = nifty.iloc[-1]

    close = latest["Close"].item()
    dma50 = latest["50DMA"].item()

    # 200DMA may still be NaN if not enough data
    dma200 = latest["200DMA"]

    if hasattr(dma200, "item"):
        dma200 = dma200.item()

    if close > dma200 and dma50 > dma200:
        phase = "BULL"

    elif close < dma200 and dma50 < dma200:
        phase = "BEAR"

    else:
        phase = "SIDEWAYS"

    return phase