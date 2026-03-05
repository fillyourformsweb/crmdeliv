import random
from datetime import datetime, timedelta
from app import app, db
from models import User, Branch, Client, Order, BillingPattern, TrackingUpdate, ReceiptSetting

def seed_data():
    with app.app_context():
        print("Starting database seeding...")
        
        # 1. Create Branches
        branches = []
        branch_data = [
            ("Main Branch", "MB001", "123 Business Rd, New York", "555-0101", "main@crm.com"),
            ("North Branch", "NB002", "456 North St, Boston", "555-0102", "north@crm.com"),
            ("West Branch", "WB003", "789 West Blvd, Los Angeles", "555-0103", "west@crm.com")
        ]
        
        for name, code, addr, phone, email in branch_data:
            branch = Branch.query.filter_by(code=code).first()
            if not branch:
                branch = Branch(name=name, code=code, address=addr, phone=phone, email=email)
                db.session.add(branch)
            branches.append(branch)
        db.session.commit()
        print(f"Seeded {len(branches)} branches.")

        # 2. Create Billing Patterns (if not already exists via init_db)
        patterns = BillingPattern.query.all()
        if not patterns:
            pattern_data = [
                ("Express 10", "10", 50.0, 10.0, 0.5, 50.0, 5.0, 0.0),
                ("Priority 15", "15", 75.0, 15.0, 0.5, 100.0, 10.0, 5.0),
                ("Standard 30", "30", 100.0, 30.0, 1.0, 500.0, 20.0, 10.0)
            ]
            for name, p_type, base, per_kg, min_w, max_w, add_c, disc in pattern_data:
                p = BillingPattern(name=name, pattern_type=p_type, base_rate=base, 
                                 rate_per_kg=per_kg, min_weight=min_w, max_weight=max_w,
                                 additional_charges=add_c, discount_percentage=disc)
                db.session.add(p)
            db.session.commit()
            patterns = BillingPattern.query.all()
        print(f"Ensured {len(patterns)} billing patterns.")

        # 3. Create Users (Staff & Delivery)
        staff_users = []
        delivery_users = []
        
        roles = ['staff'] * 5 + ['delivery'] * 8
        for i, role in enumerate(roles):
            username = f"{role}_{i+1}"
            if not User.query.filter_by(username=username).first():
                user = User(
                    username=username,
                    email=f"{username}@example.com",
                    role=role,
                    branch_id=random.choice(branches).id,
                    phone=f"555-020{i}",
                    address=f"User Address Street {i}"
                )
                user.set_password("password123")
                db.session.add(user)
                if role == 'staff': staff_users.append(user)
                else: delivery_users.append(user)
        db.session.commit()
        
        # Refresh lists from DB
        staff_users = User.query.filter_by(role='staff').all()
        delivery_users = User.query.filter_by(role='delivery').all()
        print(f"Seeded {len(staff_users)} staff and {len(delivery_users)} delivery personnel.")

        # 4. Create Clients
        client_names = ["Global Logistics", "Tech Solutions Inc", "Fashion Hub", "Daily Fresh", "Mega Retail", "Blue Whale Co", "Eco Systems", "Swift Services"]
        clients = []
        for name in client_names:
            if not Client.query.filter_by(name=name).first():
                client = Client(
                    name=name,
                    company_name=f"{name} Group",
                    email=f"contact@{name.lower().replace(' ', '')}.com",
                    phone=f"555-030{random.randint(10, 99)}",
                    address=f"{random.randint(1,999)} Commerce Way, Suite {random.randint(1,50)}",
                    billing_pattern_id=random.choice(patterns).id
                )
                db.session.add(client)
                clients.append(client)
        db.session.commit()
        clients = Client.query.all()
        print(f"Seeded {len(clients)} clients.")

        # 5. Create Orders
        statuses = ['pending', 'confirmed', 'in_transit', 'delivered', 'cancelled']
        order_types = ['client', 'walkin']
        receipt_modes = ['standard', 'prime', 'parcel', 'state_express']
        cities = ["New York", "Boston", "Chicago", "San Francisco", "Austin", "Seattle", "Miami"]
        
        print("Generating 50 orders...")
        for i in range(50):
            order_type = random.choice(order_types)
            client = random.choice(clients) if order_type == 'client' else None
            
            # Helper to calculate amounts (simplified copy from app.py logic)
            weight = round(random.uniform(0.5, 25.0), 2)
            pattern = random.choice(patterns)
            base = pattern.base_rate
            weight_charge = weight * pattern.rate_per_kg
            additional = pattern.additional_charges
            discount = ((base + weight_charge) * pattern.discount_percentage / 100)
            total = base + weight_charge + additional - discount

            created_at = datetime.utcnow() - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
            
            order = Order(
                receipt_number=f"REC-{random.randint(100000, 999999)}-{i}",
                order_type=order_type,
                receipt_mode=random.choice(receipt_modes),
                client_id=client.id if client else None,
                customer_name=client.name if client else f"Walk-in Customer {i}",
                customer_phone=client.phone if client else f"555-999{i:02d}",
                customer_address=client.address if client else "Random Customer Address",
                receiver_name=f"Receiver {i}",
                receiver_phone=f"555-888{i:02d}",
                receiver_address=f"{random.randint(100, 999)} Destination St",
                receiver_city=random.choice(cities),
                receiver_state="ST",
                receiver_pincode=str(random.randint(10000, 99999)),
                package_description=f"Package containing item category {random.randint(1, 5)}",
                weight=weight,
                number_of_boxes=random.randint(1, 5),
                base_amount=base,
                weight_charges=weight_charge,
                additional_charges=additional,
                discount=discount,
                total_amount=total,
                status=random.choice(statuses),
                branch_id=random.choice(branches).id,
                created_by=random.choice(staff_users).id,
                billing_pattern_id=pattern.id,
                created_at=created_at
            )
            
            if order.status == 'delivered':
                order.delivered_at = order.created_at + timedelta(days=random.randint(1, 5))
            
            if order.status in ['in_transit', 'delivered']:
                order.delivery_person_id = random.choice(delivery_users).id

            db.session.add(order)
            db.session.flush() # Get order.id

            # Add some tracking updates
            if order.status != 'pending':
                update = TrackingUpdate(
                    order_id=order.id,
                    status="Order Picked Up",
                    location=order.branch.name,
                    description="Package has been received at the branch.",
                    created_at=order.created_at + timedelta(hours=2)
                )
                db.session.add(update)
                
                if order.status in ['in_transit', 'delivered']:
                    update2 = TrackingUpdate(
                        order_id=order.id,
                        status="In Transit",
                        location="Distribution Hub",
                        description="Package is moving towards destination city.",
                        created_at=order.created_at + timedelta(days=1)
                    )
                    db.session.add(update2)

        db.session.commit()
        print("Successfully seeded 50 orders with tracking history.")
        print("Database seeding complete!")

if __name__ == "__main__":
    seed_data()
