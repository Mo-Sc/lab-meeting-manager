import json
import os
import smtplib
from email.mime.text import MIMEText

from config.config import SMTPConfig


class EmailSender:
    def __init__(self):
        """
        Load credentials from file, connect to smtp server and login
        """

        if os.path.exists(
            cred_file := os.path.join(SMTPConfig.CREDENTIALS_PATH, "credentials.json")
        ):
            with open(cred_file, "r") as f:
                creds = json.load(f)
                user = creds["username"]
                password = creds["password"]
        else:
            raise FileNotFoundError("Credentials file not found.")
        self.smtp_server = smtplib.SMTP_SSL(SMTPConfig.SERVER, SMTPConfig.PORT)
        self.smtp_server.login(user, password)

    def send_email(self, subject, message, msg_type="plain"):
        """
        Send an email to the recepients
        """

        msg = MIMEText(message, msg_type)
        msg["Subject"] = subject
        msg["From"] = SMTPConfig.SENDER
        msg["To"] = ", ".join(SMTPConfig.RECEPIENTS)

        self.smtp_server.sendmail(
            SMTPConfig.SENDER, SMTPConfig.RECEPIENTS, msg.as_string()
        )

    def close_connection(self):
        self.smtp_server.quit()
