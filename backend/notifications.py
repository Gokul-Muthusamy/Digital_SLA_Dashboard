import os
import re
import smtplib
from email.mime.text import MIMEText

try:
    from .constants import DEFAULT_ALERT_RECIPIENTS
except ImportError:
    from constants import DEFAULT_ALERT_RECIPIENTS


def send_email_alert(subject, message, recipients=None):
    sender_email = os.getenv("SMTP_SENDER_EMAIL", "").strip()
    sender_password = os.getenv("SMTP_SENDER_APP_PASSWORD", "").strip()
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    to_emails = recipients or DEFAULT_ALERT_RECIPIENTS
    to_emails = [email for email in to_emails if email]
    if not to_emails or not sender_email or not sender_password:
        return

    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = ", ".join(to_emails)

    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print("Mail error:", e)


def is_valid_alert_email(email):
    if not email:
        return False
    email = email.strip()
    if email.lower().endswith(".local"):
        return False
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def get_role_emails(conn, role):
    rows = conn.execute("SELECT email FROM users WHERE role=?", (role,)).fetchall()
    unique = []
    for row in rows:
        email = (row["email"] or "").strip()
        if is_valid_alert_email(email) and email not in unique:
            unique.append(email)
    return unique


def get_alert_recipients(conn):
    recipients = []
    for role in ("support", "manager"):
        for email in get_role_emails(conn, role):
            if email not in recipients:
                recipients.append(email)
    if not recipients:
        recipients = DEFAULT_ALERT_RECIPIENTS
    return recipients


def merge_with_default_recipients(recipients):
    merged = []
    for email in DEFAULT_ALERT_RECIPIENTS + (recipients or []):
        e = (email or "").strip()
        if e and e not in merged:
            merged.append(e)
    return merged


def get_user_email(conn, username):
    row = conn.execute("SELECT email FROM users WHERE username=?", (username,)).fetchone()
    if not row:
        return None
    email = (row["email"] or "").strip()
    return email if is_valid_alert_email(email) else None


def get_user_role(conn, username):
    row = conn.execute("SELECT role FROM users WHERE username=?", (username,)).fetchone()
    return row["role"] if row else "user"


def get_role_usernames(conn, role):
    rows = conn.execute("SELECT username FROM users WHERE role=? ORDER BY username", (role,)).fetchall()
    return [row["username"] for row in rows]
