# =========================================
# FILE: scheduler/update_ohlc.py
# =========================================

import os
import time
import pandas as pd
import yfinance as yf

from data.stock_list import NIFTY_50

# =========================================
# CACHE FOLDER
# =========================================

CACHE_PATH = "data/cache/ohlc"

os.makedirs(
    CACHE_PATH,
    exist_ok=True
)

# =========================================
# DOWNLOAD LOOP
# =========================================

success = 0
failed = 0

for ticker in NIFTY_50:

    try:

        print(f"\nDownloading: {ticker}")

        df = yf.download(

            ticker,

            period="1y",

            interval="1d",

            progress=False,

            auto_adjust=True,

            threads=False
        )

        if df.empty:

            print(f"❌ No Data: {ticker}")

            failed += 1

            continue

        save_path = (
            f"{CACHE_PATH}/{ticker}.csv"
        )

        df.to_csv(save_path)

        print(f"✅ Saved: {ticker}")

        success += 1

        time.sleep(1)

    except Exception as e:

        print(f"❌ Error: {ticker} → {e}")

        failed += 1

# =========================================
# FINAL SUMMARY
# =========================================

print("\n====================")
print("OHLC CACHE COMPLETE")
print("====================")

print(f"Success: {success}")
print(f"Failed: {failed}")
