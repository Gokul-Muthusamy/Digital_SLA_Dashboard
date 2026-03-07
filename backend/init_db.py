import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "database.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT NOT NULL,
    email TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    created_time TEXT,
    resolved_time TEXT,
    sla_hours REAL,
    status TEXT,
    raised_by TEXT,
    sla_status TEXT,
    owner_username TEXT,
    next_action_text TEXT,
    next_action_due TEXT,
    warning_started_time TEXT,
    warning_ack_time TEXT,
    warning_auto_escalated INTEGER DEFAULT 0,
    breach_started_time TEXT,
    breach_action_time TEXT,
    breach_auto_escalated INTEGER DEFAULT 0,
    last_action_time TEXT,
    rca_required INTEGER DEFAULT 0,
    rca_completed INTEGER DEFAULT 0,
    priority_mail_sent INTEGER DEFAULT 0,
    warning_mail_sent INTEGER DEFAULT 0,
    breach_mail_sent INTEGER DEFAULT 0,
    manager_signoff INTEGER DEFAULT 0,
    manager_intervened INTEGER DEFAULT 0,
    priority_flag INTEGER DEFAULT 0,
    extension_requested_minutes INTEGER DEFAULT 0,
    extension_request_status TEXT DEFAULT 'NONE',
    extension_requested_by TEXT,
    extension_requested_time TEXT,
    extension_decision_time TEXT,
    extension_decision_note TEXT,
    extension_difficulty TEXT DEFAULT 'NONE',
    task_difficulty TEXT DEFAULT 'MODERATE',
    sla_extension_minutes INTEGER DEFAULT 60
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER,
    alert_type TEXT,
    alert_time TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS action_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    actor_username TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    action_type TEXT NOT NULL,
    note TEXT NOT NULL,
    action_time TEXT NOT NULL,
    next_step TEXT,
    escalated_to TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_username TEXT NOT NULL,
    sender_role TEXT NOT NULL,
    receiver_username TEXT NOT NULL,
    ticket_id INTEGER,
    message_text TEXT NOT NULL,
    sent_time TEXT NOT NULL,
    auto_generated INTEGER DEFAULT 0
)
""")

conn.commit()
conn.close()

print("Database initialized successfully")
