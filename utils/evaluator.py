def evaluate_strategy(row, prev_row):
    """Validates the 6 steps. Returns True if all pass, False otherwise."""

    # 1. Trend Filter
    s1 = row['Close'] > row['EMA_200']

    # 2. Pullback Zone
    s2 = (row['Low'] <= row['EMA_21'] <= row['High']) or \
         (row['Low'] <= row['EMA_50'] <= row['High'])

    # 3. Confirmation Candle
    s3 = (row['Close'] > row['Open']) and (row['Close'] > prev_row['High'])

    # 4. RSI Filter
    s4 = (prev_row['RSI_14'] < 30) and (row['RSI_14'] > prev_row['RSI_14'])

    # 5. Volume Filter
    s5 = row['Volume'] > (1.5 * row['Vol_MA_20'])

    # Print status for each criteria
    print(f"[Step 1] Trend: {'SUCCESS' if s1 else 'FAILURE'}")
    print(f"[Step 2] Pullback: {'SUCCESS' if s2 else 'FAILURE'}")
    print(f"[Step 3] Candle: {'SUCCESS' if s3 else 'FAILURE'}")
    print(f"[Step 4] RSI: {'SUCCESS' if s4 else 'FAILURE'}")
    print(f"[Step 5] Volume: {'SUCCESS' if s5 else 'FAILURE'}")

    return all([s1, s2, s3, s4, s5])


def calculate_risk(row):
    """Calculates entry and exit levels."""
    atr = row['ATR_14']
    return {
        "Entry": row['Close'],
        "SL": row['Close'] - (atr * 1.5),
        "TP1": row['Close'] + (atr * 1.5),
        "TP2": row['Close'] + (atr * 3.0)
    }
