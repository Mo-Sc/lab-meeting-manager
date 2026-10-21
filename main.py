import argparse
import logging

from matrix_notify.notify import notify as matrix_notify

from src.io.gsheet_api import GSheetAPI
from src.io.email_sender import EmailSender
from src.meeting import Meeting, get_week, parse_config
from config.config import GSheetConfig, HTMLTemplates, NotificationsConfig, MatrixConfig


def resolve_notification_settings(test_mode=False, dry_run=False):
    if dry_run:
        return [], None

    if not test_mode:
        return NotificationsConfig.CHANNELS, MatrixConfig.CONFIG_FILE

    if "matrix" not in NotificationsConfig.CHANNELS:
        raise ValueError("--test requires 'matrix' in NotificationsConfig.CHANNELS")

    return ["matrix"], MatrixConfig.TEST_CONFIG_FILE


def publish_meeting(
    meeting: Meeting, channels: list[str], matrix_config_file: str
) -> list[str]:
    """
    Publish the meeting by compiling the meeting agenda
    and sending it via the specified channels.
    Returns the channels that failed.
    """

    logging.info(f"Publishing meeting {meeting.date}")

    # create html string with meeting agenda
    agenda_html, subject = meeting.compile_agenda()

    if not channels:
        logging.info(f"Dry run, not sending:\n{subject}\n{agenda_html}")

    failed = []

    if "matrix" in channels:
        # try sending matrix notification
        try:
            matrix_notify(agenda_html, matrix_config_file)
            logging.info("Matrix notification sent successfully!")
        except Exception as e:
            logging.error(f"Error sending matrix notification: {e}")
            failed.append("matrix")

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
            logging.error(f"Error sending email: {e}")
            failed.append("email")

    return failed


def main(channels: list[str], matrix_config_file: str):

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # load the table from the relevant columns in the google sheet
    table = GSheetAPI().load_cells(
        spreadsheet_id=GSheetConfig.SPREADSHEET_ID,
        spreadsheet_range=GSheetConfig.SPREADSHEET_RANGE,
    )

    # first 15 rows contain config information
    online_config = parse_config(table[:15])
    meeting_section_table = table[15:]

    meetings = []

    # parse the cell into meeting objects
    # each meeting block has 13 rows, and 3 empty rows between each block
    for i in range(0, len(meeting_section_table), 16):
        meeting_block = meeting_section_table[i : i + 13]
        meeting = Meeting(meeting_block, online_config=online_config)
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

    failed = [
        f"{meeting.date} ({channel})"
        for meeting in next_weeks_meetings
        for channel in publish_meeting(meeting, channels, matrix_config_file)
    ]
    if failed:
        raise RuntimeError(f"Failed to publish: {', '.join(failed)}")

    logging.info("All meetings published successfully!")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--test", action="store_true", help="send only to the test Matrix destination"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print the agendas without sending"
    )
    args = parser.parse_args()
    channels, matrix_config_file = resolve_notification_settings(args.test, args.dry_run)

    try:
        main(channels=channels, matrix_config_file=matrix_config_file)
    except Exception as e:
        logging.error(em := f"Error Sending Meeting Update: {e}")
        if not args.dry_run:
            matrix_notify(em, matrix_config_file)
        raise
