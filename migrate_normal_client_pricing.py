import sqlite3
import os

def migrate():
    db_path = os.path.join('instance', 'crm_delivery.db')
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create normal_client_state_prices table
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS normal_client_state_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                state VARCHAR(100) UNIQUE NOT NULL,
                price_100gm FLOAT DEFAULT 0,
                price_250gm FLOAT DEFAULT 0,
                price_500gm FLOAT DEFAULT 0,
                price_750gm FLOAT DEFAULT 0,
                price_1kg FLOAT DEFAULT 0,
                price_2kg FLOAT DEFAULT 0,
                price_3kg FLOAT DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("Created normal_client_state_prices table")
    except sqlite3.OperationalError as e:
        print(f"Error creating table: {e}")

    conn.commit()
    conn.close()
    print("Migration completed successfully")

if __name__ == "__main__":
    migrate()
