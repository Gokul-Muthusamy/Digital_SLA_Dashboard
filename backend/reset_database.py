import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "database.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("DELETE FROM tickets")
cursor.execute("DELETE FROM alerts")
cursor.execute("DELETE FROM action_log")

cursor.execute("DELETE FROM sqlite_sequence WHERE name='tickets'")
cursor.execute("DELETE FROM sqlite_sequence WHERE name='alerts'")
cursor.execute("DELETE FROM sqlite_sequence WHERE name='action_log'")

conn.commit()
conn.close()

print("All tickets, alerts, and action logs cleared. IDs reset successfully.")
