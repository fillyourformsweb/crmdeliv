import unittest
from app import app
from models import db, User
from tests.test_models import BaseTestCase

class AuthTestCase(BaseTestCase):
    def test_login_success(self):
        # Create user first
        with app.app_context():
            user = User(username='testadmin', email='admin@test.com', role='admin')
            user.set_password('adminpass')
            db.session.add(user)
            db.session.commit()
            
        # Try login
        response = self.app.post('/login', data=dict(
            username='testadmin',
            password='adminpass'
        ), follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login successful!', response.data)
        self.assertIn(b'Dashboard', response.data)

    def test_login_failure(self):
        response = self.app.post('/login', data=dict(
            username='wronguser',
            password='wrongpassword'
        ), follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid username or password.', response.data)

    def test_protected_route_access(self):
        # Redirect if not logged in
        response = self.app.get('/dashboard', follow_redirects=True)
        self.assertIn(b'Please log in to access this page.', response.data) # Standard Flask-Login msg

if __name__ == '__main__':
    unittest.main()
