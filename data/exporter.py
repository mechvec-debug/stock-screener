# =========================================
# FILE: data/exporter.py
# =========================================

import os
import logging
import gspread

from oauth2client.service_account import ServiceAccountCredentials


# =========================================
# Logging
# =========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


# =========================================
# Google Sheet Connection
# =========================================

def get_google_sheet(
    spreadsheet_name="Stock_List",
    worksheet_name="tech_Screener",
    credentials_file="credentials.json"
):
    """
    Connect to Google Sheets and return worksheet object.

    Spreadsheet:
        Stock_List

    Worksheet:
        tech_Screener
    """

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive"
    ]

    try:

        # --------------------------------------------------
        # Verify credentials file exists
        # --------------------------------------------------
        if not os.path.exists(credentials_file):
            logging.error(
                "Google credentials file not found: %s",
                credentials_file
            )
            return None

        # --------------------------------------------------
        # Authenticate
        # --------------------------------------------------
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            credentials_file,
            scope
        )

        client = gspread.authorize(creds)

        # --------------------------------------------------
        # Open Spreadsheet
        # --------------------------------------------------
        spreadsheet = client.open(spreadsheet_name)

        logging.info(
            "Connected to spreadsheet: %s",
            spreadsheet_name
        )

        # --------------------------------------------------
        # Open Worksheet
        # --------------------------------------------------
        worksheet = spreadsheet.worksheet(worksheet_name)

        logging.info(
            "Connected to worksheet: %s",
            worksheet_name
        )

        return worksheet

    except gspread.SpreadsheetNotFound:
        logging.error(
            "Spreadsheet '%s' not found.",
            spreadsheet_name
        )
        logging.error(
            "Verify spreadsheet name and share it with the Google Service Account."
        )
        return None

    except gspread.WorksheetNotFound:
        logging.error(
            "Worksheet '%s' not found.",
            worksheet_name
        )
        return None

    except Exception as e:
        logging.exception(
            "Failed to connect to Google Sheets: %s",
            str(e)
        )
        return None


# =========================================
# Append Single Row
# =========================================

def append_to_sheet(sheet, row_data):
    """
    Append one row to Google Sheet.
    """

    if sheet is None:
        logging.error("Sheet object is None.")
        return False

    try:

        formatted_row = []

        for value in row_data:

            if value is None:
                formatted_row.append("")

            elif isinstance(value, (int, float)):
                formatted_row.append(value)

            else:
                formatted_row.append(str(value))

        sheet.append_row(
            formatted_row,
            value_input_option="USER_ENTERED"
        )

        return True

    except Exception as e:
        logging.exception(
            "Failed to append row: %s",
            str(e)
        )
        return False


# =========================================
# Overwrite Entire Sheet
# =========================================

def overwrite_sheet(sheet, headers, all_rows):
    """
    Clear worksheet and write fresh data.
    """

    if sheet is None:
        logging.error("Sheet object is None.")
        return False

    try:

        if not headers:
            logging.error("Headers cannot be empty.")
            return False

        data = [headers]

        if all_rows:
            data.extend(all_rows)

        logging.info(
            "Updating worksheet with %s rows...",
            len(all_rows)
        )

        # Faster than append_rows()
        sheet.clear()

        sheet.update(
            range_name="A1",
            values=data,
            value_input_option="USER_ENTERED"
        )

        logging.info(
            "Successfully updated Google Sheet."
        )

        return True

    except Exception as e:
        logging.exception(
            "Failed to overwrite sheet: %s",
            str(e)
        )
        return False


# =========================================
# Sheet Health Check
# =========================================

def test_google_connection():
    """
    Test Google Sheets connectivity.
    """

    sheet = get_google_sheet()

    if sheet:
        logging.info(
            "Google Sheets connection successful."
        )
        return True

    logging.error(
        "Google Sheets connection failed."
    )
    return False
