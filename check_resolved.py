import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
SELECT id, title, status, created_time, resolved_time
FROM tickets
""")

rows = cursor.fetchall()

print("Tickets:")
for row in rows:
    print(row)

conn.close()
