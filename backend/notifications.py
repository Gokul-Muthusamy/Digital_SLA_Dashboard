import os
import re
import smtplib
import json
from email.mime.text import MIMEText
from urllib import request

try:
    from .constants import DEFAULT_ALERT_RECIPIENTS
except ImportError:
    from constants import DEFAULT_ALERT_RECIPIENTS


def send_telegram_alert(subject, message):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_ids = [
        chat_id.strip()
        for chat_id in os.getenv("TELEGRAM_CHAT_IDS", os.getenv("TELEGRAM_CHAT_ID", "")).split(",")
        if chat_id.strip()
    ]
    if not bot_token or not chat_ids:
        return

    text = f"{subject}\n\n{message}".strip()
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    for chat_id in chat_ids:
        payload = json.dumps({
            "chat_id": chat_id,
            "text": text[:4096],
        }).encode("utf-8")
        req = request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=10):
                pass
        except Exception as e:
            print("Telegram error:", e)


def send_email_alert(subject, message, recipients=None):
    send_telegram_alert(subject, message)

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
