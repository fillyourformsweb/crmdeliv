
import sqlite3
import os

db_path = os.path.join('instance', 'crm_delivery.db')
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    sys.exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print(f"Tables: {tables}")

for table in ['default_state_prices', 'client_state_prices', 'normal_client_state_prices']:
    print(f"\nSchema for {table}:")
    try:
        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
    except Exception as e:
        print(f"  Error: {e}")

conn.close()
