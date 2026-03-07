import sqlite3

try:
    from .constants import DATABASE_PATH
except ImportError:
    from constants import DATABASE_PATH


def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_column(conn, table_name, column_name, ddl):
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
    if column_name not in existing:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {ddl}")


def ensure_schema():
    conn = get_db_connection()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        email TEXT
    )
    """)

    conn.execute("""
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

    conn.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER,
        alert_type TEXT,
        alert_time TEXT
    )
    """)

    conn.execute("""
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

    conn.execute("""
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

    ensure_column(conn, "users", "email", "email TEXT")
    ticket_columns = [
        ("raised_by", "raised_by TEXT"),
        ("sla_status", "sla_status TEXT"),
        ("owner_username", "owner_username TEXT"),
        ("next_action_text", "next_action_text TEXT"),
        ("next_action_due", "next_action_due TEXT"),
        ("warning_started_time", "warning_started_time TEXT"),
        ("warning_ack_time", "warning_ack_time TEXT"),
        ("warning_auto_escalated", "warning_auto_escalated INTEGER DEFAULT 0"),
        ("breach_started_time", "breach_started_time TEXT"),
        ("breach_action_time", "breach_action_time TEXT"),
        ("breach_auto_escalated", "breach_auto_escalated INTEGER DEFAULT 0"),
        ("last_action_time", "last_action_time TEXT"),
        ("rca_required", "rca_required INTEGER DEFAULT 0"),
        ("rca_completed", "rca_completed INTEGER DEFAULT 0"),
        ("priority_mail_sent", "priority_mail_sent INTEGER DEFAULT 0"),
        ("warning_mail_sent", "warning_mail_sent INTEGER DEFAULT 0"),
        ("breach_mail_sent", "breach_mail_sent INTEGER DEFAULT 0"),
        ("manager_signoff", "manager_signoff INTEGER DEFAULT 0"),
        ("manager_intervened", "manager_intervened INTEGER DEFAULT 0"),
        ("priority_flag", "priority_flag INTEGER DEFAULT 0"),
        ("extension_requested_minutes", "extension_requested_minutes INTEGER DEFAULT 0"),
        ("extension_request_status", "extension_request_status TEXT DEFAULT 'NONE'"),
        ("extension_requested_by", "extension_requested_by TEXT"),
        ("extension_requested_time", "extension_requested_time TEXT"),
        ("extension_decision_time", "extension_decision_time TEXT"),
        ("extension_decision_note", "extension_decision_note TEXT"),
        ("extension_difficulty", "extension_difficulty TEXT DEFAULT 'NONE'"),
        ("task_difficulty", "task_difficulty TEXT DEFAULT 'MODERATE'"),
        ("sla_extension_minutes", "sla_extension_minutes INTEGER DEFAULT 60"),
    ]
    for name, ddl in ticket_columns:
        ensure_column(conn, "tickets", name, ddl)

    conn.commit()
    conn.close()

