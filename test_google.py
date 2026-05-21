from utils.google_sheet import (
    get_fundamental_data
)

df = get_fundamental_data()

print(df.head())