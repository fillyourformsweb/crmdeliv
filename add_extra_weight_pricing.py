"""
Migration script to add price_extra_per_kg column to pricing tables
for weights greater than 3kg
"""

from app import app, db
from models import DefaultStatePrice, ClientStatePrice, NormalClientStatePrice

def migrate():
    with app.app_context():
        try:
            # Check if column already exists
            inspector = db.inspect(db.engine)
            
            tables_to_check = {
                'default_state_prices': DefaultStatePrice,
                'client_state_prices': ClientStatePrice,
                'normal_client_state_prices': NormalClientStatePrice
            }
            
            for table_name, model_class in tables_to_check.items():
                columns = [col['name'] for col in inspector.get_columns(table_name)]
                
                if 'price_extra_per_kg' not in columns:
                    print(f"Adding price_extra_per_kg column to {table_name}...")
                    
                    # Add column dynamically
                    db.engine.execute(f"""
                        ALTER TABLE {table_name}
                        ADD COLUMN price_extra_per_kg FLOAT DEFAULT 20
                    """)
                    print(f"✓ Column added to {table_name}")
                else:
                    print(f"✓ Column already exists in {table_name}")
            
            print("\n✓ Migration completed successfully!")
            
        except Exception as e:
            print(f"✗ Migration failed: {str(e)}")
            print("You may need to add the column manually using:")
            print("  ALTER TABLE default_state_prices ADD COLUMN price_extra_per_kg FLOAT DEFAULT 20;")
            print("  ALTER TABLE client_state_prices ADD COLUMN price_extra_per_kg FLOAT DEFAULT 20;")
            print("  ALTER TABLE normal_client_state_prices ADD COLUMN price_extra_per_kg FLOAT DEFAULT 20;")

if __name__ == '__main__':
    migrate()
