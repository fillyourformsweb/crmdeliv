#!/usr/bin/env python3
"""
Migration script to add delivery-related fields to the orders table
Adds: reschedule_reason, reschedule_requested_date, reschedule_status, pickup_attempts, last_pickup_attempt
"""

import sqlite3
import sys
from datetime import datetime

def migrate_database():
    """Add delivery fields to orders table"""
    try:
        # Connect to the database
        conn = sqlite3.connect('instance/crm_delivery.db')
        cursor = conn.cursor()
        
        print("Connected to database successfully")
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(orders)")
        columns = [column[1] for column in cursor.fetchall()]
        
        columns_to_add = [
            ('reschedule_reason', 'VARCHAR(200)'),
            ('reschedule_requested_date', 'DATETIME'),
            ('reschedule_status', 'VARCHAR(50)'),
            ('pickup_attempts', 'INTEGER'),
            ('last_pickup_attempt', 'DATETIME')
        ]
        
        added_count = 0
        for col_name, col_type in columns_to_add:
            if col_name in columns:
                print(f"✓ Column '{col_name}' already exists")
            else:
                try:
                    alter_sql = f"ALTER TABLE orders ADD COLUMN {col_name} {col_type}"
                    cursor.execute(alter_sql)
                    conn.commit()
                    print(f"✓ Added column '{col_name}' ({col_type})")
                    added_count += 1
                except sqlite3.OperationalError as e:
                    print(f"✗ Error adding column '{col_name}': {e}")
                    return False
        
        # Verify the migration
        cursor.execute("PRAGMA table_info(orders)")
        current_columns = {column[1]: column[2] for column in cursor.fetchall()}
        
        print("\n--- Verification ---")
        for col_name, _ in columns_to_add:
            if col_name in current_columns:
                print(f"✓ {col_name}: {current_columns[col_name]}")
            else:
                print(f"✗ {col_name}: NOT FOUND")
        
        conn.close()
        
        if added_count > 0:
            print(f"\n✓ Migration completed successfully! Added {added_count} column(s)")
        else:
            print("\n✓ All columns already exist. No changes needed.")
        
        return True
        
    except sqlite3.Error as e:
        print(f"✗ Database error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

if __name__ == '__main__':
    success = migrate_database()
    sys.exit(0 if success else 1)
