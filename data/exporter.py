import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

def get_google_sheet(sheet_name, credentials_file='credentials.json'):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive"
    ]
    
    creds = None

    # 1. Check if we are running in GitHub Actions or Local Machine
    if os.environ.get("GITHUB_ACTIONS") == "true" or os.path.exists(credentials_file):
        if not os.path.exists(credentials_file):
            print(f"FATAL ERROR: {credentials_file} is missing in GitHub Actions!")
            return None
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
        except Exception as e:
            print(f"FATAL ERROR reading JSON: {e}")
            return None

    # 2. Otherwise, assume we are on Streamlit Cloud
    else:
        try:
            import streamlit as st
            if "gcp_service_account" in st.secrets:
                creds_dict = dict(st.secrets["gcp_service_account"])
                creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        except Exception:
            pass

    if creds is None:
        print("Error: No valid credentials found.")
        return None

    try:
        client = gspread.authorize(creds)
        return client.open(sheet_name).worksheet("tech_screener")
    except Exception as e:
        print(f"Failed to connect to Google Sheets: {e}")
        return None

def append_to_sheet(sheet, row_data):
    if sheet:
        try:
            formatted_row = [float(val) if isinstance(val, (int, float)) else str(val) for val in row_data]
            sheet.append_row(formatted_row)
        except Exception as e:
            print(f"Failed to write to sheet: {e}")

def overwrite_sheet(sheet, headers, all_rows):
    if sheet:
        try:
            sheet.clear()
            sheet.append_rows([headers] + all_rows)
        except Exception as e:
            print(f"Failed to overwrite sheet: {e}")
