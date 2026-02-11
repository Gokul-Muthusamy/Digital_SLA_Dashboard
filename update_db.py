import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Add raised_by column if not exists
try:
    cursor.execute("ALTER TABLE tickets ADD COLUMN raised_by TEXT")
except:
    pass   # column already exists

conn.commit()
conn.close()

print("Database updated successfully")
