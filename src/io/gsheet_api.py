import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.config import GSheetConfig


class GSheetAPI:
    def __init__(self):
        self.creds = None
        token_file = os.path.join(GSheetConfig.CREDENTIALS_PATH, "token.json")

        # Load credentials from token.json
        if os.path.exists(token_file):
            self.creds = Credentials.from_authorized_user_file(
                token_file, GSheetConfig.SCOPES
            )

        # If no valid credentials are found, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
                # Save the refreshed credentials
                with open(token_file, "w") as token:
                    token.write(self.creds.to_json())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    os.path.join(GSheetConfig.CREDENTIALS_PATH, "credentials.json"),
                    GSheetConfig.SCOPES,
                )
                self.creds = flow.run_local_server(port=0)

                # Save the credentials for future use
                with open(token_file, "w") as token:
                    token.write(self.creds.to_json())

    def load_cells(self, spreadsheet_id, spreadsheet_range):

        try:
            service = build("sheets", "v4", credentials=self.creds)

            # Call the Sheets API
            sheet = service.spreadsheets()
            result = (
                sheet.values()
                .get(spreadsheetId=spreadsheet_id, range=spreadsheet_range)
                .execute()
            )
            table = result.get("values", [])

        except HttpError as err:
            raise HttpError(err)

        if not table:
            raise ValueError("No data found.")

        return table
