import unittest
from app import app
from models import db, User, Branch, Client

class BaseTestCase(unittest.TestCase):
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

class ModelTestCase(BaseTestCase):
    def test_user_creation(self):
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            
            queried_user = User.query.filter_by(username='testuser').first()
            self.assertIsNotNone(queried_user)
            self.assertEqual(queried_user.email, 'test@example.com')
            self.assertTrue(queried_user.check_password('password123'))

    def test_branch_creation(self):
        with app.app_context():
            branch = Branch(name='Test Branch', code='TB001')
            db.session.add(branch)
            db.session.commit()
            
            queried_branch = Branch.query.filter_by(code='TB001').first()
            self.assertIsNotNone(queried_branch)
            self.assertEqual(queried_branch.name, 'Test Branch')

if __name__ == '__main__':
    unittest.main()
