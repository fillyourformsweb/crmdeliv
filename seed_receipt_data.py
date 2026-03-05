import sys
import os
from datetime import datetime

# Add the current directory to sys.path to import models
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app import app, db
from models import User, Branch, StaffReceiptAssignment, ReceiptSetting, BillingPattern, Client
from werkzeug.security import generate_password_hash

def seed_data():
    with app.app_context():
        # 1. Create Branches
        branches = [
            {'name': 'Mumbai Main Hub', 'code': 'MUM01', 'address': 'Andheri East, Mumbai'},
            {'name': 'Delhi North Hub', 'code': 'DEL01', 'address': 'Rohini, Delhi'},
            {'name': 'Bangalore South Hub', 'code': 'BLR01', 'address': 'Koramangala, Bangalore'}
        ]
        
        branch_objs = {}
        for b in branches:
            branch = Branch.query.filter_by(code=b['code']).first()
            if not branch:
                branch = Branch(**b)
                db.session.add(branch)
            branch_objs[b['code']] = branch
        db.session.commit()
        print("Branches seeded.")

        # 2. Create Users
        users = [
            {'username': 'mumbai_mgr', 'email': 'mum_mgr@example.com', 'password': 'password123', 'role': 'manager', 'branch_id': branch_objs['MUM01'].id},
            {'username': 'mumbai_staff', 'email': 'mum_staff@example.com', 'password': 'password123', 'role': 'staff', 'branch_id': branch_objs['MUM01'].id},
            {'username': 'delhi_mgr', 'email': 'del_mgr@example.com', 'password': 'password123', 'role': 'manager', 'branch_id': branch_objs['DEL01'].id},
            {'username': 'delhi_staff', 'email': 'del_staff@example.com', 'password': 'password123', 'role': 'staff', 'branch_id': branch_objs['DEL01'].id}
        ]
        
        user_objs = {}
        for u in users:
            user = User.query.filter_by(username=u['username']).first()
            if not user:
                user = User(
                    username=u['username'],
                    email=u['email'],
                    password_hash=generate_password_hash(u['password']),
                    role=u['role'],
                    branch_id=u['branch_id'],
                    is_active=True
                )
                db.session.add(user)
            user_objs[u['username']] = user
        db.session.commit()
        print("Users seeded.")

        # 3. Create Receipt Assignments
        admin = User.query.filter_by(role='admin').first()
        admin_id = admin.id if admin else 1
        
        assignments = [
            {
                'user_id': user_objs['mumbai_staff'].id,
                'branch_id': branch_objs['MUM01'].id,
                'prefix': 'MUM-',
                'base_number': '100000',
                'assigned_by': admin_id
            },
            {
                'user_id': user_objs['delhi_staff'].id,
                'branch_id': branch_objs['DEL01'].id,
                'prefix': 'DEL-',
                'base_number': '200000',
                'assigned_by': admin_id
            }
        ]
        
        for a in assignments:
            existing = StaffReceiptAssignment.query.filter_by(user_id=a['user_id'], branch_id=a['branch_id']).first()
            if not existing:
                assignment = StaffReceiptAssignment(**a)
                db.session.add(assignment)
        db.session.commit()
        print("Receipt assignments seeded.")

        # 4. Global Receipt Setting if missing
        setting = ReceiptSetting.query.first()
        if not setting:
            setting = ReceiptSetting(
                prefix='GEN-',
                base_number='500000',
                current_sequence=0,
                is_active=True
            )
            db.session.add(setting)
            db.session.commit()
            print("Global receipt settings seeded.")

        print("\nDummy data seeding complete!")
        print("Credentials: username / password123")

if __name__ == "__main__":
    seed_data()
