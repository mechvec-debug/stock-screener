def evaluate_strategy(row, prev_row):
    """Validates the strategy steps. Returns (Boolean, Reason)."""
    
    # 1. Trend Filter
    s1 = row['Close'] > row['EMA_200']
    if not s1: return False, "FAILED: Below 200 EMA Trend"
    
    # 2. Pullback Zone
    s2 = (row['Low'] <= row['EMA_21'] and row['High'] >= row['EMA_21']) or \
         (row['Low'] <= row['EMA_50'] and row['High'] >= row['EMA_50'])
    if not s2: return False, "FAILED: No Pullback to 21/50 EMA"
    
    # --- STOCKS PAST THIS POINT ARE IN THE VALUE POCKET ---
    
    # 3. Confirmation Candle
    s3 = (row['Close'] > row['Open']) and (row['Close'] > prev_row['High'])
    if not s3: return False, "WATCHLIST: Waiting for Bullish Candle"
    
    # 4. RSI Filter (Uses the new 5-day memory we added earlier)
    s4 = (row['RSI_Reset'] > 0) and (row['RSI_14'] > prev_row['RSI_14'])
    if not s4: return False, "WATCHLIST: Waiting for RSI setup"
    
    # 5. Volume Filter
    s5 = row['Volume'] > (1.5 * row['Vol_MA_20'])
    if not s5: return False, "WATCHLIST: Waiting for Volume Spike"
    
    # If it passes all 5 checks
    return True, "PASSED"

def calculate_risk(row):
    """Calculates entry and exit levels based on ATR."""
    atr = row['ATR_14']
    return {
        "Entry": row['Close'],
        "SL": row['Close'] - (atr * 1.5),
        "TP1": row['Close'] + (atr * 1.5),
        "TP2": row['Close'] + (atr * 3.0)
    }
