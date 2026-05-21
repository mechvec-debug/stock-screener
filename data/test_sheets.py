import gspread
import pandas as pd
from gspread_dataframe import set_with_dataframe

try:
    print("1. Looking for credentials.json...")
    gc = gspread.service_account(filename="google_credentials.json")
    print("✅ Authenticated successfully!")

    print("2. Trying to open the 'Stock_List' spreadsheet...")
    sh = gc.open("Stock_List")
    print("✅ Found the spreadsheet!")

    print("3. Trying to open the 'Fundamentals' tab...")
    worksheet = sh.worksheet("Fundamentals")
    print("✅ Found the tab!")

    print("4. Attempting to write a test row...")
    test_df = pd.DataFrame({
        "Ticker": ["TEST"], "Market Cap": [999], "Current Price": [150],
        "PE": [10], "ROE": [15], "ROCE": [15], "OPM": [20], "Sales Growth": [12],
        "Debt/Equity": [0.5], "EPS": [5], "Sector": ["Test"], "Industry": ["Test"], "Notes": ["SUCCESS"]
    })

    set_with_dataframe(worksheet, test_df, row=2, col=1, include_column_header=False)
    print("✅ SUCCESS! Check your Google Sheet row 2. It should say 'TEST'.")

except gspread.exceptions.SpreadsheetNotFound:
    print("\n❌ ERROR: Could not find a sheet named 'Stock_List'.")
    print("-> Did you share the sheet with the email inside your credentials.json file?")
    print(
        "-> Have you enabled the 'Google Drive API' in your Google Cloud Console? (gspread needs Drive API to search by name).")

except gspread.exceptions.WorksheetNotFound:
    print("\n❌ ERROR: Could not find a tab named 'Fundamentals'.")
    print("-> Check the spelling of the tab at the bottom of your Google Sheet.")

except FileNotFoundError:
    print("\n❌ ERROR: credentials.json is missing.")
    print(
        "-> Make sure the file is named exactly 'credentials.json' and is in the same folder you are running this from.")

except Exception as e:
    print(f"\n❌ UNKNOWN ERROR: {e}")