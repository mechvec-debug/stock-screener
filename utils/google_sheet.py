import gspread

from oauth2client.service_account import ServiceAccountCredentials

from gspread_dataframe import set_with_dataframe


SHEET_NAME = "Stock Screener"
WORKSHEET_NAME = "Screener1"


def connect_google_sheet():

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        "credentials.json",
        scope
    )

    client = gspread.authorize(credentials)

    sheet = client.open(SHEET_NAME)

    worksheet = sheet.worksheet(WORKSHEET_NAME)

    return worksheet



def upload_dataframe(df):

    try:

        worksheet = connect_google_sheet()

        worksheet.clear()

        set_with_dataframe(
            worksheet,
            df,
            include_index=False,
            resize=True
        )

        print("✅ Google Sheet Updated Successfully")

    except Exception as e:

        print(f"❌ Google Sheet Update Failed: {e}")
