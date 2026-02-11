import sqlite3

# Connect to database
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Delete all ticket records
cursor.execute("DELETE FROM tickets")

# Delete all alert records
cursor.execute("DELETE FROM alerts")

# Reset auto-increment counters
cursor.execute("DELETE FROM sqlite_sequence WHERE name='tickets'")
cursor.execute("DELETE FROM sqlite_sequence WHERE name='alerts'")

# Commit changes
conn.commit()

# Close connection
conn.close()

print("✅ All tickets and alerts cleared. IDs reset successfully.")
