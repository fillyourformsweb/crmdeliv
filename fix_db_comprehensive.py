#!/usr/bin/env python
"""Fix all missing columns in the database by recreating the database"""

from app import app, db
import sys

try:
    with app.app_context():
        print("Checking database schema...")
        print("Recreating database schema to ensure all columns exist...\n")
        
        # Drop all tables
        print("Dropping existing tables...")
        db.drop_all()
        print("✓ Tables dropped\n")
        
        # Recreate all tables
        print("Creating all tables with updated schema...")
        db.create_all()
        print("✓ All tables created\n")
        
        print("✓ Database schema is now up to date!")
        print("All required columns are in place.")
        sys.exit(0)

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
