import pytz
from datetime import datetime, timedelta
from string import Template


from config.config import HTMLTemplates

TZ = pytz.timezone("Europe/Berlin")


from datetime import datetime, timedelta

# todo: move to config
DEFAULT_TIME = "12:30"
DURATION = 90  # minutes


def get_week(kw=None, year=None):
    """
    Function to return datetime objects for the start (Monday) and end (Sunday) dates of a given week.
    If no argument is provided, the function returns the current week.
    If the argument is an integer, the function returns the start and end dates of the week in the given year.
    """

    today = datetime.now().date()

    if kw is None:
        current_day_of_week = today.weekday()
        # Calculate the current week's Monday
        current_monday = today - timedelta(days=current_day_of_week)
        current_sunday = current_monday + timedelta(days=6)
        return current_monday, current_sunday

    elif kw == "next":
        current_day_of_week = today.weekday()
        # Calculate the current week's Monday
        current_monday = today - timedelta(days=current_day_of_week)
        current_sunday = current_monday + timedelta(days=6)
        return current_monday + timedelta(weeks=1), current_sunday + timedelta(weeks=1)

    elif isinstance(kw, int):

        if year is None:
            year = datetime.now().year

        # Find the first day of the year
        first_day_of_year = datetime(year, 1, 1)
        # Calculate the first Monday of the year
        first_monday_of_year = first_day_of_year - timedelta(
            days=first_day_of_year.weekday()
        )
        # Calculate the start of the target week
        start_of_week = first_monday_of_year + timedelta(weeks=kw - 1)
        # Calculate the end of the target week
        end_of_week = start_of_week + timedelta(days=6)

        return start_of_week.date(), end_of_week.date()

    else:
        raise ValueError("Invalid argument for get_week function")


def render_html_template(template_str, **kwargs):
    template = Template(template_str)
    return template.substitute(**kwargs)


class Talk:
    def __init__(self, talk_row):
        self.student = talk_row[1]
        self.associate = talk_row[2]
        self.talk_type = talk_row[3]
        self.time_estimate = int(talk_row[4]) if talk_row[4] else ""
        self.title = talk_row[5]
        self.comment = talk_row[6] if len(talk_row) > 6 else ""
        self.internal_comment = (
            f"[INTERNAL] {talk_row[7]}" if len(talk_row) > 7 else ""
        )  # not included in agenda, since its shared with students
        self.comments = f"{self.comment}{'<br>' if self.comment and self.internal_comment else ''}{self.internal_comment}"


class Meeting:
    def __init__(self, cell_block):

        header = cell_block[0]
        self.date = TZ.localize(datetime.strptime(header[0], "%d-%b-%Y")).date()

        self.cancelled = {"FALSE": False, "TRUE": True}[
            header[3]
        ]  # convert string to boolean

        self.comment = header[5] if len(header) > 5 else ""
        # self.time = (
        #     cell_block[0][1] if len(cell_block[1]) > 0 else "15:30"
        # )  # default time for meeting is 15:30
        self.start_time = cell_block[0][1]
        # convert start time to datetime obj and add duration to get end time
        self.end_time = (
            datetime.strptime(self.start_time, "%H:%M") + timedelta(minutes=DURATION)
        ).strftime("%H:%M")

        talks = []

        # extract talks from the cell block. Number of talks can vary
        for talk_row in cell_block[2:5]:
            if len(talk_row) > 1:
                talk = Talk(talk_row)
                talks.append(talk)

        self.talks = talks
        self.n_talks = len(talks)

    def compile_agenda(self):
        """
        Fills in the html templates with the meeting data
        Creates a subject / title string
        """

        talks_html = ""
        # title = "Lab Meeting Agenda - " + self.date.strftime("%d. %B %Y")
        title = (
            "Lab Meeting Agenda - "
            + self.date.strftime("%d. %B %Y")
            # + " - Würzburg Edition"
        )

        # create html block for talks section based on meeting status
        if self.cancelled:
            talks_html += render_html_template(HTMLTemplates.MEETING_CANCELLED_TEMPLATE)
            attendace_reminder = ""
            title += " - CANCELLED"
        elif self.n_talks == 0:
            talks_html += render_html_template(HTMLTemplates.NO_TALKS_TEMPLATE)
            attendace_reminder = HTMLTemplates.ATTENDANCE_REMINDER_TEMPLATE
        else:
            talks_html += render_html_template(HTMLTemplates.TALK_HEADER_TEMPLATE)
            for talk in self.talks:
                talks_html += render_html_template(
                    HTMLTemplates.TALK_TEMPLATE, **talk.__dict__
                )
            attendace_reminder = HTMLTemplates.ATTENDANCE_REMINDER_TEMPLATE

        # if not default time, add it to the title / subject
        if not self.cancelled and self.start_time != DEFAULT_TIME:
            title = f"UPDATED TIME: {self.start_time} - " + title
            # title += f" - UPDATED TIME: {self.start_time}"

        # Embed talks block into the meeting template
        # TODO: The link to the google sheet should always point to the current weeks cell block!
        # (https://matrix-nio.readthedocs.io/en/latest/nio.html#nio.AsyncClient.update_room_topic)
        agenda_html = render_html_template(
            HTMLTemplates.MEETING_TEMPLATE,
            title=title,
            talks=talks_html,
            notes=f"<p><b>Notes: </b>{self.comment}</p> " if self.comment else "",
            attendance_reminder=attendace_reminder,
            start_time=self.start_time,
            end_time=self.end_time,
            date=self.date.strftime("%d. %B %Y"),
        )
        return agenda_html, title
