import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

def get_google_sheet(sheet_name, credentials_file='credentials.json'):
    if not os.path.exists(credentials_file): return None
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
        return gspread.authorize(creds).open(sheet_name).worksheet("tech_screener")
    except: return None

def append_to_sheet(sheet, row_data):
    if sheet:
        try: sheet.append_row([float(val) if isinstance(val, (int, float)) else str(val) for val in row_data])
        except: pass

def overwrite_sheet(sheet, headers, all_rows):
    if sheet:
        try:
            sheet.clear()
            sheet.append_rows([headers] + all_rows)
        except: pass
