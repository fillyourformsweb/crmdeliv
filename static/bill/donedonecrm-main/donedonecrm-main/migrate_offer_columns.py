"""
Database migration script to add offer tracking columns to Task table
"""
import sqlite3
import os

# Path to database
db_path = 'instance/tasks.db'

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if columns already exist
    cursor.execute("PRAGMA table_info(task)")
    columns = [col[1] for col in cursor.fetchall()]
    
    print("Existing columns:", columns)
    
    # Add is_offer column if it doesn't exist
    if 'is_offer' not in columns:
        print("Adding is_offer column...")
        cursor.execute("ALTER TABLE task ADD COLUMN is_offer BOOLEAN DEFAULT 0")
        print("✓ Added is_offer column")
    else:
        print("✓ is_offer column already exists")
    
    # Add offer_reason column if it doesn't exist
    if 'offer_reason' not in columns:
        print("Adding offer_reason column...")
        cursor.execute("ALTER TABLE task ADD COLUMN offer_reason TEXT")
        print("✓ Added offer_reason column")
    else:
        print("✓ offer_reason column already exists")
    
    # Add offer_amount column if it doesn't exist
    if 'offer_amount' not in columns:
        print("Adding offer_amount column...")
        cursor.execute("ALTER TABLE task ADD COLUMN offer_amount REAL DEFAULT 0")
        print("✓ Added offer_amount column")
    else:
        print("✓ offer_amount column already exists")
    
    conn.commit()
    print("\n✅ Migration completed successfully!")
    
except sqlite3.Error as e:
    print(f"❌ Error during migration: {e}")
    if conn:
        conn.rollback()
finally:
    if conn:
        conn.close()
