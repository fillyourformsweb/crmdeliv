import sqlite3
import os

def migrate():
    db_path = os.path.join('instance', 'crm_delivery.db')
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Add range_end to staff_receipt_assignments
    try:
        cursor.execute("ALTER TABLE staff_receipt_assignments ADD COLUMN range_end TEXT")
        print("Added column range_end to staff_receipt_assignments table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column range_end already exists in staff_receipt_assignments table.")
        else:
            print(f"Error adding column range_end: {e}")

    # Add range_end to receipt_settings
    try:
        cursor.execute("ALTER TABLE receipt_settings ADD COLUMN range_end TEXT")
        print("Added column range_end to receipt_settings table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column range_end already exists in receipt_settings table.")
        else:
            print(f"Error adding column range_end to receipt_settings: {e}")
    
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
