# =========================================
# FILE: utils/cache_fetcher.py
# =========================================

import pandas as pd
import os

# =========================================
# OHLC CACHE FETCHER
# =========================================

def get_cached_ohlc(ticker):

    try:

        file_path = (
            f"data/cache/ohlc/{ticker}.csv"
        )

        if not os.path.exists(file_path):

            print(f"❌ Cache Missing: {ticker}")

            return pd.DataFrame()

        df = pd.read_csv(file_path)

        if df.empty:

            print(f"❌ Empty Cache: {ticker}")

            return pd.DataFrame()

        return df

    except Exception as e:

        print(f"❌ Cache Error {ticker}: {e}")

        return pd.DataFrame()


# =========================================
# FUNDAMENTAL CACHE FETCHER
# =========================================

def get_fundamental_cache():

    try:

        file_path = (
            "data/cache/fundamentals/fundamentals.csv"
        )

        df = pd.read_csv(file_path)

        return df

    except Exception as e:

        print(f"❌ Fundamental Cache Error: {e}")

        return pd.DataFrame()
