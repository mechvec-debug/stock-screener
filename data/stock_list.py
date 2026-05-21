# data/stock_list.py

import pandas as pd

# Load CSV
df = pd.read_csv("stocks.csv")

# Take FIRST column automatically
symbols = df.iloc[:, 0]

# Convert to Yahoo format
NIFTY_50 = [

    str(symbol).strip()
    if str(symbol).strip().endswith(".NS")
    else f"{str(symbol).strip()}.NS"

    for symbol in symbols
]