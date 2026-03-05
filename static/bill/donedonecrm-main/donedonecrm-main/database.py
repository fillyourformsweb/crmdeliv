# database.py - Fixed version
from datetime import datetime, timedelta
import random
from app import app, db, User, Task, Service, Branch, Customer, TaskStatusHistory, TaskPayment, TaskMessage, BranchNew, Role, Priority, Status, Typecustomer, Normalservice, Quickservice, Attendance
import bcrypt

def create_dummy_data():
    """Create dummy data for testing"""
    print("Creating dummy data...")
    
    # First, let's check if tables exist and create them if not
    db.create_all()
    
    # Clear existing data but keep admin user
    print("Clearing existing data (keeping admin user)...")
    
    # Delete in correct order to avoid foreign key constraints
    TaskStatusHistory.query.delete()
    TaskPayment.query.delete()
    TaskMessage.query.delete()
    Task.query.delete()
    Customer.query.delete()
    Attendance.query.delete()
    
    # Delete all users except admin
    User.query.filter(User.useridname != 'admin').delete()
    
    Service.query.delete()
    BranchNew.query.delete()
    Role.query.delete()
    Priority.query.delete()
    Status.query.delete()
    Typecustomer.query.delete()
    Normalservice.query.delete()
    Quickservice.query.delete()
    
    db.session.commit()
    
    # Create roles
    roles_data = [
        {'roleidname': 'admin', 'rolename': 'Administrator', 'roledetails': 'System administrator with full access'},
        {'roleidname': 'manager', 'rolename': 'Branch Manager', 'roledetails': 'Manages branch operations and staff'},
        {'roleidname': 'staff', 'rolename': 'Staff Member', 'roledetails': 'Regular staff member'},
        {'roleidname': 'technician', 'rolename': 'Technician', 'roledetails': 'Technical service provider'},
        {'roleidname': 'supervisor', 'rolename': 'Supervisor', 'roledetails': 'Team supervisor'}
    ]
    
    for role_data in roles_data:
        role = Role(**role_data)
        db.session.add(role)
    
    # Create priorities
    priorities_data = [
        {'priorityid': 1, 'priorityname': 'Low', 'prioritydetails': 'Low priority tasks'},
        {'priorityid': 2, 'priorityname': 'Medium', 'prioritydetails': 'Medium priority tasks'},
        {'priorityid': 3, 'priorityname': 'High', 'prioritydetails': 'High priority tasks'},
        {'priorityid': 4, 'priorityname': 'Urgent', 'prioritydetails': 'Urgent priority tasks'}
    ]
    
    for priority_data in priorities_data:
        priority = Priority(**priority_data)
        db.session.add(priority)
    
    # Create statuses
    statuses_data = [
        {'statusid': 1, 'statusname': 'Pending', 'statusdetails': 'Task is pending assignment'},
        {'statusid': 2, 'statusname': 'in_progress', 'statusdetails': 'Task is in progress'},
        {'statusid': 3, 'statusname': 'On Hold', 'statusdetails': 'Task is on hold'},
        {'statusid': 4, 'statusname': 'Completed', 'statusdetails': 'Task is completed'},
        {'statusid': 5, 'statusname': 'Cancelled', 'statusdetails': 'Task is cancelled'}
    ]
    
    for status_data in statuses_data:
        status = Status(**status_data)
        db.session.add(status)
    
    # Create customer types
    customer_types = [
        {'typecustomerid': 1, 'typecustomername': 'Regular', 'typecustomerdetails': 'Regular customer'},
        {'typecustomerid': 2, 'typecustomername': 'Premium', 'typecustomerdetails': 'Premium customer'},
        {'typecustomerid': 3, 'typecustomername': 'VIP', 'typecustomerdetails': 'VIP customer'},
        {'typecustomerid': 4, 'typecustomername': 'Corporate', 'typecustomerdetails': 'Corporate customer'}
    ]
    
    for type_data in customer_types:
        typecustomer = Typecustomer(**type_data)
        db.session.add(typecustomer)
    
    # Create normal services
    normal_services = [
        {
            'normalserviceid': 1,
            'normalservicename': 'AC Repair',
            'normalserviceprice': 1400.0,
            'normalservicefees': 200.0,
            'normalservicecharges': 1200.0,
            'normalservicelink': '/services/ac-repair',
            'normalservicedetails': 'Air conditioner repair and maintenance'
        },
        {
            'normalserviceid': 2,
            'normalservicename': 'Plumbing Service',
            'normalserviceprice': 950.0,
            'normalservicefees': 150.0,
            'normalservicecharges': 800.0,
            'normalservicelink': '/services/plumbing',
            'normalservicedetails': 'Plumbing repair and installation'
        },
        {
            'normalserviceid': 3,
            'normalservicename': 'Electrical Work',
            'normalserviceprice': 1800.0,
            'normalservicefees': 300.0,
            'normalservicecharges': 1500.0,
            'normalservicelink': '/services/electrical',
            'normalservicedetails': 'Electrical repairs and installations'
        }
    ]
    
    for service_data in normal_services:
        service = Normalservice(**service_data)
        db.session.add(service)
    
    # Create quick services
    quick_services = [
        {'quickserviceid': 1, 'quickservicename': 'Quick Fix', 'quickserviceprice': 500.0},
        {'quickserviceid': 2, 'quickservicename': 'Emergency Call', 'quickserviceprice': 1000.0},
        {'quickserviceid': 3, 'quickservicename': 'Consultation', 'quickserviceprice': 300.0}
    ]
    
    for service_data in quick_services:
        service = Quickservice(**service_data)
        db.session.add(service)
    
    db.session.commit()
    print("✅ Basic data created")
    
    # Create branches
    branches_data = [
        {
            'code': 'BR001',
            'name': 'Main Branch',
            'address': '123 Main Street, City Center',
            'phone': '9876543210',
            'email': 'main@servicehub.com',
            'manager': 'John Manager',
            'status': 'active'
        },
        {
            'code': 'BR002',
            'name': 'North Branch',
            'address': '456 North Avenue, North City',
            'phone': '9876543211',
            'email': 'north@servicehub.com',
            'manager': 'Sarah Manager',
            'status': 'active'
        },
        {
            'code': 'BR003',
            'name': 'South Branch',
            'address': '789 South Road, South City',
            'phone': '9876543212',
            'email': 'south@servicehub.com',
            'manager': 'Mike Manager',
            'status': 'active'
        }
    ]
    
    for branch_data in branches_data:
        branch = BranchNew(**branch_data)
        db.session.add(branch)
    
    db.session.commit()
    print("✅ Branches created")
    
    # Create services
    services_data = [
        {
            'service_code': 'SRV001',
            'name': 'Air Conditioner Service',
            'service_type': 'normal',
            'price': 1400.0,
            'fee': 200.0,
            'charge': 1200.0,
            'description': 'Complete AC servicing including cleaning and gas refill',
            'estimated_time': '2 hours',
            'department': 'HVAC',
            'status': 'active'
        },
        {
            'service_code': 'SRV002',
            'name': 'Refrigerator Repair',
            'service_type': 'normal',
            'price': 1750.0,
            'fee': 250.0,
            'charge': 1500.0,
            'description': 'Refrigerator repair and maintenance',
            'estimated_time': '3 hours',
            'department': 'Appliances',
            'status': 'active'
        },
        {
            'service_code': 'SRV003',
            'name': 'Washing Machine Repair',
            'service_type': 'normal',
            'price': 1150.0,
            'fee': 150.0,
            'charge': 1000.0,
            'description': 'Washing machine repair service',
            'estimated_time': '2.5 hours',
            'department': 'Appliances',
            'status': 'active'
        },
        {
            'service_code': 'SRV004',
            'name': 'Plumbing Service',
            'service_type': 'normal',
            'price': 920.0,
            'fee': 120.0,
            'charge': 800.0,
            'description': 'Plumbing repairs and installations',
            'estimated_time': '1.5 hours',
            'department': 'Plumbing',
            'status': 'active'
        },
        {
            'service_code': 'SRV005',
            'name': 'Electrical Work',
            'service_type': 'normal',
            'price': 700.0,
            'fee': 100.0,
            'charge': 600.0,
            'description': 'Electrical repairs and wiring',
            'estimated_time': '2 hours',
            'department': 'Electrical',
            'status': 'active'
        }
    ]
    
    for service_data in services_data:
        service = Service(**service_data)
        db.session.add(service)
    
    db.session.commit()
    print("✅ Services created")
    
    # Create users (skip admin since it already exists)
    users_data = [
      
    {
        'useridname': 'manager1',
        'post': 'Manager',
        'username': 'John Manager',
        'userfathername': 'Manager Father',
        'usermothername': 'Manager Mother',
        'dateofbirth': datetime(1985, 5, 15).date(),
        'useremail': 'manager1@servicehub.com',  # Unique
        'userphone': '9876543201',
        'useremergencycontact': '9876543298',
        'useraddress': 'Manager Address 1',
        'userpannumber': 'BCDEF1234G',
        'useraadharnumber': '234567890123',
        'userdateofjoining': datetime(2021, 3, 15).date(),
        'permanentaddressuser': 'Permanent Manager Address',
        'currentaddressuser': 'Current Manager Address',
        'promationdate': datetime(2022, 3, 15).date(),
        'is_active': True,
        'branch_id': 1,  # Main Branch
        'department': 'Management',
        'designation': 'Branch Manager'
    },
    {
        'useridname': 'manager2',
        'post': 'Manager',
        'username': 'Sarah Manager',
        'userfathername': 'Manager Father 2',
        'usermothername': 'Manager Mother 2',
        'dateofbirth': datetime(1986, 8, 22).date(),
        'useremail': 'manager2@servicehub.com',  # Unique
        'userphone': '9876543205',
        'useremergencycontact': '9876543294',
        'useraddress': 'Manager Address 2',
        'userpannumber': 'FGHIJ1234K',
        'useraadharnumber': '678901234567',
        'userdateofjoining': datetime(2021, 7, 1).date(),
        'permanentaddressuser': 'Permanent Manager Address 2',
        'currentaddressuser': 'Current Manager Address 2',
        'is_active': True,
        'branch_id': 2,  # North Branch
        'department': 'Management',
        'designation': 'Branch Manager'
    },
    {
        'useridname': 'staff1',
        'post': 'Staff',
        'username': 'Alice Technician',
        'userfathername': 'Staff Father',
        'usermothername': 'Staff Mother',
        'dateofbirth': datetime(1990, 8, 20).date(),
        'useremail': 'staff1@servicehub.com',  # Unique
        'userphone': '9876543202',
        'useremergencycontact': '9876543297',
        'useraddress': 'Staff Address 1',
        'userpannumber': 'CDEFG1234H',
        'useraadharnumber': '345678901234',
        'userdateofjoining': datetime(2022, 1, 10).date(),
        'permanentaddressuser': 'Permanent Staff Address',
        'currentaddressuser': 'Current Staff Address',
        'is_active': True,
        'branch_id': 1,  # Main Branch
        'department': 'HVAC',
        'designation': 'AC Technician'
    },
    {
        'useridname': 'staff2',
        'post': 'Staff',
        'username': 'Bob Technician',
        'userfathername': 'Staff Father 2',
        'usermothername': 'Staff Mother 2',
        'dateofbirth': datetime(1992, 3, 25).date(),
        'useremail': 'staff2@servicehub.com',  # Original
        'userphone': '9876543203',
        'useremergencycontact': '9876543296',
        'useraddress': 'Staff Address 2',
        'userpannumber': 'DEFGH1234I',
        'useraadharnumber': '456789012345',
        'userdateofjoining': datetime(2022, 6, 1).date(),
        'permanentaddressuser': 'Permanent Staff Address 2',
        'currentaddressuser': 'Current Staff Address 2',
        'is_active': True,
        'branch_id': 1,  # Main Branch
        'department': 'Electrical',
        'designation': 'Electrician'
    },
    {
        'useridname': 'staff3',
        'post': 'Staff',
        'username': 'Charlie Technician',
        'userfathername': 'Staff Father 3',
        'usermothername': 'Staff Mother 3',
        'dateofbirth': datetime(1993, 11, 5).date(),
        'useremail': 'staff3@servicehub.com',  # Unique
        'userphone': '9876543204',
        'useremergencycontact': '9876543295',
        'useraddress': 'Staff Address 3',
        'userpannumber': 'EFGHI1234J',
        'useraadharnumber': '567890123456',
        'userdateofjoining': datetime(2023, 2, 15).date(),
        'permanentaddressuser': 'Permanent Staff Address 3',
        'currentaddressuser': 'Current Staff Address 3',
        'is_active': True,
        'branch_id': 2,  # North Branch
        'department': 'Plumbing',
        'designation': 'Plumber'
    },
    {
        'useridname': 'staff4',
        'post': 'Staff',
        'username': 'David Technician',
        'userfathername': 'Staff Father 4',
        'usermothername': 'Staff Mother 4',
        'dateofbirth': datetime(1991, 7, 12).date(),
        'useremail': 'staff4@servicehub.com',  # Changed to unique
        'userphone': '9876543206',
        'useremergencycontact': '9876543293',
        'useraddress': 'Staff Address 4',
        'userpannumber': 'GHIJK1234L',
        'useraadharnumber': '678901234567',
        'userdateofjoining': datetime(2022, 8, 20).date(),
        'permanentaddressuser': 'Permanent Staff Address 4',
        'currentaddressuser': 'Current Staff Address 4',
        'is_active': True,
        'branch_id': 3,  # South Branch
        'department': 'Electrical',
        'designation': 'Electrician'
    },
    {
        'useridname': 'staff5',
        'post': 'Staff',
        'username': 'Emma Technician',
        'userfathername': 'Staff Father 5',
        'usermothername': 'Staff Mother 5',
        'dateofbirth': datetime(1994, 2, 28).date(),
        'useremail': 'staff5@servicehub.com',  # Changed to unique
        'userphone': '9876543207',
        'useremergencycontact': '9876543292',
        'useraddress': 'Staff Address 5',
        'userpannumber': 'HIJKL1234M',
        'useraadharnumber': '789012345678',
        'userdateofjoining': datetime(2023, 3, 10).date(),
        'permanentaddressuser': 'Permanent Staff Address 5',
        'currentaddressuser': 'Current Staff Address 5',
        'is_active': True,
        'branch_id': 1,  # Main Branch
        'department': 'Plumbing',
        'designation': 'Plumber'
    },
    {
        'useridname': 'staff6',
        'post': 'Staff',
        'username': 'Frank Technician',
        'userfathername': 'Staff Father 6',
        'usermothername': 'Staff Mother 6',
        'dateofbirth': datetime(1989, 12, 5).date(),
        'useremail': 'staff6@servicehub.com',  # Changed to unique
        'userphone': '9876543208',
        'useremergencycontact': '9876543291',
        'useraddress': 'Staff Address 6',
        'userpannumber': 'IJKLM1234N',
        'useraadharnumber': '890123456789',
        'userdateofjoining': datetime(2021, 11, 15).date(),
        'permanentaddressuser': 'Permanent Staff Address 6',
        'currentaddressuser': 'Current Staff Address 6',
        'is_active': True,
        'branch_id': 2,  # North Branch
        'department': 'HVAC',
        'designation': 'AC Technician'
    },
    {
        'useridname': 'staff7',
        'post': 'Staff',
        'username': 'Grace Technician',
        'userfathername': 'Staff Father 7',
        'usermothername': 'Staff Mother 7',
        'dateofbirth': datetime(1995, 6, 18).date(),
        'useremail': 'staff7@servicehub.com',  # Changed to unique
        'userphone': '9876543209',
        'useremergencycontact': '9876543290',
        'useraddress': 'Staff Address 7',
        'userpannumber': 'JKLMN1234O',
        'useraadharnumber': '901234567890',
        'userdateofjoining': datetime(2023, 5, 5).date(),
        'permanentaddressuser': 'Permanent Staff Address 7',
        'currentaddressuser': 'Current Staff Address 7',
        'is_active': True,
        'branch_id': 2,  # North Branch
        'department': 'Electrical',
        'designation': 'Electrician'
    }
]
    for user_data in users_data:
        # Check if user already exists
        existing_user = User.query.filter_by(useridname=user_data['useridname']).first()
        if not existing_user:
            user = User(**user_data)
            user.set_password('password123')
            db.session.add(user)
            print(f"Created user: {user_data['useridname']}")
        else:
            print(f"User already exists: {user_data['useridname']}")
            # Update existing user with new data
            for key, value in user_data.items():
                if hasattr(existing_user, key):
                    setattr(existing_user, key, value)
    
    db.session.commit()
    print("✅ Users created/updated")
    
    # Create customers
    customers_data = [
        {
            'phone': '9876543300',
            'name': 'Rahul Sharma',
            'email': 'rahul.sharma@gmail.com',
            'address': '123 Customer Street, City',
            'total_services': 3,
            'total_spent': 4500.0,
            'last_service_date': datetime.now() - timedelta(days=15)
        },
        {
            'phone': '9876543301',
            'name': 'Priya Patel',
            'email': 'priya.patel@gmail.com',
            'address': '456 Customer Lane, City',
            'total_services': 2,
            'total_spent': 2800.0,
            'last_service_date': datetime.now() - timedelta(days=30)
        },
        {
            'phone': '9876543302',
            'name': 'Amit Verma',
            'email': 'amit.verma@gmail.com',
            'address': '789 Customer Road, City',
            'total_services': 5,
            'total_spent': 7200.0,
            'last_service_date': datetime.now() - timedelta(days=10)
        },
        {
            'phone': '9876543303',
            'name': 'Sneha Reddy',
            'email': 'sneha.reddy@gmail.com',
            'address': '101 Customer Avenue, City',
            'total_services': 1,
            'total_spent': 1400.0,
            'last_service_date': datetime.now() - timedelta(days=45)
        },
        {
            'phone': '9876543304',
            'name': 'Vikram Singh',
            'email': 'vikram.singh@gmail.com',
            'address': '202 Customer Boulevard, City',
            'total_services': 4,
            'total_spent': 5600.0,
            'last_service_date': datetime.now() - timedelta(days=5)
        }
    ]
    
    for customer_data in customers_data:
        customer = Customer(**customer_data)
        db.session.add(customer)
    
    db.session.commit()
    print("✅ Customers created")
    
    # Get created entities
    users = User.query.all()
    services = Service.query.all()
    branches = BranchNew.query.all()
    customers = Customer.query.all()
    
    print(f"Creating tasks with {len(users)} users, {len(services)} services, {len(branches)} branches, {len(customers)} customers")
    
    # Create sample tasks
    status_options = ['pending', 'in_progress', 'on_hold', 'completed']
    priority_options = ['low', 'medium', 'high', 'urgent']
    
    for i in range(200):  # Create 15 tasks
        # Random customer
        customer = random.choice(customers)
        
        # Random service
        service = random.choice(services)
        
        # Random assignment - skip admin (users[0])
        available_users = [u for u in users if u.useridname != 'admin']
        assigned_user = random.choice(available_users) if i % 3 != 0 else None  # Some tasks unassigned
        
        # Random branch
        branch = random.choice(branches) if branches else None
        
        # Random dates
        created_date = datetime.now() - timedelta(days=random.randint(0, 30))
        updated_date = created_date + timedelta(hours=random.randint(1, 72))
        
        # Generate order number
        order_no = f'ORD-{created_date.strftime("%Y%m%d")}-{i+1:04d}'
        
        # Random status
        status = random.choice(status_options)
        
        # Random priority
        priority = random.choice(priority_options)
        
        is_self_pay = random.choice([True, False])
        
        # Calculate amounts
        # Regular: target is Total (price)
        # Self-Pay: target is Fee (fee)
        target_amount = service.fee if is_self_pay else service.price
        
        total_amount = target_amount + random.uniform(0, 50)
        paid_amount = total_amount * random.uniform(0.5, 1.0)
        due_amount = total_amount - paid_amount
        
        # Create task
        task = Task(
            order_no=order_no,
            customer_name=customer.name,
            customer_phone=customer.phone,
            customer_email=customer.email,
            customer_type=random.choice(['visiting', 'online']),
            customer_password=f'pass{i+1:03d}',
            
            service_id=service.id,
            service_name=service.name,
            service_price=service.price,
            service_fee=service.fee,
            service_charge=service.charge,
            
            assigned_to_id=assigned_user.id if assigned_user else None,
            assigned_to_name=assigned_user.username if assigned_user else None,
            assigned_at=created_date + timedelta(hours=1) if assigned_user else None,
            
            branch_id=branch.id if branch else None,
            branch_name=branch.name if branch else None,
            
            payment_mode=random.choice(['cash', 'card', 'upi', 'online']),
            total_amount=total_amount,
            paid_amount=paid_amount,
            due_amount=due_amount,
            
            status=status,
            priority=priority,
            department=service.department,
            
            created_by_id=users[0].id,  # Admin created all
            created_at=created_date,
            updated_at=updated_date,
            
            description=f'Task description for {service.name} at {customer.name}\'s place',
            
            in_openplace=(assigned_user is None and status == 'pending'),
            assignment_type='openplace' if assigned_user is None else 'specific',
            
            is_self_pay=is_self_pay,
            is_hybrid=random.choice([True, False])
        )
        
        if task.is_self_pay:
            task.self_pay_service_price = service.price
            task.self_pay_service_fee = service.fee
            task.self_pay_customer_pays = service.charge
            task.self_pay_revenue = service.fee
        
        if task.is_hybrid:
            task.online_payment = total_amount * 0.6
            task.cash_payment = total_amount * 0.4
        
        if status == 'completed':
            task.completed_at = updated_date
            task.completion_notes = f'Task completed successfully. Notes: {service.name} was serviced properly.'
        
        db.session.add(task)
        db.session.flush()  # Get task ID
        
        # Add status history
        status_history = TaskStatusHistory(
            task_id=task.id,
            old_status=None,
            new_status='pending',
            reason='Task created',
            changed_by='System'
        )
        db.session.add(status_history)
        
        if status != 'pending':
            status_history2 = TaskStatusHistory(
                task_id=task.id,
                old_status='pending',
                new_status=status,
                reason=f'Status updated to {status}',
                changed_by=assigned_user.username if assigned_user else 'System'
            )
            db.session.add(status_history2)
        
        # Add payments if any
        if paid_amount > 0:
            payment = TaskPayment(
                task_id=task.id,
                amount=paid_amount,
                payment_mode=task.payment_mode,
                payment_date=created_date + timedelta(minutes=30),
                collected_by='System',
                notes='Initial payment'
            )
            db.session.add(payment)
        
        # Add some messages
        if random.choice([True, False]):
            message = TaskMessage(
                task_id=task.id,
                sender_type='customer',
                sender_name=customer.name,
                message=f'Hello, I need updates on my {service.name} service.',
                created_at=created_date + timedelta(hours=2)
            )
            db.session.add(message)
            
            if assigned_user:
                reply = TaskMessage(
                    task_id=task.id,
                    sender_type='staff',
                    sender_id=assigned_user.id,
                    sender_name=assigned_user.username,
                    message=f'We have assigned your {service.name} request to our technician.',
                    created_at=created_date + timedelta(hours=3)
                )
                db.session.add(reply)
    
    # Create attendance records for today
    today = datetime.now().date()
    for user in [u for u in users if u.useridname != 'admin']:  # Skip admin
        check_in_time = datetime.combine(today, datetime.strptime('09:00', '%H:%M').time())
        check_out_time = datetime.combine(today, datetime.strptime('18:00', '%H:%M').time())
        
        attendance = Attendance(
            user_id=user.id,
            branch_id=1 if branches else None,  # Main branch
            branch_name='Main Branch' if branches else 'Default',
            check_in=check_in_time,
            check_out=check_out_time,
            total_hours=9.0,
            status='checked_out'
        )
        db.session.add(attendance)
    
    db.session.commit()
    
    
    print(f"✅ Dummy data created successfully!")
    print(f"   - Tasks: {Task.query.count()}")
    print(f"   - Users: {User.query.count()}")
    print(f"   - Customers: {Customer.query.count()}")
    print(f"   - Services: {Service.query.count()}")
    print(f"   - Branches: {BranchNew.query.count()}")
    print("\n📋 Login credentials:")
    print("   - Admin: admin / admin123")
    print("   - Manager 1: manager1 / password123 (Main Branch)")
    print("   - Manager 2: manager2 / password123 (North Branch)")
    print("   - Staff 1: staff1 / password123 (Main Branch - HVAC)")
    print("   - Staff 2: staff2 / password123 (Main Branch - Electrical)")
    print("   - Staff 3: staff3 / password123 (North Branch - Plumbing)")

if __name__ == '__main__':
    with app.app_context():
        create_dummy_data()