import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
SELECT id, title, sla_hours, sla_status
FROM tickets
""")

rows = cursor.fetchall()

print("SLA Results:")
for row in rows:
    print(row)

conn.close()
