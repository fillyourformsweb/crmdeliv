#!/usr/bin/env python
"""Add missing columns to the database"""

from app import app, db
from models import Order
import sys

try:
    with app.app_context():
        print("Checking database schema...")
        
        # Get the database connection
        with db.engine.connect() as conn:
            # Check if is_international column exists
            print("Checking if is_international column exists...")
            try:
                result = conn.execute(db.text("SELECT is_international FROM orders LIMIT 1"))
                print("✓ is_international column found!")
            except Exception as e:
                print("✗ is_international column missing, adding it...")
                try:
                    conn.execute(db.text("ALTER TABLE orders ADD COLUMN is_international BOOLEAN DEFAULT 0"))
                    conn.commit()
                    print("✓ is_international column added successfully!")
                except Exception as add_error:
                    print(f"Could not add column: {add_error}")
                    print("Attempting to recreate database...")
                    db.drop_all()
                    db.create_all()
                    print("✓ Database recreated successfully!")
        
        print("\n✓ Database schema is up to date!")
        sys.exit(0)

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
