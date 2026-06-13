import os
import sys
import pandas as pd

# Ensure Python can find your custom modules from the root folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from data.fetcher import fetch_data
from utils.indicators import calculate_ema_pullback_indicators
from utils.evaluator import evaluate_strategy, calculate_risk
from data.exporter import get_google_sheet, overwrite_sheet

def main():
    print("Starting automated daily scan...")
    
    # Read tickers directly from the root stocks.csv
    filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stocks.csv")
    if not os.path.exists(filepath):
        print(f"Error: Could not find '{filepath}'.")
        return
        
    df_symbols = pd.read_csv(filepath, header=None)
    stock_list = [f"{str(sym).strip()}.NS" for sym in df_symbols[0].dropna() if str(sym).strip()]
    
    # Connect to the specific Google Sheet Name
    sheet = get_google_sheet("Stock_List")
    
    if not sheet:
        print("Failed to connect to Google Sheets. Aborting automated scan.")
        return

    all_rows = []
    headers = ["Ticker", "Current Price", "Status", "Entry Price", "Stop Loss", 
               "EMA200", "EMA50", "EMA21", "Open", "Close", "High", "Low", "RSI", "Volume"]

    for ticker in stock_list:
        try:
            df = fetch_data(ticker, config.PERIOD, config.INTERVAL)
            df_indicators = calculate_ema_pullback_indicators(df)
            
            current = df_indicators.iloc[-1]
            previous = df_indicators.iloc[-2]
            
            is_passed, reason = evaluate_strategy(current, previous)
            
            clean_ticker = ticker.replace(".NS", "")
            current_price = round(current['Close'], 2)
            
            if is_passed:
                risk_levels = calculate_risk(current)
                status_str = "PASSED"
                entry = round(risk_levels['Entry'], 2)
                sl = round(risk_levels['SL'], 2)
            else:
                status_str = reason
                entry = 0
                sl = 0

            # Append every stock (passed and failed) to the master list
            all_rows.append([
                clean_ticker, current_price, status_str, entry, sl,
                round(current['EMA_200'], 2), round(current['EMA_50'], 2), round(current['EMA_21'], 2),
                round(current['Open'], 2), round(current['Close'], 2), round(current['High'], 2), round(current['Low'], 2),
                round(current['RSI_14'], 2), int(current['Volume'])
            ])
            print(f"Processed {clean_ticker}")
            
        except Exception as e:
            print(f"Error processing {ticker}: {e}")

    # Push all data to Google Sheets at once
    overwrite_sheet(sheet, headers, all_rows)
    print("✅ Automated daily scan complete and pushed to Google Sheets.")

if __name__ == "__main__":
    main()
