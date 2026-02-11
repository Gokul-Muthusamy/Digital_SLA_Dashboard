import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE tickets ADD COLUMN sla_status TEXT")
except:
    pass  # column already exists

conn.commit()
conn.close()

print("SLA status column added")
