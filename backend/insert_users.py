import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "database.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

users = [
    ("user1", "user123", "user", "user1@sla.local"),
    ("support1", "support123", "support", "support1@sla.local"),
    ("manager1", "manager123", "manager", "manager1@sla.local")
]

for user in users:
    cursor.execute(
        """
        INSERT OR IGNORE INTO users (username, password, role, email)
        VALUES (?, ?, ?, ?)
        """,
        user,
    )

conn.commit()
conn.close()

print("Sample users inserted successfully")
