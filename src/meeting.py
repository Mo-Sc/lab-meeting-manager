import pytz
from datetime import datetime, timedelta
from string import Template


from config.config import HTMLTemplates

TZ = pytz.timezone("Europe/Berlin")


from datetime import datetime, timedelta


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


def parse_config(cfg_table):
    """
    Function to parse the configuration table from the Google Sheet.
    The first x rows of the table contain the configuration information.
    """
    cfg = {
        "instructions": cfg_table[3][0],
        "start_date": cfg_table[4][5],
        "interval": cfg_table[5][5],
        "default_time": cfg_table[6][5],
        "duration": cfg_table[7][5],
        "location_a": cfg_table[9][5],
        "location_b": cfg_table[10][5],
    }
    return cfg


class Talk:
    def __init__(self, talk_row):
        self.student = talk_row[0]
        self.associate = talk_row[1]
        self.talk_type = talk_row[2]
        self.time_estimate = int(talk_row[3]) if talk_row[3] else ""
        self.title = talk_row[4]
        self.comment = talk_row[5] if len(talk_row) > 5 else ""
        # self.internal_comment = (
        #     f"[INTERNAL] {talk_row[7]}" if len(talk_row) > 7 else ""
        # )  # not included in agenda, since its shared with students
        # self.comments = f"{self.comment}{'<br>' if self.comment and self.internal_comment else ''}{self.internal_comment}"


class Meeting:
    def __init__(self, cell_block, online_config=None):

        self.online_config = online_config

        self.date = TZ.localize(datetime.strptime(cell_block[0][0], "%d-%b-%Y")).date()

        self.cancelled = {"FALSE": False, "TRUE": True}[
            cell_block[2][1]
        ]  # convert string to boolean

        self.comment = cell_block[4][4] if len(cell_block[4]) > 4 else ""

        self.start_time = cell_block[3][1]
        self.end_time = cell_block[4][1]

        # convert start time to datetime obj and add duration to get end time
        # self.end_time = (
        #     datetime.strptime(self.start_time, "%H:%M") + timedelta(minutes=DURATION)
        # ).strftime("%H:%M")

        self.location = cell_block[3][4]

        talks = []

        # extract talks from the cell block. Number of talks can vary
        for talk_row in cell_block[9:12]:
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
        title = "Lab Meeting Agenda - " + self.date.strftime("%d. %B %Y")

        # create html block for talks section based on meeting status
        if self.cancelled:
            talks_html += render_html_template(HTMLTemplates.MEETING_CANCELLED_TEMPLATE)
            attendace_reminder = ""
            title += " - CANCELLED"
        else:

            # add location to title
            title += f" - {self.location.split(' ')[-1]} Edition"

            if self.n_talks == 0:
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
            if self.start_time != self.online_config["default_time"]:
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
            location=self.location,
            date=self.date.strftime("%d. %B %Y"),
        )
        return agenda_html, title
