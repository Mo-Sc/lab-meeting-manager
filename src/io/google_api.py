import logging
import os

import httplib2
from google.auth.transport.requests import Request
from google_auth_httplib2 import AuthorizedHttp
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config.config import GSheetConfig


class GoogleAPI:
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
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    os.path.join(GSheetConfig.CREDENTIALS_PATH, "credentials.json"),
                    GSheetConfig.SCOPES,
                )
                # fixed port and no browser, so the login also works on a headless server via `ssh -L 8080:localhost:8080`
                self.creds = flow.run_local_server(port=8080, open_browser=False)

            # Save the credentials for future use
            with open(token_file, "w") as token:
                token.write(self.creds.to_json())

        # copying a presentation can take longer than the default timeout of 60 s
        self.http = AuthorizedHttp(self.creds, http=httplib2.Http(timeout=300))

    def load_cells(self, spreadsheet_id, spreadsheet_range):
        sheets = build("sheets", "v4", http=self.http, cache_discovery=False).spreadsheets()
        table = (
            sheets.values()
            .get(spreadsheetId=spreadsheet_id, range=spreadsheet_range)
            .execute()
            .get("values", [])
        )

        if not table:
            raise ValueError("No data found.")

        return table

    def copy_presentation(
        self, template_id: str, folder_id: str, name: str, replacements: dict[str, str]
    ) -> str:
        """
        Copy the template presentation into the folder and replace each {{key}} in it with its value.
        If a file with that name already exists in the folder, it is reused. Already replaced placeholders stay unchanged.
        Returns the URL of the presentation.
        """
        drive = build("drive", "v3", http=self.http, cache_discovery=False)
        existing = (
            drive.files()
            .list(
                q=f"name = '{name}' and '{folder_id}' in parents and trashed = false",
                fields="files(id)",
            )
            .execute()["files"]
        )

        if existing:
            logging.info(f"Slides {name} already exist, reusing them")
            file_id = existing[0]["id"]
        else:
            file_id = (
                drive.files()
                .copy(fileId=template_id, body={"name": name, "parents": [folder_id]})
                .execute()["id"]
            )

        # also applied to existing slides, in case an earlier run failed between copying and filling
        requests = [
            {
                "replaceAllText": {
                    "containsText": {"text": "{{" + key + "}}", "matchCase": True},
                    "replaceText": value,
                }
            }
            for key, value in replacements.items()
        ]
        build("slides", "v1", http=self.http, cache_discovery=False).presentations().batchUpdate(
            presentationId=file_id, body={"requests": requests}
        ).execute()

        return f"https://docs.google.com/presentation/d/{file_id}/edit"
