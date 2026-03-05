"""
Quick database migration to add mobile app columns.
This script adds the new columns needed for the mobile app without affecting existing data.
"""
import sqlite3
import os

# Path to your database
db_path = os.path.join('instance', 'crm_delivery.db')

if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
    print("Please make sure you're running this from the project root directory.")
    exit(1)

print(f"Connecting to database: {db_path}")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    print("\n📦 Adding new columns to database...\n")
    
    # Add OTP columns to users table
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN otp_code VARCHAR(6)")
        print("✓ Added otp_code column to users table")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("- otp_code column already exists")
        else:
            raise
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN otp_expiry DATETIME")
        print("✓ Added otp_expiry column to users table")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("- otp_expiry column already exists")
        else:
            raise
    
    # Add verification columns to orders table
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN verified BOOLEAN DEFAULT 1")
        print("✓ Added verified column to orders table")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("- verified column already exists")
        else:
            raise
    
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN created_via VARCHAR(20) DEFAULT 'web'")
        print("✓ Added created_via column to orders table")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("- created_via column already exists")
        else:
            raise
    
    # Create notifications table
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                order_id INTEGER,
                message VARCHAR(500) NOT NULL,
                notification_type VARCHAR(50),
                is_read BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        """)
        print("✓ Created notifications table")
    except sqlite3.OperationalError as e:
        print(f"- Notifications table: {e}")
    
    conn.commit()
    print("\n✅ Migration completed successfully!")
    print("\nYou can now run: python app.py")
    
except Exception as e:
    print(f"\n❌ Error during migration: {e}")
    conn.rollback()
finally:
    conn.close()
