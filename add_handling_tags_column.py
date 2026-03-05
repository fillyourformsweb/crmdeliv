"""
Migration script to add handling_tags column to orders table
This script has already been executed successfully.
"""

from app import app, db
from sqlalchemy import text

def add_handling_tags_column():
    """Add handling_tags column to orders table if it doesn't exist"""
    with app.app_context():
        try:
            # Try to add the column
            db.session.execute(text('ALTER TABLE orders ADD COLUMN handling_tags TEXT'))
            db.session.commit()
            print('✓ Column handling_tags added successfully to orders table')
        except Exception as e:
            if 'duplicate column name' in str(e).lower():
                print('✓ Column handling_tags already exists in orders table')
            else:
                print(f'✗ Error adding column: {e}')
                raise

if __name__ == '__main__':
    add_handling_tags_column()
