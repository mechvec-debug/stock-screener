import os
import sys
import logging
from pathlib import Path

import pandas as pd

# -------------------------------------------------------------------
# Project root setup
# -------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import config
from data.fetcher import fetch_data
from utils.indicators import calculate_ema_pullback_indicators
from utils.evaluator import evaluate_strategy, calculate_risk
from data.exporter import get_google_sheet, overwrite_sheet


# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def safe_round(value, digits=2, default=0):
    """Safely round numeric values."""
    try:
        if pd.isna(value):
            return default
        return round(float(value), digits)
    except Exception:
        return default


def safe_int(value, default=0):
    """Safely convert a value to int."""
    try:
        if pd.isna(value):
            return default
        return int(float(value))
    except Exception:
        return default


def load_stock_list(csv_path: Path):
    """
    Load stock symbols from CSV and convert them to NSE tickers.
    Example: RELIANCE -> RELIANCE.NS
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"stocks file not found: {csv_path}")

    df_symbols = pd.read_csv(csv_path, header=None)

    if df_symbols.empty:
        raise ValueError(f"{csv_path} is empty.")

    symbols = []
    seen = set()

    for raw in df_symbols.iloc[:, 0].dropna():
        sym = str(raw).strip()
        if not sym:
            continue

        ticker = sym if sym.endswith(".NS") else f"{sym}.NS"

        if ticker not in seen:
            seen.add(ticker)
            symbols.append(ticker)

    if not symbols:
        raise ValueError(f"No valid symbols found in {csv_path}")

    return symbols


def process_ticker(ticker: str, period: str, interval: str):
    """
    Fetch data, calculate indicators, run strategy, and return one output row.
    Returns None if the ticker cannot be processed safely.
    """
    df = fetch_data(ticker, period, interval)

    if df is None or df.empty:
        logging.warning("No price data returned for %s", ticker)
        return None

    df_indicators = calculate_ema_pullback_indicators(df.copy())

    if df_indicators is None or df_indicators.empty:
        logging.warning("No indicator data returned for %s", ticker)
        return None

    if len(df_indicators) < 2:
        logging.warning("Not enough rows for %s to compare current and previous candles", ticker)
        return None

    required_cols = [
        "Close", "Open", "High", "Low",
        "EMA_200", "EMA_50", "EMA_21",
        "RSI_14", "Volume"
    ]

    missing = [c for c in required_cols if c not in df_indicators.columns]
    if missing:
        raise KeyError(f"{ticker} is missing required columns: {missing}")

    current = df_indicators.iloc[-1]
    previous = df_indicators.iloc[-2]

    passed, reason = evaluate_strategy(current, previous)

    clean_ticker = ticker.replace(".NS", "")
    current_price = safe_round(current["Close"])

    if passed:
        risk_levels = calculate_risk(current)
        status_str = "PASSED"
        entry = safe_round(risk_levels.get("Entry"))
        sl = safe_round(risk_levels.get("SL"))
    else:
        status_str = str(reason) if reason else "FAILED"
        entry = 0
        sl = 0

    row = [
        clean_ticker,
        current_price,
        status_str,
        entry,
        sl,
        safe_round(current["EMA_200"]),
        safe_round(current["EMA_50"]),
        safe_round(current["EMA_21"]),
        safe_round(current["Open"]),
        safe_round(current["Close"]),
        safe_round(current["High"]),
        safe_round(current["Low"]),
        safe_round(current["RSI_14"]),
        safe_int(current["Volume"]),
    ]

    return row


def main():
    logging.info("Starting automated daily scan...")

    # -------------------------------------------------------------------
    # Read stock list
    # -------------------------------------------------------------------
    stocks_file = ROOT_DIR / "stocks.csv"

    try:
        stock_list = load_stock_list(stocks_file)
    except Exception as e:
        logging.error("Failed to load stock list: %s", e)
        return 1

    logging.info("Loaded %d symbols from %s", len(stock_list), stocks_file)

    # -------------------------------------------------------------------
    # Google Sheet connection
    # -------------------------------------------------------------------
    # Best practice: keep the sheet name in config.py
    sheet_name = getattr(config, "GOOGLE_SHEET_NAME", "Stock_List")

    sheet = get_google_sheet(sheet_name)

    if sheet is None:
        logging.error("Failed to connect to Google Sheet '%s'. Aborting scan.", sheet_name)
        return 1

    # -------------------------------------------------------------------
    # Process tickers
    # -------------------------------------------------------------------
    headers = [
        "Ticker", "Current Price", "Status", "Entry Price", "Stop Loss",
        "EMA200", "EMA50", "EMA21", "Open", "Close", "High", "Low", "RSI", "Volume"
    ]

    all_rows = []
    failed_count = 0

    period = getattr(config, "PERIOD", "1y")
    interval = getattr(config, "INTERVAL", "1d")

    for ticker in stock_list:
        try:
            row = process_ticker(ticker, period, interval)
            if row:
                all_rows.append(row)
                logging.info("Processed %s", ticker.replace(".NS", ""))
            else:
                failed_count += 1
        except Exception as e:
            failed_count += 1
            logging.exception("Error processing %s: %s", ticker, e)

    # -------------------------------------------------------------------
    # Upload results
    # -------------------------------------------------------------------
    if not all_rows:
        logging.warning("No valid rows generated. Sheet update skipped.")
        return 0

    try:
        overwrite_sheet(sheet, headers, all_rows)
    except Exception as e:
        logging.exception("Failed to write to Google Sheet: %s", e)
        return 1

    logging.info(
        "Automated daily scan complete. Success: %d | Failed: %d",
        len(all_rows),
        failed_count
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
