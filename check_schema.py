#!/usr/bin/env python
"""Check actual database schema"""
from app import db, app
from sqlalchemy import inspect

with app.app_context():
    inspector = inspect(db.engine)
    
    print('=== Checking database schema ===\n')
    
    for table_name in ['default_state_prices', 'client_state_prices', 'normal_client_state_prices']:
        cols = inspector.get_columns(table_name)
        print(f'{table_name}:')
        for col in cols:
            print(f'  - {col["name"]}')
        print()
