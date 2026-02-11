import sqlite3

# Connect to database
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Insert sample users
users = [
    ("user1", "user123", "user"),
    ("support1", "support123", "support"),
    ("manager1", "manager123", "manager")
]

cursor.executemany(
    "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
    users
)

conn.commit()
conn.close()

print("Sample users inserted successfully")
