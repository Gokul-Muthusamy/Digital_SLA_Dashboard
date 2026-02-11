import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("SELECT id, username, role FROM users")
rows = cursor.fetchall()

print("Users in database:")
for row in rows:
    print(row)

conn.close()
