import streamlit as st
import pandas as pd
import os

# Import your modules based on the folder structure
import config
from data.fetcher import fetch_data
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
    
    # Store results in two separate lists
    execution_ready = []
    no_signal = []
    
    total_stocks = len(stock_list)

    for i, ticker in enumerate(stock_list):
        status_text.text(f"Scanning {ticker}... ({i+1}/{total_stocks})")
        
        try:
            df = fetch_data(ticker, config.PERIOD, config.INTERVAL)
            df_indicators = calculate_ema_pullback_indicators(df)
            
            current = df_indicators.iloc[-1]
            previous = df_indicators.iloc[-2]
            
            # Unpack the strategy evaluation
            is_passed, reason = evaluate_strategy(current, previous)
            
            clean_ticker = ticker.replace(".NS", "")
            current_price = round(current['Close'], 2)

            # --- SORT RESULTS INTO BOXES ---
            if is_passed:
                risk_levels = calculate_risk(current)
                
                # Format for Streamlit Box 1 (4 Columns)
                execution_ready.append({
                    "Ticker": clean_ticker,
                    "Current Price": current_price,
                    "Entry Price": round(risk_levels['Entry'], 2),
                    "Stop Loss": round(risk_levels['SL'], 2)
                })

                # Push ONLY passed trades to Google Sheets to keep it clean
                if sheet:
                    sheet_row = [
                        clean_ticker, "N/A", current_price,
                        round(current['EMA_200'], 2), round(current['EMA_50'], 2), round(current['EMA_21'], 2),
                        round(current['Open'], 2), round(current['Close'], 2), round(current['High'], 2), round(current['Low'], 2),
                        round(current['RSI_14'], 2), int(current['Volume']),
                        f"PASSED (Entry: {round(risk_levels['Entry'], 2)}, SL: {round(risk_levels['SL'], 2)})"
                    ]
                    append_to_sheet(sheet, sheet_row)
                    
            else:
                # Format for Streamlit Box 2 (3 Columns)
                no_signal.append({
                    "Ticker": clean_ticker,
                    "Current Price": current_price,
                    "Status": reason
                })

        except Exception as e:
            st.toast(f"Error processing {ticker}: {e}")
        
        # Update progress bar
        progress_bar.progress((i + 1) / total_stocks)

    # --- FINAL OUTPUT UI ---
    status_text.text("Scan Complete!")
    
    # Box 1: Execution Ready
    st.subheader("🟢 Execution Ready")
    if execution_ready:
        df_ready = pd.DataFrame(execution_ready)
        # hide_index=True removes the 0, 1, 2, 3 column on the far left
        st.dataframe(df_ready, use_container_width=True, hide_index=True) 
    else:
        st.info("No stocks met all criteria for execution today.")

    st.markdown("---") # Visual divider line

    # Box 2: No Signal
    st.subheader("🔴 NO SIGNAL")
    if no_signal:
        df_no_signal = pd.DataFrame(no_signal)
        st.dataframe(df_no_signal, use_container_width=True, hide_index=True)
    else:
        st.success("Wow! Every stock scanned passed the criteria!")
