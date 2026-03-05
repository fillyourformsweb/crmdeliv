import sqlite3
import os

def migrate():
    db_path = os.path.join('instance', 'crm.db')
    if not os.path.exists(db_path):
        # Try finding it in the current directory if not in instance
        db_path = 'crm.db'
        if not os.path.exists(db_path):
            # Check for any .db files in the directory
            db_files = [f for f in os.listdir('.') if f.endswith('.db')]
            if db_files:
                db_path = db_files[0]
            else:
                db_files = [f for f in os.listdir('instance') if f.endswith('.db')] if os.path.exists('instance') else []
                if db_files:
                    db_path = os.path.join('instance', db_files[0])
                else:
                    print("Could not find database file.")
                    return

    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(service)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'fee_pay_mode' not in columns:
            print("Adding 'fee_pay_mode' column to 'service' table...")
            cursor.execute("ALTER TABLE service ADD COLUMN fee_pay_mode VARCHAR(20) DEFAULT 'direct'")
            conn.commit()
            print("Successfully added 'fee_pay_mode' column.")
        else:
            print("'fee_pay_mode' column already exists.")
            
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
