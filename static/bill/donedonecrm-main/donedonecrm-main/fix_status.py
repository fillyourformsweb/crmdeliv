
import sqlite3

conn = sqlite3.connect('instance/tasks.db')
cursor = conn.cursor()

try:
    print("Adding 'status' column to 'quickservice' table...")
    cursor.execute("ALTER TABLE quickservice ADD COLUMN status VARCHAR(20) DEFAULT 'active'")
    print("Column 'status' added.")
except sqlite3.OperationalError as e:
    print(f"Error adding 'status': {e}")

conn.commit()
conn.close()
print("Database schema update complete.")
