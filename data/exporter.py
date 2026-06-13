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
    
    try:
        # 1. Cloud Deployment: Try fetching from Streamlit Secrets first
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            
        # 2. Local Machine / GitHub Actions: Fall back to local JSON file
        elif os.path.exists(credentials_file):
            creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
            
        else:
            print("Error: No credentials found in Streamlit Secrets or local directory.")
            return None

        # Authorize and connect
        client = gspread.authorize(creds)
        # Open the main file, then target the specific tab
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
