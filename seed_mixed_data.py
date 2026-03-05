from app import app, db
from models import User, Client, Order, ReceiptSetting, BillingPattern, Branch
from datetime import datetime
import random

def seed_data():
    with app.app_context():
        print("Starting seed...")

        # 1. Create Dummy Users (Staff/Delivery)
        print("Creating Users...")
        users_data = [
            {'username': 'log_staff', 'email': 'staff1@crm.com', 'role': 'staff', 'password': 'password123'},
            {'username': 'log_delivery', 'email': 'delivery1@crm.com', 'role': 'delivery', 'password': 'password123'},
            {'username': 'log_manager', 'email': 'manager@crm.com', 'role': 'admin', 'password': 'password123'}
        ]
        
        for u_data in users_data:
            if not User.query.filter_by(username=u_data['username']).first():
                user = User(
                    username=u_data['username'],
                    email=u_data['email'],
                    role=u_data['role'],
                )
                user.set_password(u_data['password'])
                db.session.add(user)
        
        # Ensure a branch exists
        branch = Branch.query.first()
        if not branch:
            branch = Branch(name="Main Branch", code="MB01", address="123 Main St", phone="1234567890")
            db.session.add(branch)
            db.session.commit() # Commit to get ID
            
        # Ensure Billing Pattern exists
        bp = BillingPattern.query.first()
        if not bp:
            bp = BillingPattern(name="Standard", pattern_type="30", base_rate=100, rate_per_kg=20)
            db.session.add(bp)
            db.session.commit()

        # 2. Create Clients
        print("Creating Clients...")
        clients_data = [
            {'name': 'Alpha Corp', 'phone': '9876543210', 'email': 'contact@alpha.com', 'company': 'Alpha Industries'},
            {'name': 'Beta Traders', 'phone': '8765432109', 'email': 'info@beta.com', 'company': 'Beta Ltd'},
            {'name': 'Gamma Logistics', 'phone': '7654321098', 'email': 'support@gamma.com', 'company': 'Gamma Sol'}
        ]
        
        created_clients = []
        for c_data in clients_data:
            client = Client.query.filter_by(phone=c_data['phone']).first()
            if not client:
                client = Client(
                    name=c_data['name'],
                    phone=c_data['phone'],
                    email=c_data['email'],
                    company_name=c_data['company'],
                    billing_pattern_id=bp.id
                )
                db.session.add(client)
                db.session.commit() # Commit to get ID
            created_clients.append(client)

        # 3. Create Orders (Walking & Client)
        print("Creating Orders...")
        
        # Walking Orders (No Client ID, order_type='walkin')
        for i in range(5):
            order = Order(
                receipt_number=f"WALK-{random.randint(1000, 9999)}",
                order_type='walkin',
                customer_name=f"Walkin Customer {i+1}",
                customer_phone=f"55500000{i}",
                package_description="Personal items",
                weight=random.uniform(1.0, 10.0),
                total_amount=random.uniform(100, 500),
                status=random.choice(['pending', 'in_transit', 'delivered']),
                branch_id=branch.id
            )
            db.session.add(order)

        # Client Orders
        for i in range(5):
            client = random.choice(created_clients)
            order = Order(
                receipt_number=f"CLI-{random.randint(1000, 9999)}",
                order_type='client',
                client_id=client.id,
                customer_name=client.name,
                customer_phone=client.phone,
                package_description="Business documents",
                weight=random.uniform(0.5, 5.0),
                total_amount=random.uniform(200, 1000),
                status=random.choice(['pending', 'in_transit', 'delivered']),
                branch_id=branch.id
            )
            db.session.add(order)

        db.session.commit()
        print("Seeding complete!")

if __name__ == '__main__':
    seed_data()
