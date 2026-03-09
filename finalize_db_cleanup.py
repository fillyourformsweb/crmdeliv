
import sqlite3
import os

def cleanup_db():
    db_path = os.path.join('instance', 'crm_delivery.db')
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tables_to_clean = ['default_state_prices', 'client_state_prices', 'normal_client_state_prices']
    
    for table in tables_to_clean:
        print(f"Cleaning table: {table}")
        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'price_750gm' in column_names:
            print(f"  Removing price_750gm from {table}...")
            
            # 1. Get current schema to recreate correctly (minus 750g)
            new_columns = [col for col in column_names if col != 'price_750gm']
            new_columns_str = ", ".join(new_columns)
            
            # Temporary table approach for maximum compatibility
            cursor.execute(f"CREATE TABLE {table}_new AS SELECT {new_columns_str} FROM {table}")
            cursor.execute(f"DROP TABLE {table}")
            cursor.execute(f"ALTER TABLE {table}_new RENAME TO {table}")
            print(f"  Successfully cleaned {table}")
        else:
            print(f"  price_750gm not found in {table}, skipping.")

    conn.commit()
    conn.close()
    print("Database cleanup completed successfully.")

if __name__ == "__main__":
    cleanup_db()
