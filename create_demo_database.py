#!/usr/bin/env python
"""
Comprehensive Demo Database Creator
Creates realistic sample data across all tables for testing and demonstration
"""

from app import app, db
from models import (
    User, Branch, Client, Receiver, ClientAddress, BillingPattern,
    Order, TrackingUpdate, DefaultStatePrice, ClientStatePrice,
    NormalClientStatePrice, Courier, Offer, SalesVisit, FollowUp, Meeting,
    ReceiptSetting, StaffReceiptAssignment, SystemSettings, ExcelUpload,
    ExcelData, Notification, AuditLog
)
from datetime import datetime, timedelta
import random
import secrets

# ============ INDIAN STATES FOR DEMO ============
INDIAN_STATES = [
    'Maharashtra', 'Tamil Nadu', 'Karnataka', 'Delhi', 'Uttar Pradesh',
    'Rajasthan', 'Gujarat', 'West Bengal', 'Punjab', 'Haryana',
    'Telangana', 'Andhra Pradesh', 'Madhya Pradesh', 'Bihar', 'Jharkhand'
]

SHIPPING_MODES = ['standard', 'prime', 'prime_express', 'parcel', 'state_express', 'road_express', 'air']

def create_demo_database():
    """Create complete demo database"""
    with app.app_context():
        print("🚀 Creating Demo Database...")
        
        # Clear existing data (optional - comment out for preserving data)
        print("📋 Clearing existing data...")
        # db.drop_all()
        # db.create_all()
        
        # 1. Create System Settings
        print("⚙️  Creating system settings...")
        create_system_settings()
        
        # 2. Create Branches
        print("🏢 Creating branches...")
        branches = create_branches()
        
        # 3. Create Users (Admin, Managers, Staff, Delivery Team)
        print("👥 Creating users...")
        users = create_users(branches)
        
        # 4. Create Billing Patterns
        print("💳 Creating billing patterns...")
        billing_patterns = create_billing_patterns()
        
        # 5. Create Pricing Data (Default State Prices)
        print("💰 Creating default state prices...")
        create_default_state_prices()
        
        # 6. Create Normal Client State Prices
        print("💹 Creating normal client state prices...")
        create_normal_client_state_prices()
        
        # 7. Create Couriers
        print("🚚 Creating courier companies...")
        couriers = create_couriers()
        
        # 8. Create Offers
        print("🎁 Creating promotional offers...")
        offers = create_offers(users)
        
        # 9. Create Clients
        print("👔 Creating corporate clients...")
        clients = create_clients(billing_patterns)
        
        # 10. Create Client Addresses
        print("📍 Creating client addresses...")
        create_client_addresses(clients)
        
        # 11. Create Receivers
        print("📦 Creating receivers...")
        create_receivers(clients)
        
        # 12. Create Client State Prices
        print("🎯 Creating client-specific state prices...")
        create_client_state_prices(clients)
        
        # 13. Create Receipt Settings
        print("📃 Creating receipt settings...")
        create_receipt_settings(users)
        
        # 14. Create Orders
        print("📋 Creating sample orders...")
        orders = create_orders(clients, users, branches)
        
        # 15. Create Tracking Updates
        print("📍 Creating tracking updates...")
        create_tracking_updates(orders, users)
        
        # 16. Create Sales Visits
        print("🤝 Creating sales visits...")
        sales_visits = create_sales_visits(users)
        
        # 17. Create Follow-ups
        print("📞 Creating follow-ups...")
        create_follow_ups(sales_visits, users)
        
        # 18. Create Meetings
        print("📅 Creating scheduled meetings...")
        create_meetings(sales_visits, users)
        
        print("\n✅ Demo Database Created Successfully!")
        print("\n📊 Summary:")
        print(f"   • Users: {User.query.count()}")
        print(f"   • Branches: {Branch.query.count()}")
        print(f"   • Clients: {Client.query.count()}")
        print(f"   • Receivers: {Receiver.query.count()}")
        print(f"   • Billing Patterns: {BillingPattern.query.count()}")
        print(f"   • Orders: {Order.query.count()}")
        print(f"   • Tracking Updates: {TrackingUpdate.query.count()}")
        print(f"   • Default State Prices: {DefaultStatePrice.query.count()}")
        print(f"   • Client State Prices: {ClientStatePrice.query.count()}")
        print(f"   • Normal Client Prices: {NormalClientStatePrice.query.count()}")
        print(f"   • Couriers: {Courier.query.count()}")
        print(f"   • Offers: {Offer.query.count()}")
        print(f"   • Sales Visits: {SalesVisit.query.count()}")
        print(f"   • Follow-ups: {FollowUp.query.count()}")
        print(f"   • Meetings: {Meeting.query.count()}")


def create_system_settings():
    """Create system configuration settings"""
    if SystemSettings.query.count() == 0:
        settings = [
            SystemSettings(key='app_name', value='CRM Delivery System', description='Application Name'),
            SystemSettings(key='timezone', value='Asia/Kolkata', description='System Timezone'),
            SystemSettings(key='currency', value='INR', description='Currency Code'),
            SystemSettings(key='tax_rate', value='18', description='Default Tax Rate (%)'),
            SystemSettings(key='insurance_rate', value='1.5', description='Insurance Rate (%)'),
            SystemSettings(key='base_receipt_number', value='100371900086', description='Base Receipt Number'),
        ]
        db.session.add_all(settings)
        db.session.commit()


def create_branches():
    """Create demo branches"""
    branches = [
        Branch(name='Mumbai Branch', code='MUM', address='123 Business Park, Mumbai', 
               phone='9876543210', email='mumbai@crmdelivery.com', is_active=True),
        Branch(name='Delhi Branch', code='DEL', address='456 Trade Center, New Delhi', 
               phone='9876543211', email='delhi@crmdelivery.com', is_active=True),
        Branch(name='Bangalore Branch', code='BNG', address='789 Tech Park, Bangalore', 
               phone='9876543212', email='bangalore@crmdelivery.com', is_active=True),
        Branch(name='Chennai Branch', code='CHE', address='321 Business Hub, Chennai', 
               phone='9876543213', email='chennai@crmdelivery.com', is_active=True),
    ]
    
    for branch in branches:
        if not Branch.query.filter_by(code=branch.code).first():
            db.session.add(branch)
    
    db.session.commit()
    return Branch.query.all()


def create_users(branches):
    """Create demo users with different roles"""
    users = []
    
    # Admin User
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email='admin@crmdelivery.com',
            phone='9999999900',
            role='admin',
            branch_id=branches[0].id,
            is_active=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        users.append(admin)
    
    # Manager Users (one per branch)
    for i, branch in enumerate(branches):
        if not User.query.filter_by(username=f'manager_branch{i+1}').first():
            manager = User(
                username=f'manager_branch{i+1}',
                email=f'manager{i+1}@crmdelivery.com',
                phone=f'999999990{i}',
                role='manager',
                branch_id=branch.id,
                is_active=True
            )
            manager.set_password('manager123')
            db.session.add(manager)
            users.append(manager)
    
    # Staff Users (multiple per branch)
    staff_count = 0
    for branch in branches:
        for j in range(3):
            if not User.query.filter_by(username=f'staff_{branch.code}_{j+1}').first():
                staff = User(
                    username=f'staff_{branch.code}_{j+1}',
                    email=f'staff_{branch.code}_{j+1}@crmdelivery.com',
                    phone=f'988888888{staff_count % 10}',
                    role='staff',
                    branch_id=branch.id,
                    is_active=True
                )
                staff.set_password('staff123')
                db.session.add(staff)
                users.append(staff)
                staff_count += 1
    
    # Delivery Team Users
    delivery_count = 0
    for branch in branches:
        for j in range(5):
            if not User.query.filter_by(username=f'delivery_{branch.code}_{j+1}').first():
                delivery = User(
                    username=f'delivery_{branch.code}_{j+1}',
                    email=f'delivery_{branch.code}_{j+1}@crmdelivery.com',
                    phone=f'977777777{delivery_count % 10}',
                    role='delivery',
                    branch_id=branch.id,
                    is_active=True
                )
                delivery.set_password('delivery123')
                db.session.add(delivery)
                users.append(delivery)
                delivery_count += 1
    
    db.session.commit()
    return User.query.all()


def create_billing_patterns():
    """Create billing patterns"""
    patterns = [
        BillingPattern(
            name='Startup Pattern', pattern_type='10', base_rate=30, rate_per_kg=10,
            min_weight=0.5, max_weight=50, discount_percentage=5,
            description='Best for small startups with low shipping volume'
        ),
        BillingPattern(
            name='Standard Pattern', pattern_type='15', base_rate=50, rate_per_kg=15,
            min_weight=0.5, max_weight=100, discount_percentage=10,
            description='Most popular pattern for medium enterprises'
        ),
        BillingPattern(
            name='Premium Pattern', pattern_type='30', base_rate=100, rate_per_kg=30,
            min_weight=0.5, max_weight=500, discount_percentage=20,
            description='For large enterprises with high volume'
        ),
        BillingPattern(
            name='Enterprise Pattern', pattern_type='25', base_rate=80, rate_per_kg=25,
            min_weight=0.5, max_weight=1000, discount_percentage=15,
            description='Customized for enterprise clients'
        ),
    ]
    
    for pattern in patterns:
        if not BillingPattern.query.filter_by(name=pattern.name).first():
            db.session.add(pattern)
    
    db.session.commit()
    return BillingPattern.query.all()


def create_default_state_prices():
    """Create default pricing for all states and shipping modes"""
    for state in INDIAN_STATES:
        for mode in SHIPPING_MODES:
            # Check if already exists
            existing = DefaultStatePrice.query.filter_by(state=state, shipping_mode=mode).first()
            if not existing:
                # Base prices vary by shipping mode
                base_prices = {
                    'standard': {'100gm': 30, '250gm': 50, '500gm': 80, '1kg': 120, '2kg': 200, '3kg': 280, 'extra': 80},
                    'prime': {'100gm': 40, '250gm': 65, '500gm': 100, '1kg': 150, '2kg': 250, '3kg': 340, 'extra': 100},
                    'prime_express': {'1kg': 180, 'extra': 120},  # Prime Express has special tier logic
                    'parcel': {'100gm': 35, '250gm': 60, '500gm': 95, '1kg': 140, '2kg': 230, '3kg': 310, 'extra': 90},
                    'state_express': {'100gm': 25, '250gm': 45, '500gm': 70, '1kg': 110, '2kg': 180, '3kg': 250, 'extra': 70},
                    'road_express': {'100gm': 50, '250gm': 80, '500gm': 120, '1kg': 180, '2kg': 300, '3kg': 420, 'extra': 120},
                    'air': {'100gm': 60, '250gm': 100, '500gm': 150, '1kg': 220, '2kg': 380, '3kg': 540, 'extra': 150},
                }
                
                prices = base_prices.get(mode, base_prices['standard'])
                
                price = DefaultStatePrice(
                    state=state,
                    shipping_mode=mode,
                    price_100gm=prices.get('100gm', 0),
                    price_250gm=prices.get('250gm', 0),
                    price_500gm=prices.get('500gm', 0),
                    price_1kg=prices.get('1kg', 120),
                    price_2kg=prices.get('2kg', 0),
                    price_3kg=prices.get('3kg', 0),
                    price_extra_per_kg=prices.get('extra', 80),
                    price_3_10kg=int(prices.get('extra', 80) * 2.5),
                    price_10_25kg=int(prices.get('extra', 80) * 4),
                    price_25_50kg=int(prices.get('extra', 80) * 6),
                    price_50_100kg=int(prices.get('extra', 80) * 8),
                    price_100plus_kg=int(prices.get('extra', 80) * 10),
                )
                db.session.add(price)
    
    db.session.commit()


def create_normal_client_state_prices():
    """Create pricing for normal clients (non-corporate)"""
    for state in INDIAN_STATES:
        for mode in SHIPPING_MODES:
            existing = NormalClientStatePrice.query.filter_by(state=state, shipping_mode=mode).first()
            if not existing:
                # Normal client pricing (slightly cheaper than default)
                base_prices = {
                    'standard': {'100gm': 25, '250gm': 42, '500gm': 65, '1kg': 100, '2kg': 165, '3kg': 230, 'extra': 65},
                    'prime': {'100gm': 33, '250gm': 55, '500gm': 85, '1kg': 125, '2kg': 205, '3kg': 285, 'extra': 85},
                    'prime_express': {'1kg': 155, 'extra': 110, '3_10kg': 100},  # Prime Express special tier
                    'parcel': {'100gm': 28, '250gm': 50, '500gm': 78, '1kg': 115, '2kg': 190, '3kg': 260, 'extra': 75},
                    'state_express': {'100gm': 20, '250gm': 38, '500gm': 58, '1kg': 90, '2kg': 150, '3kg': 210, 'extra': 58},
                    'road_express': {'100gm': 42, '250gm': 68, '500gm': 100, '1kg': 150, '2kg': 250, '3kg': 350, 'extra': 100},
                    'air': {'100gm': 50, '250gm': 85, '500gm': 125, '1kg': 185, '2kg': 315, '3kg': 450, 'extra': 125},
                }
                
                prices = base_prices.get(mode, base_prices['standard'])
                
                price = NormalClientStatePrice(
                    state=state,
                    shipping_mode=mode,
                    price_100gm=prices.get('100gm', 0),
                    price_250gm=prices.get('250gm', 0),
                    price_500gm=prices.get('500gm', 0),
                    price_1kg=prices.get('1kg', 100),
                    price_2kg=prices.get('2kg', 0),
                    price_3kg=prices.get('3kg', 0),
                    price_extra_per_kg=prices.get('extra', 65),
                    price_3_10kg=prices.get('3_10kg', int(prices.get('extra', 65) * 2.2)),
                    price_10_25kg=int(prices.get('extra', 65) * 3.5),
                    price_25_50kg=int(prices.get('extra', 65) * 5),
                    price_50_100kg=int(prices.get('extra', 65) * 7),
                    price_100plus_kg=int(prices.get('extra', 65) * 9),
                )
                db.session.add(price)
    
    db.session.commit()


def create_couriers():
    """Create courier company records"""
    couriers = [
        Courier(name='Example Courier Ltd', service_type='Express', contact_person='John Doe',
                contact_email='john@examplecourier.com', contact_phone='9876543210'),
        Courier(name='Fast Delivery Partners', service_type='Standard', contact_person='Jane Smith',
                contact_email='jane@fastdelivery.com', contact_phone='9876543211'),
        Courier(name='Premium Logistics', service_type='Premium', contact_person='Mike Johnson',
                contact_email='mike@premiumlogistics.com', contact_phone='9876543212'),
        Courier(name='Rural Connect', service_type='Rural', contact_person='Priya Sharma',
                contact_email='priya@ruralconnect.com', contact_phone='9876543213'),
    ]
    
    for courier in couriers:
        if not Courier.query.filter_by(name=courier.name).first():
            db.session.add(courier)
    
    db.session.commit()
    return Courier.query.all()


def create_offers(users):
    """Create promotional offers"""
    offers = [
        Offer(min_amount=200, max_amount=500, offer_amount=30,
              description='30 Rs discount on orders between 200-500',
              created_by=users[0].id),
        Offer(min_amount=500, max_amount=1000, offer_amount=75,
              description='75 Rs discount on orders between 500-1000',
              created_by=users[0].id),
        Offer(min_amount=1000, max_amount=2000, offer_amount=150,
              description='150 Rs discount on orders above 1000',
              created_by=users[0].id),
        Offer(min_amount=100, max_amount=200, offer_amount=10,
              description='10 Rs discount on first orders',
              created_by=users[0].id),
    ]
    
    for offer in offers:
        if not Offer.query.filter_by(min_amount=offer.min_amount, max_amount=offer.max_amount).first():
            db.session.add(offer)
    
    db.session.commit()
    return Offer.query.all()


def create_clients(billing_patterns):
    """Create corporate client records"""
    client_data = [
        {'name': 'Rajesh Kumar', 'company': 'TechFlow Solutions', 'city': 'Mumbai', 'state': 'Maharashtra'},
        {'name': 'Priya Sharma', 'company': 'Fashion Hub India', 'city': 'Delhi', 'state': 'Delhi'},
        {'name': 'Amit Patel', 'company': 'Electronics Plus', 'city': 'Bangalore', 'state': 'Karnataka'},
        {'name': 'Neha Gupta', 'company': 'Health & Wellness', 'city': 'Chennai', 'state': 'Tamil Nadu'},
        {'name': 'Arjun Singh', 'company': 'Business Solutions', 'city': 'Hyderabad', 'state': 'Telangana'},
        {'name': 'Divya Nair', 'company': 'Education Platform', 'city': 'Pune', 'state': 'Maharashtra'},
        {'name': 'Vikram Rao', 'company': 'Manufacturing Co', 'city': 'Kolkata', 'state': 'West Bengal'},
        {'name': 'Sneha Mishra', 'company': 'Retail Networks', 'city': 'Jaipur', 'state': 'Rajasthan'},
    ]
    
    clients = []
    for data in client_data:
        if not Client.query.filter_by(company_name=data['company']).first():
            client = Client(
                name=data['name'],
                company_name=data['company'],
                email=f"{data['name'].lower().replace(' ', '.')}@{data['company'].lower().replace(' ', '')}.com",
                phone=f'98{random.randint(10000000, 99999999)}',
                address=f"{random.randint(100, 999)} {data['city']} Market",
                landmark=f"Near {random.choice(['Railway Station', 'Bus Stand', 'Airport', 'Mall'])}",
                city=data['city'],
                state=data['state'],
                pincode=f"{random.randint(100000, 999999)}",
                gst_number=f"27{random.randint(1000000000000, 9999999999999)}ZX1",
                billing_pattern_id=random.choice(billing_patterns).id,
                billing_date=random.randint(1, 28),
                alt_phone=f'98{random.randint(10000000, 99999999)}',
                alt_email=f"alternate{random.randint(1, 99)}@company.com",
                is_active=True
            )
            db.session.add(client)
            clients.append(client)
    
    db.session.commit()
    return Client.query.all()


def create_client_addresses(clients):
    """Create multiple addresses for clients"""
    address_labels = ['HQ', 'Warehouse', 'Branch Office', 'Secondary Location']
    
    for client in clients:
        # Create 2-3 addresses per client
        for i in range(random.randint(2, 3)):
            address = ClientAddress(
                client_id=client.id,
                address_label=address_labels[i % len(address_labels)],
                address=f"{random.randint(100, 9999)} {random.choice(['Main Road', 'High Street', 'Business Park', 'Industrial Area'])}",
                landmark=f"Near {random.choice(['Metro', 'Bus Stop', 'Hospital', 'School', 'Market'])}",
                city=client.city,
                state=client.state,
                pincode=f"{random.randint(100000, 999999)}"
            )
            db.session.add(address)
    
    db.session.commit()


def create_receivers(clients):
    """Create receiver records for clients"""
    for client in clients:
        # Create 3-5 receivers per client
        for j in range(random.randint(3, 5)):
            receiver = Receiver(
                client_id=client.id,
                name=f"Receiver {j+1}",
                company_name=f"{client.company_name} - Branch {j+1}",
                phone=f'98{random.randint(10000000, 99999999)}',
                alt_phone=f'97{random.randint(10000000, 99999999)}',
                email=f"receiver{j+1}@{client.company_name.lower().replace(' ', '')}.com",
                address=f"{random.randint(100, 9999)} {random.choice(INDIAN_STATES)} Road",
                city=random.choice(INDIAN_STATES),
                state=random.choice(INDIAN_STATES),
                pincode=f"{random.randint(100000, 999999)}"
            )
            db.session.add(receiver)
    
    db.session.commit()


def create_client_state_prices(clients):
    """Create client-specific state prices"""
    for client in clients:
        # Create pricing for 5 key states
        selected_states = random.sample(INDIAN_STATES, 5)
        
        for state in selected_states:
            for mode in SHIPPING_MODES:
                existing = ClientStatePrice.query.filter_by(
                    client_id=client.id, state=state, shipping_mode=mode
                ).first()
                
                if not existing:
                    # Client pricing (typically cheaper than default)
                    base_prices = {
                        'standard': {'100gm': 20, '250gm': 35, '500gm': 55, '1kg': 85, '2kg': 140, '3kg': 190, 'extra': 55},
                        'prime': {'100gm': 28, '250gm': 48, '500gm': 75, '1kg': 110, '2kg': 180, '3kg': 250, 'extra': 75},
                        'prime_express': {'1kg': 135, 'extra': 95, '3_10kg': 85},  # Prime Express special tier
                        'parcel': {'100gm': 23, '250gm': 42, '500gm': 65, '1kg': 100, '2kg': 165, '3kg': 230, 'extra': 65},
                        'state_express': {'100gm': 15, '250gm': 28, '500gm': 45, '1kg': 70, '2kg': 120, '3kg': 170, 'extra': 45},
                        'road_express': {'100gm': 35, '250gm': 55, '500gm': 85, '1kg': 130, '2kg': 220, '3kg': 310, 'extra': 85},
                        'air': {'100gm': 42, '250gm': 70, '500gm': 105, '1kg': 160, '2kg': 270, '3kg': 390, 'extra': 105},
                    }
                    
                    prices = base_prices.get(mode, base_prices['standard'])
                    
                    price = ClientStatePrice(
                        client_id=client.id,
                        state=state,
                        shipping_mode=mode,
                        price_100gm=prices.get('100gm', 0),
                        price_250gm=prices.get('250gm', 0),
                        price_500gm=prices.get('500gm', 0),
                        price_1kg=prices.get('1kg', 85),
                        price_2kg=prices.get('2kg', 0),
                        price_3kg=prices.get('3kg', 0),
                        price_extra_per_kg=prices.get('extra', 55),
                        price_3_10kg=prices.get('3_10kg', int(prices.get('extra', 55) * 2)),
                        price_10_25kg=int(prices.get('extra', 55) * 3),
                        price_25_50kg=int(prices.get('extra', 55) * 4.5),
                        price_50_100kg=int(prices.get('extra', 55) * 6),
                        price_100plus_kg=int(prices['extra'] * 8),
                    )
                    db.session.add(price)
    
    db.session.commit()


def create_receipt_settings(users):
    """Create receipt settings for staff members"""
    branches = Branch.query.all()
    staff_users = User.query.filter_by(role='staff').all()
    
    for i, staff in enumerate(staff_users[:8]):  # Create for first 8 staff members
        existing = StaffReceiptAssignment.query.filter_by(user_id=staff.id).first()
        if not existing:
            assignment = StaffReceiptAssignment(
                user_id=staff.id,
                branch_id=staff.branch_id,
                base_number=f"100371900{100 + i}",
                current_sequence=0,
                assigned_by=users[0].id,  # Admin assigned
                is_active=True
            )
            db.session.add(assignment)
    
    db.session.commit()


def create_orders(clients, users, branches):
    """Create sample orders"""
    orders = []
    staff_users = User.query.filter_by(role='staff').all()
    delivery_users = User.query.filter_by(role='delivery').all()
    
    statuses = ['at_destination', 'confirmed', 'in_transit', 'delivered', 'cancelled']
    payment_statuses = ['unpaid', 'partial', 'paid']
    payment_modes = ['cash', 'card', 'upi', 'credit']
    
    # Create 50 sample orders
    for i in range(50):
        client = random.choice(clients)
        staff = random.choice(staff_users)
        delivery = random.choice(delivery_users) if random.random() > 0.3 else None
        receiver = random.choice(client.receivers) if client.receivers else None
        receiver_address = random.choice(client.addresses) if client.addresses else None
        
        weight = round(random.uniform(0.1, 5), 2)
        receipt_mode = random.choice(SHIPPING_MODES)
        status = random.choice(statuses)
        
        # Calculate pricing (simple example)
        base_amount = 50 + (weight * 50)
        weight_charges = weight * 20
        additional_charges = random.randint(0, 100)
        discount = round(base_amount * random.uniform(0, 0.1), 2)
        tax_amount = round((base_amount + weight_charges + additional_charges - discount) * 0.18, 2)
        total_amount = base_amount + weight_charges + additional_charges - discount + tax_amount
        
        order = Order(
            receipt_number=f"RCP{100000 + i}",
            receipt_type='standard' if random.random() > 0.2 else 'manual',
            order_type=random.choice(['client', 'walkin']),
            receipt_mode=receipt_mode,
            customer_name=client.name if random.random() > 0.5 else f"Customer {i+1}",
            customer_phone=client.phone,
            customer_email=client.email,
            customer_address=client.address,
            customer_landmark=client.landmark,
            customer_city=client.city,
            customer_state=client.state,
            customer_pincode=client.pincode,
            receiver_name=receiver.name if receiver else f"Receiver {i+1}",
            receiver_phone=receiver.phone if receiver else f"98{random.randint(10000000, 99999999)}",
            receiver_address=receiver.address if receiver else f"Address {i+1}",
            receiver_city=receiver.city if receiver else random.choice(INDIAN_STATES),
            receiver_state=receiver.state if receiver else random.choice(INDIAN_STATES),
            receiver_pincode=receiver.pincode if receiver else f"{random.randint(100000, 999999)}",
            package_description=random.choice(['Documents', 'Books', 'Electronics', 'Clothing', 'Gifts', 'Sample Products']),
            weight=weight,
            weight_in_kg=weight,
            number_of_boxes=random.randint(1, 5),
            price_list_type=random.choice(['default', 'normal_client']),
            base_amount=base_amount,
            weight_charges=weight_charges,
            additional_charges=additional_charges,
            discount=discount,
            tax_amount=tax_amount,
            total_amount=total_amount,
            calculated_amount=total_amount,
            received_amount=total_amount if random.random() > 0.3 else 0,
            status=status,
            payment_status=random.choice(payment_statuses),
            payment_mode=random.choice(payment_modes),
            client_id=client.id,
            branch_id=staff.branch_id,
            created_by=staff.id,
            delivery_person_id=delivery.id if delivery else None,
            created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30)),
        )
        
        order.generate_tracking_link()
        order.generate_customer_form_link()
        
        db.session.add(order)
        orders.append(order)
    
    db.session.commit()
    return Order.query.all()


def create_tracking_updates(orders, users):
    """Create tracking updates for orders"""
    locations = ['Order Received', 'In Transit', 'Out for Delivery', 'Delivered', 'Returned']
    descriptions = {
        'Order Received': 'Your order has been received at our facility',
        'In Transit': 'Your package is on the way',
        'Out for Delivery': 'Your package is out for delivery today',
        'Delivered': 'Your package has been delivered',
        'Returned': 'Package returned to sender'
    }
    
    for order in orders[:30]:  # Add tracking for first 30 orders
        # Add 2-4 tracking updates per order
        num_updates = random.randint(2, 4)
        for j in range(num_updates):
            status = locations[j % len(locations)]
            update = TrackingUpdate(
                order_id=order.id,
                status=status,
                location=f"{random.choice(INDIAN_STATES)}, India",
                description=descriptions.get(status, 'Status update'),
                updated_by=random.choice(users).id,
                created_at=order.created_at + timedelta(hours=j*6)
            )
            db.session.add(update)
    
    db.session.commit()


def create_sales_visits(users):
    """Create sales visit records"""
    managers = User.query.filter_by(role='manager').all()
    companies = [
        'ABC Trading Company', 'XYZ Exports', 'Global Logistics', 'Modern Retail',
        'Tech Innovations', 'Fashion Forward', 'Health Supplies', 'Manufacturing Hub'
    ]
    
    visits = []
    for i in range(12):
        visit = SalesVisit(
            contact_name=f"Contact Person {i+1}",
            contact_phone=f'98{random.randint(10000000, 99999999)}',
            contact_email=f"contact{i+1}@company.com",
            contact_designation=random.choice(['Managing Director', 'Operations Head', 'Logistics Manager']),
            company_name=random.choice(companies),
            company_address=f"{random.randint(100, 999)} Business District, {random.choice(INDIAN_STATES)}",
            company_city=random.choice(INDIAN_STATES),
            company_state=random.choice(INDIAN_STATES),
            covered_area=f"{random.choice(INDIAN_STATES)} and nearby states",
            load_frequency=random.choice(['Daily', 'Weekly', 'Monthly']),
            load_capacity=f"{random.randint(5, 50)} shipments per {random.choice(['day', 'week'])}",
            current_courier=random.choice(['Competitor A', 'Competitor B', 'Multiple couriers']),
            price_cert='Rate per kg applicable',
            desired_price='Negotiable based on volume',
            pitch_notes='High potential client with growing business',
            status=random.choice(['new', 'follow_up', 'converted', 'lost']),
            created_by=random.choice(managers).id if managers else users[0].id,
            visit_date=datetime.utcnow() - timedelta(days=random.randint(0, 60))
        )
        db.session.add(visit)
        visits.append(visit)
    
    db.session.commit()
    return SalesVisit.query.all()


def create_follow_ups(sales_visits, users):
    """Create follow-up records for sales visits"""
    for visit in sales_visits:
        # Create 1-3 follow-ups per visit
        for j in range(random.randint(1, 3)):
            follow_up = FollowUp(
                visit_id=visit.id,
                notes=random.choice([
                    'Discussed pricing and services',
                    'Client interested in partnership',
                    'Need to provide demo and quotation',
                    'Awaiting client decision',
                    'Follow-up meeting scheduled'
                ]),
                follow_up_date=visit.visit_date + timedelta(days=random.randint(3, 14)),
                status=random.choice(['pending', 'done', 'skipped']),
                created_by=random.choice(users).id
            )
            db.session.add(follow_up)
    
    db.session.commit()


def create_meetings(sales_visits, users):
    """Create meeting records for sales visits"""
    for visit in sales_visits:
        if random.random() > 0.4:  # 60% of visits have meetings scheduled
            # Create 1-2 meetings per visit
            for k in range(random.randint(1, 2)):
                meeting = Meeting(
                    visit_id=visit.id,
                    scheduled_at=visit.visit_date + timedelta(days=random.randint(1, 10)),
                    location=visit.company_address,
                    notes=random.choice([
                        'Product demonstration',
                        'Pricing negotiation',
                        'Contract review',
                        'Partnership discussion'
                    ]),
                    status=random.choice(['scheduled', 'completed', 'cancelled', 'rescheduled']),
                    created_by=random.choice(users).id
                )
                db.session.add(meeting)
    
    db.session.commit()


if __name__ == '__main__':
    create_demo_database()
