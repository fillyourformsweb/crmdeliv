#!/usr/bin/env python
"""Quick migration to add air shipping columns"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db
from sqlalchemy import text

def add_columns():
    with app.app_context():
        try:
            print("Adding columns to database...")
            
            # List of (table_name, column_def) pairs
            tables_and_cols = [
                ('default_state_prices', [
                    ('shipping_mode', "VARCHAR(50) DEFAULT 'standard'"),
                    ('price_3_10kg', 'FLOAT DEFAULT 0'),
                    ('price_10_25kg', 'FLOAT DEFAULT 0'),
                    ('price_25_50kg', 'FLOAT DEFAULT 0'),
                    ('price_50_100kg', 'FLOAT DEFAULT 0'),
                    ('price_100plus_kg', 'FLOAT DEFAULT 0'),
                ]),
                ('client_state_prices', [
                    ('shipping_mode', "VARCHAR(50) DEFAULT 'standard'"),
                    ('price_3_10kg', 'FLOAT DEFAULT 0'),
                    ('price_10_25kg', 'FLOAT DEFAULT 0'),
                    ('price_25_50kg', 'FLOAT DEFAULT 0'),
                    ('price_50_100kg', 'FLOAT DEFAULT 0'),
                    ('price_100plus_kg', 'FLOAT DEFAULT 0'),
                ]),
                ('normal_client_state_prices', [
                    ('shipping_mode', "VARCHAR(50) DEFAULT 'standard'"),
                    ('price_3_10kg', 'FLOAT DEFAULT 0'),
                    ('price_10_25kg', 'FLOAT DEFAULT 0'),
                    ('price_25_50kg', 'FLOAT DEFAULT 0'),
                    ('price_50_100kg', 'FLOAT DEFAULT 0'),
                    ('price_100plus_kg', 'FLOAT DEFAULT 0'),
                ]),
            ]
            
            with db.engine.begin() as conn:
                for table_name, columns in tables_and_cols:
                    print(f"\nProcessing {table_name}...")
                    for col_name, col_type in columns:
                        sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"
                        try:
                            conn.execute(text(sql))
                            print(f"  ✓ Added {col_name}")
                        except Exception as e:
                            if "already exists" in str(e):
                                print(f"  - {col_name} already exists (skipping)")
                            else:
                                print(f"  ✗ Error: {str(e)[:100]}")
            
            print("\n✅ Migration completed!")
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    add_columns()
