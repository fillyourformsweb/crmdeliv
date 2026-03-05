import sqlite3
import os

def migrate_branch_gst():
    # Use the path from config.py
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'instance', 'crm_delivery.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    print(f"Connecting to database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Add gst_number column to 'branches' table
    try:
        cursor.execute("ALTER TABLE branches ADD COLUMN gst_number TEXT")
        print("Successfully added 'gst_number' column to 'branches' table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'gst_number' already exists in 'branches' table.")
        else:
            print(f"Error adding column 'gst_number' to 'branches': {e}")

    conn.commit()
    conn.close()
    print("Migration finished.")

if __name__ == "__main__":
    migrate_branch_gst()
