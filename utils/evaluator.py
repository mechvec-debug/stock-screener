def evaluate_strategy(row, prev_row):
    """Validates the 6 steps. Returns (Boolean, Reason)."""
    
    # 1. Trend Filter
    s1 = row['Close'] > row['EMA_200']
    if not s1: return False, "EMA 200 (Below Trend)"
    
    # 2. Pullback Zone
    s2 = (row['Low'] <= row['EMA_21'] and row['High'] >= row['EMA_21']) or \
         (row['Low'] <= row['EMA_50'] and row['High'] >= row['EMA_50'])
    if not s2: return False, "EMA Pullback (No 21/50 touch)"
    
    # 3. Confirmation Candle
    s3 = (row['Close'] > row['Open']) and (row['Close'] > prev_row['High'])
    if not s3: return False, "Candle (Not Bullish/Above Prev High)"
    
    # 4. RSI Filter
    s4 = (prev_row['RSI_14'] < 30) and (row['RSI_14'] > prev_row['RSI_14'])
    if not s4: return False, "RSI (Not rising from <30)"
    
    # 5. Volume Filter
    s5 = row['Volume'] > (1.5 * row['Vol_MA_20'])
    if not s5: return False, "Volume (< 1.5x MA)"
    
    # If it passes all checks
    return True, "PASSED"

# Keep your calculate_risk() function exactly as it is below this...



def calculate_risk(row):
    """Calculates entry and exit levels."""
    atr = row['ATR_14']
    return {
        "Entry": row['Close'],
        "SL": row['Close'] - (atr * 1.5),
        "TP1": row['Close'] + (atr * 1.5),
        "TP2": row['Close'] + (atr * 3.0)
    }
