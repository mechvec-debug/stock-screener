import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import streamlit as st

def get_google_sheet(sheet_name, credentials_file='credentials.json'):
    """Authenticates and returns the Google Sheet object via Secrets or Local File."""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive"
    ]
    
    creds = None

    # 1. First, check if credentials.json exists (Local Machine OR GitHub Actions)
    if os.path.exists(credentials_file):
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
        except Exception as e:
            print(f"Error reading credentials.json: {e}")
            
    # 2. If no local file, try Streamlit Secrets (Streamlit Cloud Deployment)
    if creds is None:
        try:
            if "gcp_service_account" in st.secrets:
                creds_dict = dict(st.secrets["gcp_service_account"])
                creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        except Exception:
            # We catch and ignore the error Streamlit throws when running headlessly
            pass

    # 3. Abort if both methods failed
    if creds is None:
        print("Error: No credentials found in local directory or Streamlit Secrets.")
        return None

    try:
        # Authorize and connect
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
            formatted_row = [float(val) if isinstance(val, (int, float)) else str(val) for val in row_data]
            sheet.append_row(formatted_row)
        except Exception as e:
            print(f"Failed to write to sheet: {e}")

def overwrite_sheet(sheet, headers, all_rows):
    """Clears the sheet and writes a fresh batch of data."""
    if sheet:
        try:
            sheet.clear()
            sheet.append_rows([headers] + all_rows)
        except Exception as e:
            print(f"Failed to overwrite sheet: {e}")
