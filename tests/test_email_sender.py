"""Unit tests for src/email_sender.py."""

import os
import tempfile
from email.mime.multipart import MIMEMultipart
from unittest.mock import MagicMock, patch

import pytest

from src.email_sender import _build_message, send_email


# ---------------------------------------------------------------------------
# _build_message
# ---------------------------------------------------------------------------

def test_build_message_headers():
    msg = _build_message(
        sender="sender@example.com",
        recipient="recipient@example.com",
        subject="Test Subject",
        html_body="<p>Hello</p>",
    )
    assert isinstance(msg, MIMEMultipart)
    assert msg["From"] == "sender@example.com"
    assert msg["To"] == "recipient@example.com"
    assert msg["Subject"] == "Test Subject"


def test_build_message_html_body():
    html_body = "<h1>Report</h1><p>Some jobs</p>"
    msg = _build_message(
        sender="a@example.com",
        recipient="b@example.com",
        subject="Daily Job Report",
        html_body=html_body,
    )
    payload = msg.get_payload()
    # MIMEMultipart has a list of parts
    assert isinstance(payload, list)
    # The HTML body should be in one of the parts
    body_str = payload[0].get_payload(decode=True).decode("utf-8")
    assert "<h1>Report</h1>" in body_str


# ---------------------------------------------------------------------------
# send_email – configuration validation
# ---------------------------------------------------------------------------

@patch("src.email_sender.config")
def test_send_email_missing_sender(mock_config):
    mock_config.GMAIL_SENDER = ""
    mock_config.GMAIL_APP_PASS = "pass"
    mock_config.GMAIL_RECIPIENT = "r@example.com"
    mock_config.EMAIL_SUBJECT = "Subject"

    with pytest.raises(EnvironmentError, match="GMAIL_SENDER"):
        send_email(report_path="/nonexistent/report.html")


@patch("src.email_sender.config")
def test_send_email_missing_app_pass(mock_config):
    mock_config.GMAIL_SENDER = "s@example.com"
    mock_config.GMAIL_APP_PASS = ""
    mock_config.GMAIL_RECIPIENT = "r@example.com"
    mock_config.EMAIL_SUBJECT = "Subject"

    with pytest.raises(EnvironmentError, match="GMAIL_APP_PASS"):
        send_email(report_path="/nonexistent/report.html")


@patch("src.email_sender.config")
def test_send_email_missing_recipient(mock_config):
    mock_config.GMAIL_SENDER = "s@example.com"
    mock_config.GMAIL_APP_PASS = "pass"
    mock_config.GMAIL_RECIPIENT = ""
    mock_config.EMAIL_SUBJECT = "Subject"

    with pytest.raises(EnvironmentError, match="GMAIL_RECIPIENT"):
        send_email(report_path="/nonexistent/report.html")


@patch("src.email_sender.config")
def test_send_email_missing_report_file(mock_config):
    mock_config.GMAIL_SENDER = "s@example.com"
    mock_config.GMAIL_APP_PASS = "pass"
    mock_config.GMAIL_RECIPIENT = "r@example.com"
    mock_config.EMAIL_SUBJECT = "Subject"

    with pytest.raises(FileNotFoundError):
        send_email(report_path="/nonexistent/report.html")


@patch("src.email_sender.send_via_smtp")
@patch("src.email_sender.config")
def test_send_email_calls_smtp(mock_config, mock_smtp):
    mock_config.GMAIL_SENDER = "s@example.com"
    mock_config.GMAIL_APP_PASS = "apppassword"
    mock_config.GMAIL_RECIPIENT = "r@example.com"
    mock_config.EMAIL_SUBJECT = "Daily Report"

    html_content = "<p>Jobs</p>"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as fh:
        fh.write(html_content)
        report_path = fh.name

    try:
        send_email(report_path=report_path, subject="Daily Report")
        mock_smtp.assert_called_once_with(
            "s@example.com",
            "apppassword",
            "r@example.com",
            "Daily Report",
            html_content,
        )
    finally:
        os.unlink(report_path)
