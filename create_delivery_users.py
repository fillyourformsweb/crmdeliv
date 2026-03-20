#!/usr/bin/env python3
"""
Create test delivery users for testing the delivery dashboard system
"""

from app import app, db
from models import User

def create_delivery_users():
    with app.app_context():
        # Check if delivery1 already exists
        existing = User.query.filter_by(username='delivery1').first()
        if existing:
            print(f"✗ User 'delivery1' already exists")
            return False
        
        # Create test delivery users
        users_to_create = [
            {
                'username': 'delivery1',
                'email': 'delivery1@crm.com',
                'password': 'delivery123',
                'role': 'delivery',
                'phone': '9876543210',
                'address': 'Warehouse, Main St'
            },
            {
                'username': 'delivery2',
                'email': 'delivery2@crm.com',
                'password': 'delivery123',
                'role': 'delivery',
                'phone': '9876543211',
                'address': 'Distribution Center'
            },
            {
                'username': 'pickup1',
                'email': 'pickup1@crm.com',
                'password': 'pickup123',
                'role': 'delivery_pickup',
                'phone': '9876543212',
                'address': 'Pickup Station'
            }
        ]
        
        for user_data in users_to_create:
            try:
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    role=user_data['role'],
                    phone=user_data['phone'],
                    address=user_data['address']
                )
                user.set_password(user_data['password'])
                db.session.add(user)
                print(f"✓ Created user '{user_data['username']}' with role '{user_data['role']}'")
            except Exception as e:
                print(f"✗ Error creating user '{user_data['username']}': {e}")
                return False
        
        try:
            db.session.commit()
            print("\n✓ All delivery users created successfully!")
            print("\nTest Credentials:")
            for user_data in users_to_create:
                print(f"  - {user_data['username']} / {user_data['password']}")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error committing to database: {e}")
            return False

if __name__ == '__main__':
    create_delivery_users()
