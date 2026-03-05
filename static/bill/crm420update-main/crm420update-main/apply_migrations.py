import sqlite3
import os

def migrate():
    db_path = os.path.join('instance', 'crm_delivery.db')
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Add columns to 'clients' table
    client_columns = [
        ('alt_phone', 'TEXT'),
        ('alt_email', 'TEXT'),
        ('alt_address', 'TEXT'),
        ('vill_pattern', 'TEXT')
    ]

    for col_name, col_type in client_columns:
        try:
            cursor.execute(f"ALTER TABLE clients ADD COLUMN {col_name} {col_type}")
            print(f"Added column {col_name} to clients table.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"Column {col_name} already exists in clients table.")
            else:
                print(f"Error adding column {col_name} to clients: {e}")

    # Add columns to 'orders' table
    order_columns = [
        ('sender_address_id', 'INTEGER'),
        ('receiver_id', 'INTEGER'),
        ('receipt_type', 'TEXT DEFAULT "standard"'),
        ('assignment_id', 'INTEGER')
    ]

    for col_name, col_type in order_columns:
        try:
            cursor.execute(f"ALTER TABLE orders ADD COLUMN {col_name} {col_type}")
            print(f"Added column {col_name} to orders table.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"Column {col_name} already exists in orders table.")
            else:
                print(f"Error adding column {col_name} to orders: {e}")

    # Create 'staff_receipt_assignments' table
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS staff_receipt_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                branch_id INTEGER NOT NULL,
                prefix TEXT,
                base_number TEXT NOT NULL,
                current_sequence INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME,
                assigned_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (branch_id) REFERENCES branches (id),
                FOREIGN KEY (assigned_by) REFERENCES users (id)
            )
        ''')
        print("Created table staff_receipt_assignments.")
    except sqlite3.OperationalError as e:
        print(f"Error creating table staff_receipt_assignments: {e}")

    # Add columns to 'receivers' table
    receiver_columns = [
        ('city', 'TEXT'),
        ('state', 'TEXT'),
        ('pincode', 'TEXT')
    ]

    for col_name, col_type in receiver_columns:
        try:
            cursor.execute(f"ALTER TABLE receivers ADD COLUMN {col_name} {col_type}")
            print(f"Added column {col_name} to receivers table.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"Column {col_name} already exists in receivers table.")
            else:
                print(f"Error adding column {col_name} to receivers: {e}")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
