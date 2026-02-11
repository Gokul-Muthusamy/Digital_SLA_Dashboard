import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("SELECT id, title, status, raised_by FROM tickets")
rows = cursor.fetchall()

print("Tickets:")
for row in rows:
    print(row)

conn.close()

