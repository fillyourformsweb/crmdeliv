#!/usr/bin/env python
"""
Migration Script: Add Air Shipping Mode with Cargo Weight Tiers to Pricing Tables
This script adds the shipping_mode column and air cargo weight tier pricing for SQLite
"""

from app import app, db
from models import DefaultStatePrice, ClientStatePrice, NormalClientStatePrice
import sqlalchemy as sa
from sqlalchemy import text

def migrate_add_shipping_mode():
    """Add shipping_mode column and air cargo weight tiers to all pricing tables"""
    with app.app_context():
        print("Starting migration: Add Air Shipping Mode with Cargo Weight Tiers...")
        
        try:
            inspector = sa.inspect(db.engine)
            
            # ============== MIGRATE DefaultStatePrice ==============
            print("\n1. Checking DefaultStatePrice table...")
            default_columns = {col['name'] for col in inspector.get_columns('default_state_prices')}
            
            cols_to_add = {
                'shipping_mode': 'VARCHAR(50) DEFAULT "standard" NOT NULL',
                'price_3_10kg': 'FLOAT DEFAULT 0',
                'price_10_25kg': 'FLOAT DEFAULT 0',
                'price_25_50kg': 'FLOAT DEFAULT 0',
                'price_50_100kg': 'FLOAT DEFAULT 0',
                'price_100plus_kg': 'FLOAT DEFAULT 0'
            }
            
            with db.engine.connect() as conn:
                for col_name, col_def in cols_to_add.items():
                    if col_name not in default_columns:
                        print(f"   - Adding {col_name} column...")
                        try:
                            conn.execute(text(f"ALTER TABLE default_state_prices ADD COLUMN {col_name} {col_def}"))
                            conn.commit()
                        except Exception as e:
                            print(f"     Warning: {str(e)}")
                
                # Try to add unique constraint (may fail if already exists)
                if 'shipping_mode' in default_columns or 'shipping_mode' in cols_to_add:
                    try:
                        conn.execute(text("""
                            CREATE UNIQUE INDEX IF NOT EXISTS uq_default_state_mode 
                            ON default_state_prices(state, shipping_mode)
                        """))
                        conn.commit()
                    except:
                        pass
            
            print("   ✓ DefaultStatePrice updated successfully")
            
            # ============== MIGRATE ClientStatePrice ==============
            print("\n2. Checking ClientStatePrice table...")
            client_columns = {col['name'] for col in inspector.get_columns('client_state_prices')}
            
            with db.engine.connect() as conn:
                for col_name, col_def in cols_to_add.items():
                    if col_name not in client_columns:
                        print(f"   - Adding {col_name} column...")
                        try:
                            conn.execute(text(f"ALTER TABLE client_state_prices ADD COLUMN {col_name} {col_def}"))
                            conn.commit()
                        except Exception as e:
                            print(f"     Warning: {str(e)}")
                
                # Try to add unique constraint
                if 'shipping_mode' in client_columns or 'shipping_mode' in cols_to_add:
                    try:
                        conn.execute(text("""
                            CREATE UNIQUE INDEX IF NOT EXISTS uq_client_state_mode 
                            ON client_state_prices(client_id, state, shipping_mode)
                        """))
                        conn.commit()
                    except:
                        pass
            
            print("   ✓ ClientStatePrice updated successfully")
            
            # ============== MIGRATE NormalClientStatePrice ==============
            print("\n3. Checking NormalClientStatePrice table...")
            normal_columns = {col['name'] for col in inspector.get_columns('normal_client_state_prices')}
            
            with db.engine.connect() as conn:
                for col_name, col_def in cols_to_add.items():
                    if col_name not in normal_columns:
                        print(f"   - Adding {col_name} column...")
                        try:
                            conn.execute(text(f"ALTER TABLE normal_client_state_prices ADD COLUMN {col_name} {col_def}"))
                            conn.commit()
                        except Exception as e:
                            print(f"     Warning: {str(e)}")
                
                # Try to add unique constraint
                if 'shipping_mode' in normal_columns or 'shipping_mode' in cols_to_add:
                    try:
                        conn.execute(text("""
                            CREATE UNIQUE INDEX IF NOT EXISTS uq_normal_state_mode 
                            ON normal_client_state_prices(state, shipping_mode)
                        """))
                        conn.commit()
                    except:
                        pass
            
            print("   ✓ NormalClientStatePrice updated successfully")
            
            print("\n✅ Migration completed successfully!")
            print("\nShipping modes now supported:")
            print("  - standard")
            print("  - prime")
            print("  - parcel")
            print("  - state_express")
            print("  - road_express")
            print("  - air (NEW) - with cargo weight tiers")
            
            print("\nAir Cargo Weight Tiers (for shipments > 3kg):")
            print("  - 3-10 kg")
            print("  - 10-25 kg")
            print("  - 25-50 kg")
            print("  - 50-100 kg")
            print("  - 100+ kg")
            
        except Exception as e:
            print(f"\n❌ Error during migration: {str(e)}")
            print("\nTroubleshooting:")
            print("1. Make sure the database is not locked")
            print("2. Check database file permissions")
            print("3. Verify you're in the correct directory")
            raise

if __name__ == '__main__':
    migrate_add_shipping_mode()
