
import sqlite3

conn = sqlite3.connect('instance/tasks.db')
cursor = conn.cursor()

try:
    print("Adding 'unit' column to 'quickservice' table...")
    cursor.execute("ALTER TABLE quickservice ADD COLUMN unit VARCHAR(50) DEFAULT 'Per'")
    print("Column 'unit' added.")
except sqlite3.OperationalError as e:
    print(f"Error adding 'unit': {e}")

try:
    print("Adding 'description' column to 'quickservice' table...")
    cursor.execute("ALTER TABLE quickservice ADD COLUMN description TEXT")
    print("Column 'description' added.")
except sqlite3.OperationalError as e:
    print(f"Error adding 'description': {e}")

conn.commit()
conn.close()
print("Database schema update complete.")
