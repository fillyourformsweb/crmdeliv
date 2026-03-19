#!/usr/bin/env python
"""
Migration script to add International Booking columns to orders table
Run this once: python migrate_add_international.py
"""

import sqlite3
from pathlib import Path

def migrate():
    # Get database path
    db_path = Path(__file__).parent / 'instance' / 'crm_delivery.db'
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(orders)")
        columns = {row[1] for row in cursor.fetchall()}
        
        # List of new columns to add with their definitions
        new_columns = [
            ('is_international', 'BOOLEAN DEFAULT 0'),
            ('destination_country', 'VARCHAR(100)'),
            ('hs_code', 'VARCHAR(50)'),
            ('customs_description', 'TEXT'),
            ('product_value_usd', 'FLOAT'),
            ('invoice_currency', "VARCHAR(10) DEFAULT 'USD'"),
            ('international_notes', 'TEXT'),
            ('requires_signature_intl', 'BOOLEAN DEFAULT 0'),
        ]
        
        # Add missing columns
        added_count = 0
        for col_name, col_def in new_columns:
            if col_name not in columns:
                try:
                    cursor.execute(f'ALTER TABLE orders ADD COLUMN {col_name} {col_def}')
                    print(f"✓ Added column: {col_name}")
                    added_count += 1
                except sqlite3.OperationalError as e:
                    print(f"✗ Failed to add {col_name}: {e}")
            else:
                print(f"✓ Column {col_name} already exists")
        
        conn.commit()
        conn.close()
        
        if added_count > 0:
            print(f"\n✅ Migration successful! Added {added_count} columns.")
        else:
            print("\n✅ No new columns needed - database is already up to date.")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == '__main__':
    migrate()
