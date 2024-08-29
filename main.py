import logging

from matrix_notify.notify import notify as matrix_notify

from src.io.gsheet_api import GSheetAPI
from src.io.email_sender import EmailSender
from src.meeting import Meeting, get_week
from config.config import GSheetConfig, HTMLTemplates, NotificationsConfig, MatrixConfig


def publish_meeting(meeting: Meeting, channels=["matrix", "email"]):
    """
    Publish the meeting by compiling the meeting agenda
    and sending it via the specified channels
    """

    logging.info(f"Publishing meeting {meeting.date}")

    # create html string with meeting agenda
    agenda_html, subject = meeting.compile_agenda()

    # logging.info("Agenda Message:")
    # logging.info(agenda_html)

    if "matrix" in channels:
        # try sending matrix notification
        try:
            matrix_notify(agenda_html, MatrixConfig.CONFIG_FILE)
            logging.info("Matrix notification sent successfully!")
        except Exception as e:
            logging.info("Error sending matrix notification:", str(e))

    if "email" in channels:
        # try sending email
        try:
            # add email-specific formatting for html tables
            agenda_html_formatted = agenda_html + HTMLTemplates.TABLE_BORDER_FORMATTING
            # login to stmp server and send email
            email_sender = EmailSender()
            email_sender.send_email(
                subject=subject,
                message=agenda_html_formatted,
                msg_type="html",
            )
            email_sender.close_connection()
            logging.info("Email sent successfully!")
        except Exception as e:
            logging.info("Error sending email:", str(e))


def main():

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    gmail_api = GSheetAPI()

    # load the table from the relevant columns in the google sheet
    table = gmail_api.load_cells(
        spreadsheet_id=GSheetConfig.SPREADSHEET_ID,
        spreadsheet_range=GSheetConfig.SPREADSHEET_RANGE,
    )

    meetings = []

    # parse the cell into meeting objects
    # each meeting block has 5 rows, and 2 empty rows between each block
    for i in range(0, len(table), 7):
        meeting_block = table[i : i + 5]
        meeting = Meeting(meeting_block)
        meetings.append(meeting)

    # meetings.sort(key=lambda x: x.date)

    # get the date range for the next week
    next_monday, next_sunday = get_week(kw=NotificationsConfig.WEEK)

    logging.info(
        f"Compiling meeting agenda for the week from {next_monday} to {next_sunday}"
    )

    # find all meetings that happen in next week. Can be any day of the week
    next_weeks_meetings = [
        meeting
        for meeting in meetings
        if meeting.date >= next_monday and meeting.date <= next_sunday
    ]

    logging.info(f"Found {len(next_weeks_meetings)} meetings in specified week")

    # publish all meeting that happen in next week
    for meeting in next_weeks_meetings:
        publish_meeting(meeting, channels=NotificationsConfig.CHANNELS)

    logging.info("All meetings published successfully!")


if __name__ == "__main__":

    main()

    # try:
    #     main()
    # except Exception as e:
    #     logging.info(em := "Error Sending Meeting Update: " + str(e))
    #     matrix_notify(em, MatrixConfig.CONFIG_FILE)
