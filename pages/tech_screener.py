import streamlit as st
import pandas as pd
import os
import config
from data.fetcher import fetch_data
from utils.indicators import calculate_ema_pullback_indicators
from utils.evaluator import evaluate_strategy, calculate_risk
from data.exporter import get_google_sheet, overwrite_sheet

st.set_page_config(page_title="Technical Screener", page_icon="📈")
st.title("📈 Technical Strategy Screener")

GOOGLE_SHEET_NAME = "My_Trading_Scanner_Results" # Update this

def load_tickers_from_csv(filepath="stocks.csv"):
    if not os.path.exists(filepath):
        return []
    df_symbols = pd.read_csv(filepath, header=None)
    return [f"{str(sym).strip()}.NS" for sym in df_symbols[0].dropna() if str(sym).strip()]

# --- 1. INSTANT LOAD FROM GOOGLE SHEETS ---
st.subheader("📊 Latest End-of-Day Results")
st.caption("Data is fetched from the latest 4:30 PM IST automated run.")

sheet = get_google_sheet(GOOGLE_SHEET_NAME)
if sheet:
    try:
        # Fetch all data from the sheet
        records = sheet.get_all_records()
        if records:
            df_all = pd.DataFrame(records)
            
            # Split the data into our two boxes based on the Status column
            df_passed = df_all[df_all['Status'] == "PASSED"]
            df_failed = df_all[df_all['Status'] != "PASSED"]
            
            st.markdown("### 🟢 Execution Ready")
            if not df_passed.empty:
                # Select only the 4 requested columns
                display_passed = df_passed[["Ticker", "Current Price", "Entry Price", "Stop Loss"]]
                st.dataframe(display_passed, use_container_width=True, hide_index=True)
            else:
                st.info("No stocks met all criteria for execution.")

            st.markdown("---")
            st.markdown("### 🔴 NO SIGNAL")
            if not df_failed.empty:
                # Select only the 3 requested columns
                display_failed = df_failed[["Ticker", "Current Price", "Status"]]
                st.dataframe(display_failed, use_container_width=True, hide_index=True)
            else:
                st.success("All stocks passed!")
        else:
            st.warning("Google Sheet is currently empty. Waiting for the first automated scan.")
    except Exception as e:
        st.error(f"Error reading Google Sheet: {e}")

st.markdown("---")

# --- 2. MANUAL LIVE RUN OVERRIDE ---
with st.expander("⚙️ Manual Intraday Scan"):
    st.write("Need an intraday update? Run a live scan below. This will overwrite the Google Sheet.")
    
    if st.button("🚀 Run Live Scan Now", type="primary"):
        stock_list = load_tickers_from_csv()
        if not stock_list:
            st.stop()

        progress_bar = st.progress(0)
        status_text = st.empty()
        total_stocks = len(stock_list)
        
        all_rows = []
        headers = ["Ticker", "Current Price", "Status", "Entry Price", "Stop Loss", 
                   "EMA200", "EMA50", "EMA21", "Open", "Close", "High", "Low", "RSI", "Volume"]

        for i, ticker in enumerate(stock_list):
            status_text.text(f"Scanning {ticker}... ({i+1}/{total_stocks})")
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
                    all_rows.append([clean_ticker, current_price, "PASSED", round(risk_levels['Entry'], 2), round(risk_levels['SL'], 2), 0,0,0,0,0,0,0,0,0]) # Padded for simplicity in UI override
                else:
                    all_rows.append([clean_ticker, current_price, reason, 0, 0, 0,0,0,0,0,0,0,0,0])

            except Exception as e:
                pass
            progress_bar.progress((i + 1) / total_stocks)

        # Overwrite sheet with manual run data
        overwrite_sheet(sheet, headers, all_rows)
        status_text.text("Live scan complete! Refresh the page to see updated tables.")
        st.rerun() # Instantly refreshes the page to show the new Google Sheet data
