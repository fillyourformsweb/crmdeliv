import sqlite3
import os

def migrate():
    db_path = os.path.join('instance', 'crm_delivery.db')
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Add columns to clients table
    try:
        cursor.execute("ALTER TABLE clients ADD COLUMN landmark TEXT")
        cursor.execute("ALTER TABLE clients ADD COLUMN city TEXT")
        cursor.execute("ALTER TABLE clients ADD COLUMN state TEXT")
        cursor.execute("ALTER TABLE clients ADD COLUMN pincode TEXT")
        cursor.execute("ALTER TABLE clients ADD COLUMN alt_landmark TEXT")
        print("Updated clients table")
    except sqlite3.OperationalError as e:
        print(f"Clients table update: {e}")

    # Add columns to receivers table
    try:
        cursor.execute("ALTER TABLE receivers ADD COLUMN landmark TEXT")
        print("Updated receivers table")
    except sqlite3.OperationalError as e:
        print(f"Receivers table update: {e}")

    # Add columns to client_addresses table
    try:
        cursor.execute("ALTER TABLE client_addresses ADD COLUMN landmark TEXT")
        print("Updated client_addresses table")
    except sqlite3.OperationalError as e:
        print(f"Client_addresses table update: {e}")

    # Add columns to orders table
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN customer_landmark TEXT")
        cursor.execute("ALTER TABLE orders ADD COLUMN customer_city TEXT")
        cursor.execute("ALTER TABLE orders ADD COLUMN customer_state TEXT")
        cursor.execute("ALTER TABLE orders ADD COLUMN customer_pincode TEXT")
        cursor.execute("ALTER TABLE orders ADD COLUMN receiver_landmark TEXT")
        print("Updated orders table")
    except sqlite3.OperationalError as e:
        print(f"Orders table update: {e}")

    conn.commit()
    conn.close()
    print("Migration completed successfully")

if __name__ == "__main__":
    migrate()
