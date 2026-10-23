# Lab Meeting Manager

Repository to automatically notify team members about the agenda of the next weekly group meeting, based on a shared Google Sheet. Supports notification via Email and Matrix chat, and can create a Google Slides deck for each meeting.

The meeting manager is built around a shared Google Docs spreadsheet, where team members enter the talks they (or their students) plan. The meeting manager then sends an agenda message via the specified channels to the given recipients at a specified time, for example, every Monday. It can handle multiple meetings in one week. A sample spreadsheet that works without adjustments can be provided upon request. If the document structure is changed (e.g., what is in which row or column), the corresponding code must be updated accordingly.

## Requirements:
- requirements.txt
- Google Sheet and API access (see [Instructions](https://developers.google.com/sheets/api/quickstart/python)).
- For email notification: An email account (SMTP server, username, etc.)
- For Matrix notification:
    - A Matrix account (access token, room ID, etc.). Create via [Element](https://app.element.io)
    - Install [matrix-notifier](https://github.com/Mo-Sc/matrix-notifier)

## Setup

The configuration is mainly done via `config/config.py`, which is not tracked by git. Create it from the template with `cp config/config.example.py config/config.py` and fill in your values. For a detailed description of the parameters, check the file.
- **NotificationsConfig**: General configurations, like which channels to use and which week's agenda to compile.
- **SMTPConfig**: Configuration of the email server.
- **GSheetConfig**: Configuration of the Google API access (credentials, scopes) and the spreadsheet.
- **SlidesConfig**: Optional creation of a slide deck for each upcoming meeting (see [Meeting Slides](#meeting-slides)).


### Credential Files

Each channel has a separate json file that can be used to store confidential data. The path to those files have to be set in the config file.

**Email:**
```
{"username": "user@email.com", "password": "password"}
```

**GSheet:**

The GSheet `credentials.json` file can be downloaded when creating the [API access](https://developers.google.com/sheets/api/quickstart/python). On the first run, the tool asks you to log in and stores the result in `token.json`.

**Matrix:**

For the Matrix credentials file, check the [matrix-notifier](https://github.com/Mo-Sc/matrix-notifier) repository.

### Meeting Slides
If `SlidesConfig.ENABLED` is set, the tool copies the template presentation into the shared folder for every upcoming, non-cancelled meeting, named `<NAME_PREFIX>-<YYYY-MM-DD>-<group>`. The agenda then links to this deck.

Requirements:
- The Google Drive API and Google Slides API are enabled in the Google Cloud project, and `https://www.googleapis.com/auth/drive` is in `GSheetConfig.SCOPES`.
- The template is a native Google Slides file and contains these placeholders: `{{date}}`, `{{group}}`, `{{staff}}`, `{{students}}` and `{{agenda}}`.
- A staff file `SlidesConfig.STAFF_FILE` (see `config/staff.example.json`). If `WikiConfig.ENABLED` is set, it is updated before each run from a GitLab wiki page with a `## Staff` and a `## Students` table, each with the columns `Name` and `Meeting Group` (`A` or `B`). People without a meeting group are skipped. If the update fails, the stored file is used.

Groups A and B alternate with every scheduled meeting, including cancelled ones. `SlidesConfig.ANCHOR_DATE` sets a meeting of group A.

### Spreadsheet
A template for the spreadsheet can be provided upon request.

![template](meeting_plan_template.png)

Recommended use:
- Share the document with all team members. Make white cells writable by the team, gray cells only by the admin.
- Each member can add meetings to the rows.
- When a meeting is canceled, check the canceled box. The meeting manager will then send a "meeting canceled" notification.
- Use Data Validation and conditional formatting to limit possible input (e.g., the "Associate" field only allows team members).
- Don't insert, modify, or delete rows or columns; otherwise, the corresponding variables in the code must be adapted.
- By default, the meeting will be scheduled with date, time, duration and location as given in the config section day at the top of the spreadsheet. This can be overwritten for an individual meeting by changing the values in the meeting's box.

## Run
After setting up the configuration, start the script by running the `main.py` file.

For a test send, set `MatrixConfig.TEST_CONFIG_FILE` to a separate Matrix credentials file and run `python main.py --test`. Slide decks are still created in the shared folder.

To check the agendas without sending anything, run `python main.py --dry-run`. The agendas are printed to the log.

Alternatively, you can set up a cron job to send out the meeting agenda periodically, e.g., every Friday at 5 PM:
- Open the crontab file: `crontab -e`
- Add the following line: `0 17 * * 5 /usr/bin/python3 /path/to/lab_meeting_manager/main.py`
- (`0 17 * * 5` means 5:00 PM every Friday.)

## Upcoming
Integration with Outlook, creating .ical files, etc.
