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

# Make sure this exactly matches your Google file name
GOOGLE_SHEET_NAME = "Stock_List" 

def load_tickers_from_csv(filepath="stocks.csv"):
    if not os.path.exists(filepath):
        return []
    df_symbols = pd.read_csv(filepath, header=None)
    return [f"{str(sym).strip()}.NS" for sym in df_symbols[0].dropna() if str(sym).strip()]

# --- 1. INSTANT LOAD FROM GOOGLE SHEETS ---
st.subheader("📊 Latest End-of-Day Results")
st.caption("Data is fetched directly from your Stock_List Google Sheet.")

sheet = get_google_sheet(GOOGLE_SHEET_NAME)
if sheet:
    try:
        # Fetch all records from the sheet
        records = sheet.get_all_records()
        if records:
            df_all = pd.DataFrame(records)
            
            # Split the data into our two boxes
            df_passed = df_all[df_all['Status'] == "PASSED"]
            df_failed = df_all[df_all['Status'] != "PASSED"]
            
            # --- FIRST BOX: EXECUTION READY ---
            st.markdown("### 🟢 Execution Ready")
            if not df_passed.empty:
                # 4 Columns: Ticker name, Current Price, Entry Price, Stop Loss
                display_passed = df_passed[["Ticker", "Current Price", "Entry Price", "Stop Loss"]]
                st.dataframe(display_passed, use_container_width=True, hide_index=True)
            else:
                st.info("No stocks met all criteria for execution.")

            st.markdown("---")

            # --- SECOND BOX: NO SIGNAL ---
            st.markdown("### 🔴 NO SIGNAL")
            if not df_failed.empty:
                # 3 Columns: Ticker name, Current Price, Status (Failure reason)
                display_failed = df_failed[["Ticker", "Current Price", "Status"]]
                st.dataframe(display_failed, use_container_width=True, hide_index=True)
            else:
                st.success("Wow! All stocks passed!")
        else:
            st.warning("Google Sheet is currently empty. Run a manual scan below.")
    except Exception as e:
        st.error(f"Error reading Google Sheet: {e}")
else:
    st.error("Could not connect to Google Sheets.")

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
                    # Note: We pad the rest of the columns with 0s for speed during the intraday scan
                    all_rows.append([clean_ticker, current_price, "PASSED", round(risk_levels['Entry'], 2), round(risk_levels['SL'], 2), 0,0,0,0,0,0,0,0,0])
                else:
                    all_rows.append([clean_ticker, current_price, reason, 0, 0, 0,0,0,0,0,0,0,0,0])

            except Exception as e:
                pass
            progress_bar.progress((i + 1) / total_stocks)

        # Overwrite sheet with manual run data
        overwrite_sheet(sheet, headers, all_rows)
        status_text.text("Live scan complete! Refreshing page...")
        st.rerun() # Instantly reloads the page to display the newly written data
