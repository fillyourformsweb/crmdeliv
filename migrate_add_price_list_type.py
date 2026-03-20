"""
Migration: Add price_list_type column to orders table
"""

import sqlite3
import os
import sys

def migrate():
    # Get the database path - it should be in the instance folder
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, 'instance', 'crm_delivery.db')
    
    print(f"Looking for database at: {db_path}")
    print(f"Database exists: {os.path.exists(db_path)}")
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        # Try alternate path
        db_path = os.path.join(current_dir, 'instance', 'test.db')
        print(f"Trying alternate path: {db_path}")
        print(f"Alternate exists: {os.path.exists(db_path)}")
        if not os.path.exists(db_path):
            return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(orders)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"Existing columns: {columns[:5]}...")  # Print first 5
        
        if 'price_list_type' not in columns:
            print("Adding price_list_type column to orders table...")
            cursor.execute("""
                ALTER TABLE orders 
                ADD COLUMN price_list_type VARCHAR(50) DEFAULT 'default'
            """)
            conn.commit()
            print("✓ Successfully added price_list_type column")
        else:
            print("✓ price_list_type column already exists")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    if migrate():
        print("\nMigration completed successfully!")
    else:
        print("\nMigration failed!")
