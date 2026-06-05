import os
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr


def send_mail(subject, html):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    to_email = os.getenv("TO_EMAIL")

    if not all([smtp_host, smtp_user, smtp_pass, to_email]):
        return

    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = formataddr(("Market AI", smtp_user))
    msg["To"] = to_email

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
    except Exception:
        pass
