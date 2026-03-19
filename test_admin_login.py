#!/usr/bin/env python
"""Test admin dashboard access"""

from app import app, db
from models import User, Order
import sys

try:
    with app.app_context():
        print("Checking admin user...")
        admin = User.query.filter_by(role='admin').first()
        
        if not admin:
            print("❌ No admin user found in database!")
            sys.exit(1)
        
        print(f"✓ Admin user found: {admin.username}")
        print(f"✓ Admin role: {admin.role}")
        print(f"✓ Admin is_active: {admin.is_authenticated}")
        
        # Test the dashboard route
        print("\nTesting admin dashboard route...")
        with app.test_client() as client:
            # Login as admin
            response = client.post('/login', data={
                'username': admin.username,
                'password': 'admin123'  # Default password
            }, follow_redirects=True)
            
            print(f"Login response status: {response.status_code}")
            
            # Try to access admin dashboard
            response = client.get('/admin-dashboard')
            print(f"Admin dashboard response status: {response.status_code}")
            
            if response.status_code == 200:
                print("✓ Admin dashboard is accessible!")
                if b'Admin Analytics' in response.data:
                    print("✓ Admin dashboard content found!")
                else:
                    print("⚠ Admin dashboard template may be missing content")
            elif response.status_code == 302:
                print("⚠ Admin dashboard redirecting to:", response.location)
            elif response.status_code == 403:
                print("❌ Access forbidden to admin dashboard")
            elif response.status_code == 500:
                print("❌ Server error on admin dashboard")
                print("Response data:", response.data[:500])
            else:
                print(f"❌ Unexpected status code: {response.status_code}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
