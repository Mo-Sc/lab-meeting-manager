class NotificationsConfig:
    CHANNELS = ["matrix", "email"]
    WEEK = "next"  # can be "next" (meaning next week), None (meaning this week) or an integer (the calendar week of the year)


class SMTPConfig:
    SERVER = "smtp.gmail.com"  # or any other SMTP server
    PORT = 465
    SENDER = "email@gmail.com"  # the email address from which the emails will be sent
    RECEPIENTS = [
        "person_a@gmail.com",
        "person_b@gmail.com",
    ]  # the email addresses of the recepients
    CREDENTIALS_PATH = "/path/to/lab_meeting_manager/config/email"  # the path to the folder that contains the credentials.json file


class GSheetConfig:
    CREDENTIALS_PATH = "/path/to/lab_meeting_manager/config/gsheet"  # the path to the folder that contains the credentials.json file
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets.readonly"
    ]  # the scopes required to access the Google Sheets API
    SPREADSHEET_ID = "<spreadsheet_id>"  # the ID of the Google Sheet
    SPREADSHEET_RANGE = "<sheet_name>!range"  # the range of the Google Sheet


class MatrixConfig:
    CONFIG_FILE = "/path/to/lab_meeting_manager/config/matrix/credentials.json"  # the path to the file that contains the Matrix credentials


class HTMLTemplates:  # HTML templates for the email notifications
    MEETING_TEMPLATE = """
        <body>
            <h2>$title</h2>
            <p></p>
            <p>Hi Lab,</p>
            <p>here is the agenda for the meeting on the $date:</p>

            <table>
            $talks
            </table>

            $notes

            $attendance_reminder

            <p>Have a nice weekend!</p>

            <hr>
            <p><i>Time: $start_time - $end_time, $date</i></p>
            <p><i>Place: $location and on <a href='zoomlink'>Zoom</a></i></p>
            <p><i>Slide Upload: <a href='uploadlink'>Drive</a></i></p>
            <hr>

        </body>
        """
    TALK_HEADER_TEMPLATE = """
        <tr><th>Student</th><th>Associate</th><th>Type</th><th>Time Estimate (Min)</th><th>Title</th><th>Comment</th></tr>
        """
    TALK_TEMPLATE = """
        <tr><td>$student</td><td>$associate</td><td>$talk_type</td><td>$time_estimate</td><td>$title</td><td>$comment</td></tr>
        """
    MEETING_CANCELLED_TEMPLATE = """
        <tr><th>Meeting Cancelled</th></tr>
        """
    NO_TALKS_TEMPLATE = """
        <tr><td>Regular Update Meeting (No Talks Scheduled)</td></tr>
        """
    TABLE_BORDER_FORMATTING = """
        <style>
            td, th {
                border: solid 2px lightgrey;
                padding: 5px;

            }

            table {
                border-collapse: collapse;
                border: 5px solid lightgrey;
            } 
        </style>
        """
    ATTENDANCE_REMINDER_TEMPLATE = """
        <p>Remember to present your recent work if it is your turn by preparing a slide for this week’s <a href='sharedslidelink'>Colloquium Presentation</a>.</p>
    """
