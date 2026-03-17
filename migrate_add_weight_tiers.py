#!/usr/bin/env python3
"""
Migration: Add weight tier pricing columns to normal_client_state_prices
Adds columns for: 3-10kg, 10-25kg, 25-50kg, 50-100kg, 100+kg
"""

from app import app, db
from sqlalchemy import text

def add_columns():
    with app.app_context():
        with db.engine.connect() as conn:
            columns_to_add = [
                ('price_3_10kg', 'REAL DEFAULT 0'),
                ('price_10_25kg', 'REAL DEFAULT 0'),
                ('price_25_50kg', 'REAL DEFAULT 0'),
                ('price_50_100kg', 'REAL DEFAULT 0'),
                ('price_100plus_kg', 'REAL DEFAULT 0')
            ]
            
            print("="*50)
            print("Adding weight tier columns to normal_client_state_prices...")
            print("="*50)
            
            for column_name, column_def in columns_to_add:
                try:
                    # Check if column already exists
                    check_query = text(f"PRAGMA table_info(normal_client_state_prices)")
                    result = conn.execute(check_query)
                    existing_columns = [row[1] for row in result]
                    
                    if column_name not in existing_columns:
                        alter_query = text(f"ALTER TABLE normal_client_state_prices ADD COLUMN {column_name} {column_def}")
                        conn.execute(alter_query)
                        conn.commit()
                        print(f"✓ Column {column_name} added to normal_client_state_prices")
                    else:
                        print(f"✓ Column {column_name} already exists in normal_client_state_prices")
                except Exception as e:
                    print(f"✗ Error adding {column_name}: {str(e)}")
            
            print("="*50)
            print("✓ Migration completed successfully!")
            print("="*50)

if __name__ == '__main__':
    add_columns()
