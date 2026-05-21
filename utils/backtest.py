import pandas as pd

def backtest_strategy(df):
    trades = []

    position = None

    for i in range(50, len(df)):  # skip initial data
        row = df.iloc[i]

        # Entry condition
        breakout = row["Close"] > df["Close"].rolling(20).max().iloc[i-1]
        volume_spike = row["Volume"] > 1.5 * df["Volume"].rolling(20).mean().iloc[i-1]
        trend = row["Close"] > row["50DMA"]

        if position is None:
            if breakout and volume_spike and trend:
                position = {
                    "entry_price": row["Close"],
                    "entry_date": df.index[i]
                }

        else:
            change = (row["Close"] - position["entry_price"]) / position["entry_price"]

            # Exit conditions
            if change >= 0.10 or change <= -0.05 or i - df.index.get_loc(position["entry_date"]) > 30:
                trades.append({
                    "entry": position["entry_date"],
                    "exit": df.index[i],
                    "return": round(change * 100, 2)
                })
                position = None

    return pd.DataFrame(trades)