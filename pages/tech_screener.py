import streamlit as st
import pandas as pd
import os

# Import your modules based on the new folder structure
import config
from data.fetcher import fetch_data, fetch_market_cap
from utils.indicators import calculate_ema_pullback_indicators
from utils.evaluator import evaluate_strategy, calculate_risk
from data.exporter import get_google_sheet, append_to_sheet

# --- PAGE SETUP ---
st.set_page_config(page_title="Technical Screener", page_icon="📈")
st.title("📈 Technical Strategy Screener")

GOOGLE_SHEET_NAME = "My_Trading_Scanner_Results" # Update to your actual sheet name

def load_tickers_from_csv(filepath="stocks.csv"):
    """Reads tickers from the root stocks.csv file."""
    if not os.path.exists(filepath):
        st.error(f"Could not find '{filepath}'.")
        return []
    
    try:
        # Assuming the CSV has no header and symbols are in the first column
        # Adjust 'header=None' if your CSV has a title row like 'Symbol'
        df_symbols = pd.read_csv(filepath, header=None)
        
        formatted_tickers = []
        for symbol in df_symbols[0].dropna():
            clean_symbol = str(symbol).strip()
            if clean_symbol:
                formatted_tickers.append(f"{clean_symbol}.NS")
        return formatted_tickers
    except Exception as e:
        st.error(f"Error reading CSV: {e}")
        return []

# --- UI LAYOUT ---
st.write("Click below to run the EMA/RSI Pullback strategy against the stock list.")

if st.button("🚀 Run Full Scan", type="primary"):
    stock_list = load_tickers_from_csv()
    
    if not stock_list:
        st.warning("No tickers loaded to scan.")
        st.stop()

    sheet = get_google_sheet(GOOGLE_SHEET_NAME)
    if sheet:
        st.toast("Connected to Google Sheets!", icon="✅")
    else:
        st.toast("Could not connect to Google Sheets. Data will only show on screen.", icon="⚠️")

    # Create a visual progress bar and status text
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Store results to display in a Streamlit dataframe later
    scan_results = []
    total_stocks = len(stock_list)

    for i, ticker in enumerate(stock_list):
        status_text.text(f"Scanning {ticker}... ({i+1}/{total_stocks})")
        
        try:
            df = fetch_data(ticker, config.PERIOD, config.INTERVAL)
            market_cap = fetch_market_cap(ticker)
            df_indicators = calculate_ema_pullback_indicators(df)
            
            current = df_indicators.iloc[-1]
            previous = df_indicators.iloc[-2]
            
            is_passed = evaluate_strategy(current, previous)
            
            if is_passed:
                risk_levels = calculate_risk(current)
                status = "PASSED"
            else:
                status = "FAILED"
                risk_levels = {"Entry": 0, "SL": 0, "TP1": 0, "TP2": 0}

            # Prepare the row dictionary for Streamlit viewing
            row_dict = {
                "Ticker": ticker.replace(".NS", ""),
                "Market Cap": market_cap,
                "Close": round(current['Close'], 2),
                "EMA_200": round(current['EMA_200'], 2),
                "RSI_14": round(current['RSI_14'], 2),
                "Volume": int(current['Volume']),
                "Status": status,
                "Entry": round(risk_levels['Entry'], 2),
                "SL": round(risk_levels['SL'], 2)
            }
            scan_results.append(row_dict)

            # Prepare the list for Google Sheets export
            if sheet and is_passed: # Optional: Only push PASSED setups to the sheet to save space
                sheet_row = [
                    row_dict["Ticker"], row_dict["Market Cap"], row_dict["Close"],
                    round(current['EMA_200'], 2), round(current['EMA_50'], 2), round(current['EMA_21'], 2),
                    round(current['Open'], 2), round(current['Close'], 2), round(current['High'], 2), round(current['Low'], 2),
                    row_dict["RSI_14"], row_dict["Volume"],
                    f"PASSED (Entry: {row_dict['Entry']}, SL: {row_dict['SL']})"
                ]
                append_to_sheet(sheet, sheet_row)

        except Exception as e:
            st.toast(f"Error processing {ticker}: {e}")
        
        # Update progress bar
        progress_bar.progress((i + 1) / total_stocks)

    # --- FINAL OUTPUT ---
    status_text.text("Scan Complete!")
    
    if scan_results:
        results_df = pd.DataFrame(scan_results)
        
        # Display the results table on the page, highlighting PASSED rows
        st.subheader("Scan Results")
        st.dataframe(
            results_df.style.applymap(
                lambda x: "background-color: lightgreen; color: black" if x == "PASSED" else "", 
                subset=["Status"]
            ),
            use_container_width=True
        )
