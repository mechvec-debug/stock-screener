import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os


def get_google_sheet(sheet_name, credentials_file='credentials.json'):
    """Authenticates and returns the Google Sheet object."""
    if not os.path.exists(credentials_file):
        print(f"Error: {credentials_file} not found. Cannot connect to Google Sheets.")
        return None

    # Define the scope of access
    scope = ["https://spreadsheets.google.com/feeds",
             'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file",
             "https://www.googleapis.com/auth/drive"]

    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
        client = gspread.authorize(creds)
        sheet = client.open(sheet_name).worksheet("tech_screener")
        return sheet
    except Exception as e:
        print(f"Failed to connect to Google Sheets: {e}")
        return None


def append_to_sheet(sheet, row_data):
    """Appends a single row of data to the Google Sheet."""
    if sheet:
        try:
            # gspread requires standard Python types, so we convert numpy floats/ints to standard formats
            formatted_row = [float(val) if isinstance(val, (int, float)) else str(val) for val in row_data]
            sheet.append_row(formatted_row)
        except Exception as e:
            print(f"Failed to write to sheet: {e}")
def overwrite_sheet(sheet, headers, all_rows):
    """Clears the sheet and writes a fresh batch of data."""
    if sheet:
        try:
            sheet.clear()
            # gspread handles bulk inserts much faster than row-by-row
            sheet.append_rows([headers] + all_rows)
        except Exception as e:
            print(f"Failed to overwrite sheet: {e}")
            
