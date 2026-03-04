"""Send the HTML job report via Gmail using SMTP with an App Password."""

import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config

REPORT_PATH = os.path.join("output", "report.html")


def _build_message(sender: str, recipient: str, subject: str, html_body: str) -> MIMEMultipart:
    """Construct a MIME email with an HTML body."""
    msg = MIMEMultipart("alternative")
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    return msg


def send_via_smtp(
    sender: str,
    app_password: str,
    recipient: str,
    subject: str,
    html_body: str,
) -> None:
    """Send email using Gmail SMTP with an App Password."""
    msg = _build_message(sender, recipient, subject, html_body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, app_password)
        smtp.sendmail(sender, recipient, msg.as_string())

    print(f"[email_sender] Email sent to {recipient} via SMTP")


def send_email(
    report_path: str = REPORT_PATH,
    subject: str = config.EMAIL_SUBJECT,
) -> None:
    """Read configuration and send the HTML report via Gmail.

    Settings are read from config.py (which itself falls back to environment
    variables).  Required settings:
        GMAIL_SENDER     – sender Gmail address (e.g. you@gmail.com)
        GMAIL_APP_PASS   – Gmail App Password (16-char, no spaces)
        GMAIL_RECIPIENT  – recipient email address

    Optional:
        EMAIL_SUBJECT    – overrides the default subject line
    """
    sender = config.GMAIL_SENDER
    app_password = config.GMAIL_APP_PASS
    recipient = config.GMAIL_RECIPIENT

    if not sender:
        raise EnvironmentError(
            "GMAIL_SENDER is not set. Add it to config.py or export it as an environment variable."
        )
    if not app_password:
        raise EnvironmentError(
            "GMAIL_APP_PASS is not set. Add it to config.py or export it as an environment variable."
        )
    if not recipient:
        raise EnvironmentError(
            "GMAIL_RECIPIENT is not set. Add it to config.py or export it as an environment variable."
        )

    if not os.path.exists(report_path):
        raise FileNotFoundError(f"Report file not found: {report_path}")

    with open(report_path, encoding="utf-8") as fh:
        html_body = fh.read()

    send_via_smtp(sender, app_password, recipient, subject, html_body)


if __name__ == "__main__":
    try:
        send_email()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
