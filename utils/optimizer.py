import itertools
import pandas as pd
from utils.backtest import backtest_strategy

def optimize_strategy(df):

    breakout_periods = [10, 20, 30]
    volume_multipliers = [1.2, 1.5, 2.0]
    stop_losses = [0.03, 0.05, 0.07]
    targets = [0.08, 0.10, 0.15]

    results = []

    for bp, vm, sl, tgt in itertools.product(
        breakout_periods,
        volume_multipliers,
        stop_losses,
        targets
    ):

        trades = backtest_strategy(
            df.copy(),
            breakout_period=bp,
            volume_multiplier=vm,
            stop_loss=sl,
            target=tgt
        )

        if len(trades) == 0:
            continue

        win_rate = (trades["return"] > 0).mean()
        avg_return = trades["return"].mean()
        total_return = trades["return"].sum()

        results.append({
            "breakout": bp,
            "volume": vm,
            "stop_loss": sl,
            "target": tgt,
            "win_rate": win_rate,
            "avg_return": avg_return,
            "total_return": total_return
        })

    return pd.DataFrame(results).sort_values(by="total_return", ascending=False)