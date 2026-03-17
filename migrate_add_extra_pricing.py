"""
Migration script to add price_extra_per_kg column to pricing tables
Handles both fresh databases and existing ones
"""

import sys
from app import app, db
from sqlalchemy import text

def migrate():
    with app.app_context():
        try:
            connection = db.engine.raw_connection()
            cursor = connection.cursor()
            
            tables_to_migrate = [
                'default_state_prices',
                'client_state_prices',
                'normal_client_state_prices'
            ]
            
            for table_name in tables_to_migrate:
                print(f"\nMigrating {table_name}...")
                
                try:
                    # Try to add the column
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN price_extra_per_kg FLOAT DEFAULT 20")
                    connection.commit()
                    print(f"✓ Column added to {table_name}")
                except Exception as e:
                    if 'duplicate column' in str(e).lower():
                        print(f"✓ Column already exists in {table_name}")
                        connection.rollback()
                    else:
                        print(f"✗ Error with {table_name}: {str(e)}")
                        connection.rollback()
            
            cursor.close()
            connection.close()
            
            print("\n" + "="*50)
            print("✓ Migration completed successfully!")
            print("="*50)
            return True
            
        except Exception as e:
            print(f"\n✗ Migration failed: {str(e)}")
            print("\nTry running these SQL commands manually:")
            print("  sqlite3 instance/crm_delivery.db")
            print("  ALTER TABLE default_state_prices ADD COLUMN price_extra_per_kg FLOAT DEFAULT 20;")
            print("  ALTER TABLE client_state_prices ADD COLUMN price_extra_per_kg FLOAT DEFAULT 20;")
            print("  ALTER TABLE normal_client_state_prices ADD COLUMN price_extra_per_kg FLOAT DEFAULT 20;")
            return False

if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
