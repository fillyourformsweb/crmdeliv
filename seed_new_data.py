from app import app
from models import (
    db, User, Branch, Client, Receiver, ClientAddress, 
    BillingPattern, Order, TrackingUpdate, DefaultStatePrice,
    StaffReceiptAssignment
)
from datetime import datetime, timedelta
import random

def seed_data():
    with app.app_context():
        print("Starting data seeding with duplicate handling...")
        
        # 1. Get or Create Branches
        branches = []
        branch_codes = ["BLR-001", "CHN-001", "DEL-001", "MUM-001"]
        for code in branch_codes:
            existing = Branch.query.filter_by(code=code).first()
            if existing:
                branches.append(existing)
            else:
                branch = Branch(name=code, code=code, address="Address", phone="9000000000")
                db.session.add(branch)
                branches.append(branch)
        db.session.commit()
        print(f"✓ Branches: {len(branches)}")
        
        # 2. Get or Create Users
        users = []
        user_emails = ["admin@crm.com", "manager@bangalore.com", "staff@bangalore.com", 
                      "delivery@bangalore.com", "delivery2@bangalore.com"]
        for email in user_emails:
            existing = User.query.filter_by(email=email).first()
            if existing:
                users.append(existing)
            else:
                user = User(
                    username=email.split("@")[0],
                    email=email,
                    role="admin" if "admin" in email else ("manager" if "manager" in email else "staff"),
                    branch_id=branches[0].id if branches else None
                )
                user.set_password("password123")
                db.session.add(user)
                users.append(user)
        db.session.commit()
        print(f"✓ Users: {len(users)}")
        
        # 3. Billing patterns
        patterns = []
        for name in ["Standard", "Premium", "Economy"]:
            existing = BillingPattern.query.filter_by(name=name).first()
            if not existing:
                pattern = BillingPattern(
                    name=name, pattern_type=name.lower(), base_rate=50, rate_per_kg=10
                )
                db.session.add(pattern)
            patterns.append(existing if existing else pattern)
        db.session.commit()
        print(f"✓ Billing Patterns: {BillingPattern.query.count()}")
        
        # 4. Clients
        for i in range(4):
            if Client.query.filter_by(email=f"client{i}@example.com").count() == 0:
                client = Client(
                    name=f"Client {i}",
                    company_name=f"Company {i}",
                    email=f"client{i}@example.com",
                    phone=f"912345678{i}",
                    city="Bangalore",
                    state="Karnataka",
                    pincode="560001",
                    billing_pattern_id=patterns[0].id if patterns else None
                )
                db.session.add(client)
        db.session.commit()
        print(f"✓ Clients: {Client.query.count()}")
        
        # 5. Create 10 new orders
        existing_orders = Order.query.count()
        for i in range(min(10, 20 - existing_orders)):
            order = Order(
                receipt_number=f"RCP{100000 + existing_orders + i}",
                order_type="client",
                customer_name=f"Customer {i}",
                customer_phone=f"98765432{i:02d}",
                customer_address="Address",
                customer_city="Bangalore",
                customer_state="Karnataka",
                customer_pincode="560001",
                receiver_name=f"Receiver {i}",
                receiver_address="Receiver Address",
                receiver_city="Bangalore",
                receiver_state="Karnataka",
                receiver_pincode="560001",
                weight=round(random.uniform(0.5, 5), 2),
                weight_in_kg=round(random.uniform(0.5, 5), 2),
                base_amount=100,
                total_amount=150,
                status="pending",
                payment_status="unpaid",
                payment_mode="cash",
                branch_id=branches[0].id if branches else None,
                created_by=users[2].id if len(users) > 2 else None,
                delivery_person_id=users[3].id if len(users) > 3 else None,
                billing_pattern_id=patterns[0].id if patterns else None,
                created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30))
            )
            order.generate_tracking_link()
            order.generate_customer_form_link()
            db.session.add(order)
        db.session.commit()
        print(f"✓ Orders: {Order.query.count()}")
        
        print("\n" + "="*50)
        print("✓ DATA SEEDING COMPLETED!")
        print("="*50)
        print(f"Summary:")
        print(f"  Branches: {Branch.query.count()}")
        print(f"  Users: {User.query.count()}")
        print(f"  Clients: {Client.query.count()}")
        print(f"  Orders: {Order.query.count()}")
        print("="*50)

if __name__ == "__main__":
    seed_data()
