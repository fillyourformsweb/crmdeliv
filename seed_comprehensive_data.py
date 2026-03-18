from app import app
from models import (
    db, User, Branch, Client, Receiver, ClientAddress, 
    BillingPattern, Order, TrackingUpdate, DefaultStatePrice,
    StaffReceiptAssignment
)
from datetime import datetime, timedelta
import random

def seed_comprehensive():
    with app.app_context():
        # Clear existing data (optional - comment out if you want to keep existing data)
        # db.drop_all()
        # db.create_all()
        
        print("Starting comprehensive data seeding...")
        
        # 1. Create Branches (skip if exists)
        branches = [
            Branch(
                name="Bangalore Branch",
                code="BLR-001",
                address="123 Tech Park, Whitefield",
                phone="9876543210",
                email="bangalore@crm.com"
            ),
            Branch(
                name="Chennai Branch",
                code="CHN-001",
                address="456 IT Corridor, Tidel Park",
                phone="9876543211",
                email="chennai@crm.com"
            ),
            Branch(
                name="Delhi Branch",
                code="DEL-001",
                address="789 Business District, Gurgaon",
                phone="9876543212",
                email="delhi@crm.com"
            ),
            Branch(
                name="Mumbai Branch",
                code="MUM-001",
                address="321 Commercial Hub, Andheri",
                phone="9876543213",
                email="mumbai@crm.com"
            )
        ]
        db.session.add_all(branches)
        db.session.commit()
        print("✓ Created 4 branches")
        
        # 2. Create Users
        user_data = [
            {"username": "admin", "email": "admin@crm.com", "role": "admin"},
            {"username": "manager_blr", "email": "manager@bangalore.com", "role": "manager"},
            {"username": "staff_blr", "email": "staff@bangalore.com", "role": "staff"},
            {"username": "delivery_blr", "email": "delivery@bangalore.com", "role": "delivery"},
            {"username": "delivery_blr2", "email": "delivery2@bangalore.com", "role": "delivery"},
        ]
        
        users = []
        for i, user_info in enumerate(user_data):
            existing_user = User.query.filter_by(email=user_info['email']).first()
            if existing_user:
                users.append(existing_user)
                print(f"  - User {user_info['email']} already exists, skipping")
            else:
                user = User(
                    username=user_info['username'],
                    email=user_info['email'],
                    role=user_info['role'],
                    branch_id=branches[0].id if i == 0 or branches else None,
                    phone=f"9{8-i}88888888",
                    address=f"Address {i}"
                )
                user.set_password("password123")
                db.session.add(user)
                users.append(user)
        
        db.session.commit()
        print(f"✓ Users processed (created new ones, skipped existing)")

        
        # 3. Create Billing Patterns
        billing_patterns = [
            BillingPattern(
                name="Standard",
                pattern_type="standard",
                base_rate=50,
                rate_per_kg=10,
                min_weight=0.5,
                description="Standard billing pattern for regular clients"
            ),
            BillingPattern(
                name="Premium",
                pattern_type="premium",
                base_rate=75,
                rate_per_kg=15,
                min_weight=0.25,
                description="Premium billing with faster service"
            ),
            BillingPattern(
                name="Economy",
                pattern_type="economy",
                base_rate=30,
                rate_per_kg=8,
                min_weight=1,
                description="Economy billing for bulk shipments"
            ),
        ]
        db.session.add_all(billing_patterns)
        db.session.commit()
        print("✓ Created 3 billing patterns")
        
        # 4. Create Clients
        clients = [
            Client(
                name="Rajesh Kumar",
                company_name="TechFlow Solutions",
                email="rajesh@techflow.com",
                phone="9123456789",
                address="Plot 45, Tech Park",
                city="Bangalore",
                state="Karnataka",
                pincode="560001",
                gst_number="29ABCDE1234F1Z5",
                billing_pattern_id=billing_patterns[0].id,
                billing_date=1
            ),
            Client(
                name="Priya Sharma",
                company_name="Global Logistics",
                email="priya@globallog.com",
                phone="8123456789",
                address="123 Ship Lane",
                city="Chennai",
                state="Tamil Nadu",
                pincode="600001",
                gst_number="33FGHIJ5678K2Z9",
                billing_pattern_id=billing_patterns[1].id,
                billing_date=10
            ),
            Client(
                name="Amit Patel",
                company_name="Express Trading",
                email="amit@expresstrade.com",
                phone="7123456789",
                address="456 Commerce Street",
                city="Delhi",
                state="Delhi",
                pincode="110001",
                gst_number="07IJKLM9012N3Z8",
                billing_pattern_id=billing_patterns[0].id,
                billing_date=15
            ),
            Client(
                name="Neha Singh",
                company_name="FastShip Industries",
                email="neha@fastship.com",
                phone="6123456789",
                address="789 Port Road",
                city="Mumbai",
                state="Maharashtra",
                pincode="400001",
                gst_number="27OPQRS3456T4Z7",
                billing_pattern_id=billing_patterns[2].id,
                billing_date=20
            ),
        ]
        db.session.add_all(clients)
        db.session.commit()
        print("✓ Created 4 clients")
        
        # 5. Create Client Addresses
        client_addresses = [
            ClientAddress(
                client_id=clients[0].id,
                address_label="Head Office",
                address="Plot 45, Tech Park",
                city="Bangalore",
                state="Karnataka",
                pincode="560001"
            ),
            ClientAddress(
                client_id=clients[0].id,
                address_label="Warehouse",
                address="123 Industrial Estate",
                city="Bangalore",
                state="Karnataka",
                pincode="560034"
            ),
            ClientAddress(
                client_id=clients[1].id,
                address_label="Main Office",
                address="123 Ship Lane",
                city="Chennai",
                state="Tamil Nadu",
                pincode="600001"
            ),
            ClientAddress(
                client_id=clients[2].id,
                address_label="Branch Office",
                address="456 Commerce Street",
                city="Delhi",
                state="Delhi",
                pincode="110001"
            ),
        ]
        db.session.add_all(client_addresses)
        db.session.commit()
        print("✓ Created 4 client addresses")
        
        # 6. Create Receivers
        receivers = [
            Receiver(
                client_id=clients[0].id,
                name="John Doe",
                company_name="Tech Corp",
                phone="9876543210",
                email="john@techcorp.com",
                address="123 Innovation Drive",
                city="Bangalore",
                state="Karnataka",
                pincode="560001",
                gst_number="29ABCDE1234F1Z5",
                bill_pattern="BLR-NORTH"
            ),
            Receiver(
                client_id=clients[0].id,
                name="Jane Smith",
                company_name="Tech Retail",
                phone="9876543211",
                email="jane@techretail.com",
                address="456 Commerce Hub",
                city="Bangalore",
                state="Karnataka",
                pincode="560027"
            ),
            Receiver(
                client_id=clients[1].id,
                name="David Wilson",
                company_name="Global Trade",
                phone="8876543210",
                email="david@globaltrade.com",
                address="789 Port Lane",
                city="Chennai",
                state="Tamil Nadu",
                pincode="600001"
            ),
            Receiver(
                client_id=clients[2].id,
                name="Sarah Johnson",
                company_name="Express Ltd",
                phone="7876543210",
                email="sarah@expressltd.com",
                address="321 Business Park",
                city="Delhi",
                state="Delhi",
                pincode="110001"
            ),
            Receiver(
                client_id=clients[3].id,
                name="Michael Brown",
                company_name="Fast Industries",
                phone="6876543210",
                email="michael@fastind.com",
                address="654 Industrial Zone",
                city="Mumbai",
                state="Maharashtra",
                pincode="400001"
            ),
        ]
        db.session.add_all(receivers)
        db.session.commit()
        print("✓ Created 5 receivers")
        
        # 7. Create Staff Receipt Assignments
        assignments = [
            StaffReceiptAssignment(
                user_id=users[2].id,
                branch_id=branches[0].id,
                prefix="BLR",
                base_number="100001",
                range_end="100500",
                current_sequence=0,
                assigned_by=users[0].id
            ),
            StaffReceiptAssignment(
                user_id=users[3].id,
                branch_id=branches[0].id,
                prefix="BLRD",
                base_number="200001",
                range_end="200500",
                current_sequence=0,
                assigned_by=users[0].id
            ),
        ]
        db.session.add_all(assignments)
        db.session.commit()
        print("✓ Created 2 staff receipt assignments")
        
        # 8. Create Orders
        orders = []
        receipt_counter = 100001
        statuses = ['pending', 'confirmed', 'in_transit', 'delivered', 'cancelled']
        payment_statuses = ['unpaid', 'partial', 'paid']
        payment_modes = ['cash', 'card', 'upi', 'credit']
        
        for i in range(20):
            order = Order(
                receipt_number=f"RCP{receipt_counter + i}",
                order_type="client" if i % 2 == 0 else "walkin",
                receipt_mode="standard" if i % 3 == 0 else "prime",
                customer_name=f"Customer {i+1}",
                customer_phone=f"98765432{str(i).zfill(2)}",
                customer_email=f"customer{i+1}@example.com",
                customer_address=f"Address {i+1}, Street {i+1}",
                customer_city=random.choice(["Bangalore", "Chennai", "Delhi", "Mumbai"]),
                customer_state=random.choice(["Karnataka", "Tamil Nadu", "Delhi", "Maharashtra"]),
                customer_pincode=f"{560000 + i}",
                receiver_name=random.choice([r.name for r in receivers]),
                receiver_phone=random.choice([r.phone for r in receivers]),
                receiver_address=f"Receiver Address {i+1}",
                receiver_city=random.choice(["Bangalore", "Chennai", "Delhi", "Mumbai"]),
                receiver_state=random.choice(["Karnataka", "Tamil Nadu", "Delhi", "Maharashtra"]),
                receiver_pincode=f"{560000 + i}",
                package_description=f"Package {i+1} - Various items",
                weight=round(random.uniform(0.5, 5), 2),
                weight_in_kg=round(random.uniform(0.5, 5), 2),
                number_of_boxes=random.randint(1, 3),
                base_amount=round(random.uniform(50, 200), 2),
                weight_charges=round(random.uniform(10, 50), 2),
                additional_charges=round(random.uniform(0, 30), 2),
                total_amount=round(random.uniform(100, 300), 2),
                received_amount=round(random.uniform(100, 300), 2),
                status=random.choice(statuses),
                payment_status=random.choice(payment_statuses),
                payment_mode=random.choice(payment_modes),
                client_id=random.choice([c.id for c in clients]),
                branch_id=random.choice([b.id for b in branches]),
                created_by=users[2].id,
                delivery_person_id=random.choice([users[3].id, users[4].id]),
                billing_pattern_id=random.choice([bp.id for bp in billing_patterns]),
                created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30)),
            )
            order.generate_tracking_link()
            order.generate_customer_form_link()
            orders.append(order)
        
        db.session.add_all(orders)
        db.session.commit()
        print(f"✓ Created {len(orders)} orders")
        
        # 9. Create Tracking Updates
        tracking_updates = []
        tracking_statuses = ['pending', 'picked_up', 'in_transit', 'out_for_delivery', 'delivered']
        locations = ['Bangalore', 'Chennai', 'Delhi', 'Mumbai', 'Hyderabad', 'Pune']
        
        for order in orders[:10]:  # Add tracking for first 10 orders
            num_updates = random.randint(1, 4)
            for j in range(num_updates):
                update = TrackingUpdate(
                    order_id=order.id,
                    status=tracking_statuses[min(j, len(tracking_statuses)-1)],
                    location=random.choice(locations),
                    description=f"Order {tracking_statuses[min(j, len(tracking_statuses)-1)]} in {random.choice(locations)}",
                    updated_by=users[3].id,
                    created_at=datetime.utcnow() - timedelta(hours=random.randint(0, 72))
                )
                tracking_updates.append(update)
        
        db.session.add_all(tracking_updates)
        db.session.commit()
        print(f"✓ Created {len(tracking_updates)} tracking updates")
        
        # 10. Create Default State Prices
        states = {
            "Karnataka": {"100g": 50, "250g": 80, "500g": 120, "1kg": 180, "2kg": 300, "3kg": 400},
            "Tamil Nadu": {"100g": 55, "250g": 85, "500g": 125, "1kg": 185, "2kg": 310, "3kg": 410},
            "Delhi": {"100g": 60, "250g": 90, "500g": 130, "1kg": 190, "2kg": 320, "3kg": 420},
            "Maharashtra": {"100g": 62, "250g": 92, "500g": 132, "1kg": 192, "2kg": 325, "3kg": 425},
            "Telangana": {"100g": 53, "250g": 83, "500g": 123, "1kg": 183, "2kg": 305, "3kg": 405},
        }
        
        default_state_prices = []
        for state, prices in states.items():
            price = DefaultStatePrice(
                state=state,
                price_100gm=prices["100g"],
                price_250gm=prices["250g"],
                price_500gm=prices["500g"],
                price_1kg=prices["1kg"],
                price_2kg=prices["2kg"],
                price_3kg=prices["3kg"],
                price_extra_per_kg=20
            )
            default_state_prices.append(price)
        
        db.session.add_all(default_state_prices)
        db.session.commit()
        print("✓ Created default state prices for 5 states")
        
        print("\n" + "="*50)
        print("✓ COMPREHENSIVE DATA SEEDING COMPLETED!")
        print("="*50)
        print(f"Summary:")
        print(f"  - Branches: {len(branches)}")
        print(f"  - Users: {len(users)}")
        print(f"  - Billing Patterns: {len(billing_patterns)}")
        print(f"  - Clients: {len(clients)}")
        print(f"  - Client Addresses: {len(client_addresses)}")
        print(f"  - Receivers: {len(receivers)}")
        print(f"  - Orders: {len(orders)}")
        print(f"  - Tracking Updates: {len(tracking_updates)}")
        print(f"  - Default State Prices: {len(default_state_prices)}")
        print(f"  - Staff Receipt Assignments: {len(assignments)}")
        print("="*50)

if __name__ == "__main__":
    seed_comprehensive()
