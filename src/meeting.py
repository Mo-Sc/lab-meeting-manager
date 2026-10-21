import pytz
from datetime import date, datetime, timedelta
from string import Template


from config.config import HTMLTemplates, NotificationsConfig, SlidesConfig

TZ = pytz.timezone("Europe/Berlin")


def get_week(kw=None, year=None):
    """
    Return the Monday and Sunday dates of a week.
    kw: None (current week), "next" (next week) or an int (ISO calendar week of `year`, default current year).
    """

    today = datetime.now().date()

    monday = today - timedelta(days=today.weekday())

    if kw == "next":
        monday += timedelta(weeks=1)
    elif isinstance(kw, int):
        monday = date.fromisocalendar(year or today.year, kw, 1)
    elif kw is not None:
        raise ValueError(f"Invalid week: {kw}")

    return monday, monday + timedelta(days=6)


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
        self.time_changed = False  # if time deviates from default

        # convert start time to datetime obj and add duration to get end time
        # self.end_time = (
        #     datetime.strptime(self.start_time, "%H:%M") + timedelta(minutes=DURATION)
        # ).strftime("%H:%M")

        self.location = cell_block[3][4]

        # set by main, since the presenting group depends on the previous meetings
        self.group = None
        self.slides_link = f"https://drive.google.com/drive/folders/{SlidesConfig.FOLDER_ID}"

        talks = []

        # extract talks from the cell block. Number of talks can vary
        for talk_row in cell_block[9:12]:
            if len(talk_row) > 1:
                talk = Talk(talk_row)
                talks.append(talk)

        self.talks = talks
        self.n_talks = len(talks)

        if self.n_talks > 0:
            # talks are prepended to the meeting, so talk time has to be subtracted from start time
            self.update_meeting_time(position="start")

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

            attendace_reminder = render_html_template(
                HTMLTemplates.ATTENDANCE_REMINDER_TEMPLATE, slides_link=self.slides_link
            )

            if self.n_talks == 0:
                talks_html += render_html_template(HTMLTemplates.NO_TALKS_TEMPLATE)
            else:
                talks_html += render_html_template(HTMLTemplates.TALK_HEADER_TEMPLATE)
                for talk in self.talks:
                    talks_html += render_html_template(
                        HTMLTemplates.TALK_TEMPLATE, **talk.__dict__
                    )

            # if not default time, add it to the title / subject
            if self.time_changed:
                title = f"⚠️ Time Changed - " + title
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

    def update_meeting_time(self, position="start"):
        """
        Updates the meeting time based on the number of talks and their time estimates.
        Sets self.time_changed to True if the time was updated or if it deviates from the default time given in the config.
        The total time of all talks is either added to the start or end time of the meeting, including configured breaks after each talk.
        position: "start" or "end" - which time to update
        """

        start_time_dt = datetime.strptime(self.start_time, "%H:%M")
        end_time_dt = datetime.strptime(self.end_time, "%H:%M")
        default_start_time_dt = datetime.strptime(
            self.online_config["default_time"], "%H:%M"
        )
        h, m, s = map(int, self.online_config["duration"].split(":"))
        default_duration_td = timedelta(hours=h, minutes=m, seconds=s)

        # start or end time deviates from default
        if (
            start_time_dt != default_start_time_dt
            or end_time_dt - start_time_dt != default_duration_td
        ):
            self.time_changed = True

        # calculate total talks time, including the configured break after each talk
        talk_durations = [
            talk.time_estimate + NotificationsConfig.BREAK_DURATION
            for talk in self.talks
            if talk.time_estimate
        ]
        total_talk_time = sum(talk_durations)

        if total_talk_time == 0:
            return  # no update needed

        if position == "start":
            # subtract total talk time from start time
            new_start_time_dt = start_time_dt - timedelta(minutes=total_talk_time)
            # convert back to string
            self.start_time = new_start_time_dt.strftime("%H:%M")

        elif position == "end":
            # add total talk time to end time
            new_end_time_dt = end_time_dt + timedelta(minutes=total_talk_time)
            # convert back to string
            self.end_time = new_end_time_dt.strftime("%H:%M")

        self.time_changed = True
