import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Delete all ticket records
cursor.execute("DELETE FROM tickets")

conn.commit()
conn.close()

print("All tickets cleared successfully")
