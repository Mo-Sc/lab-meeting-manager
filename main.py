import argparse
import json
import logging

from matrix_notify.notify import notify as matrix_notify

from src.io.gitlab_wiki import load_people
from src.io.google_api import GoogleAPI
from src.io.email_sender import EmailSender
from src.meeting import Meeting, get_week, parse_config
from config.config import (
    GSheetConfig,
    HTMLTemplates,
    NotificationsConfig,
    MatrixConfig,
    SlidesConfig,
    WikiConfig,
)


def resolve_notification_settings(test_mode=False, dry_run=False):
    if dry_run:
        return [], None

    if not test_mode:
        return NotificationsConfig.CHANNELS, MatrixConfig.CONFIG_FILE

    if "matrix" not in NotificationsConfig.CHANNELS:
        raise ValueError("--test requires 'matrix' in NotificationsConfig.CHANNELS")

    return ["matrix"], MatrixConfig.TEST_CONFIG_FILE


def create_slides(google_api: GoogleAPI, meeting: Meeting, staff: list[dict]) -> str:
    """
    Copy the slide template for the meeting and fill in the date, the presenting group and the agenda.
    Returns the URL of the slides.
    """
    group = [person for person in staff if person["group"] == meeting.group]
    talks = [
        f"{talk.student}: {talk.title} ({talk.talk_type}, {talk.time_estimate} min)"
        for talk in meeting.talks
    ]

    return google_api.copy_presentation(
        template_id=SlidesConfig.TEMPLATE_ID,
        folder_id=SlidesConfig.FOLDER_ID,
        name=f"{SlidesConfig.NAME_PREFIX}-{meeting.date:%Y-%m-%d}-{meeting.group}",
        replacements={
            "date": f"{meeting.date:%B} {meeting.date.day}, {meeting.date.year}",
            "group": meeting.group,
            "staff": "\n".join(p["name"] for p in group if p["role"] == "staff"),
            "students": "\n".join(p["name"] for p in group if p["role"] == "student"),
            "agenda": "\n".join([f"Update Meeting Group {meeting.group}", *talks]),
        },
    )


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


def main(channels: list[str], matrix_config_file: str, with_slides: bool):

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    google_api = GoogleAPI()

    # load the table from the relevant columns in the google sheet
    table = google_api.load_cells(
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

    # all slides are created before sending, so a failure stops every agenda from going out with a broken link
    if with_slides:
        if WikiConfig.ENABLED:
            # the stored list stays as fallback
            try:
                people = load_people()
                with open(SlidesConfig.STAFF_FILE, "w") as f:
                    json.dump(people, f, indent=4, ensure_ascii=False)
            except Exception as e:
                logging.warning(
                    em := f"Could not update staff from the wiki, using the stored list: {e}"
                )
                matrix_notify(em, MatrixConfig.TEST_CONFIG_FILE)

        with open(SlidesConfig.STAFF_FILE) as f:
            staff = json.load(f)

        # groups alternate per scheduled meeting, so after a cancelled meeting the previous group presents again
        scheduled = sorted(
            (m for m in meetings if m.date >= SlidesConfig.ANCHOR_DATE),
            key=lambda m: m.date,
        )
        for i, meeting in enumerate(scheduled):
            meeting.group = "AB"[i % 2]

        for meeting in next_weeks_meetings:
            if not meeting.cancelled:
                meeting.slides_link = create_slides(google_api, meeting, staff)

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
    channels, matrix_config_file = resolve_notification_settings(
        args.test, args.dry_run
    )
    with_slides = SlidesConfig.ENABLED and not args.dry_run

    try:
        main(channels, matrix_config_file, with_slides)
    except Exception as e:
        logging.error(em := f"Error Sending Meeting Update: {e}")
        if not args.dry_run:
            matrix_notify(em, matrix_config_file)
        raise
