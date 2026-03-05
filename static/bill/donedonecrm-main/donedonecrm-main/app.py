from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, event
from functools import wraps

import json
from datetime import datetime, timedelta, timezone  
import atexit
import bcrypt
import re
import os
import traceback
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename
import chat_db

app = Flask(__name__)

# Use ProxyFix to handle X-Forwarded-Proto for AWS Load Balancer
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Use a stronger secret key
app.secret_key = os.urandom(24)

app.config['SECRET_KEY'] = '16530303.1651yvykbuuuij'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7) 
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

db = SQLAlchemy(app)

# ================= MODELS =================
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    address = db.Column(db.Text)
    total_services = db.Column(db.Integer, default=0)
    total_spent = db.Column(db.Float, default=0)
    last_service_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

# ================= NOTIFICATION MODEL =================
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)
    notification_type = db.Column(db.String(50), nullable=False)  # task_assigned, status_change, message, etc.
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    read_at = db.Column(db.DateTime)
    
    user = db.relationship('User', backref='notifications', lazy=True)

class TaskMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    sender_type = db.Column(db.String(20), nullable=False)  # staff, customer, system
    sender_id = db.Column(db.Integer, nullable=True)  # User ID if staff, None if customer/system
    sender_name = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    read_by = db.Column(db.String(100))
    read_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # File attachments (optional)
    attachment_url = db.Column(db.String(500))
    attachment_name = db.Column(db.String(200))

class TaskExtraCharge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    charge_type = db.Column(db.String(50), nullable=False)  # tax, bank, other
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    added_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    added_by = db.Column(db.String(100))  

class TaskPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_mode = db.Column(db.String(20), nullable=False)
    payment_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    collected_by = db.Column(db.String(100))
    notes = db.Column(db.Text)
    is_self_pay = db.Column(db.Boolean, default=False)
    self_pay_provider_name = db.Column(db.String(100))
    self_pay_provider_phone = db.Column(db.String(15)) 

class TaskStatusHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    old_status = db.Column(db.String(20))
    new_status = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.Text)
    changed_by = db.Column(db.String(100), nullable=False)
    changed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    notification_sent = db.Column(db.Boolean, default=False)
    notification_to_customer = db.Column(db.Text) 

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(50), unique=True, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(15), nullable=False)
    customer_email = db.Column(db.String(100))
    customer_type = db.Column(db.String(20), default='visiting')  # visiting, online
    customer_password = db.Column(db.String(50))  # Password for customer to access task
    
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    service_name = db.Column(db.String(200), nullable=False)
    service_price = db.Column(db.Float, nullable=False)
    service_fee = db.Column(db.Float, default=0)
    service_charge = db.Column(db.Float, default=0)
    
    # Assignment
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    assigned_to_name = db.Column(db.String(100))
    assigned_at = db.Column(db.DateTime)
    assignment_type = db.Column(db.String(20), default='specific')  # specific, openplace, myself
    in_openplace = db.Column(db.Boolean, default=False)
    sent_to_openplace_at = db.Column(db.DateTime)
    sent_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    sent_by_name = db.Column(db.String(100))
    
    # Branch information
    branch_id = db.Column(db.Integer, db.ForeignKey('branch_new.id'), nullable=True)
    branch_name = db.Column(db.String(100))
    
    # Payment
    payment_mode = db.Column(db.String(20))  # cash, card, upi, online, bank_transfer, self_pay, hybrid
    total_amount = db.Column(db.Float, nullable=False)
    paid_amount = db.Column(db.Float, default=0)
    due_amount = db.Column(db.Float, default=0)
    
    # Self-pay specific
    is_self_pay = db.Column(db.Boolean, default=False)
    self_pay_service_price = db.Column(db.Float, default=0)
    self_pay_service_fee = db.Column(db.Float, default=0)
    self_pay_customer_pays = db.Column(db.Float, default=0)
    self_pay_revenue = db.Column(db.Float, default=0)
    
    # Hybrid payment
    is_hybrid = db.Column(db.Boolean, default=False)
    online_payment = db.Column(db.Float, default=0)
    cash_payment = db.Column(db.Float, default=0)
    
    # Status
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, on_hold, completed, cancelled
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    department = db.Column(db.String(100))
    
    # Timestamps
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime)
    
    # Description and notes
    description = db.Column(db.Text)
    completion_notes = db.Column(db.Text)
    
    # Offer/Discount tracking
    is_offer = db.Column(db.Boolean, default=False)
    offer_reason = db.Column(db.Text)
    offer_amount = db.Column(db.Float, default=0)
    
    # Relationships
    service = db.relationship('Service', backref='tasks', lazy=True)
    branch = db.relationship('BranchNew', backref='tasks', lazy=True)
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id], backref='tasks_assigned', lazy=True)
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='tasks_created', lazy=True)
    sent_by = db.relationship('User', foreign_keys=[sent_by_id], backref='tasks_sent_to_openplace', lazy=True)
    status_history = db.relationship('TaskStatusHistory', backref='task', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('TaskPayment', backref='task', lazy=True, cascade='all, delete-orphan')
    extra_charges = db.relationship('TaskExtraCharge', backref='task', lazy=True, cascade='all, delete-orphan')
    messages = db.relationship('TaskMessage', backref='task', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_no': self.order_no,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'customer_email': self.customer_email,
            'customer_type': self.customer_type,
            'service_id': self.service_id,
            'service_name': self.service_name,
            'service_price': self.service_price,
            'service_fee': self.service_fee,
            'service_charge': self.service_charge,
            'assigned_to': self.assigned_to_name,
            'assigned_to_name': self.assigned_to_name,
            'assigned_to_id': self.assigned_to_id,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'branch_name': self.branch_name,
            'branch_id': self.branch_id,
            'status': self.status,
            'priority': self.priority,
            'department': self.department,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by.useridname if self.created_by else None,
            'total_amount': self.total_amount,
            'paid_amount': self.paid_amount,
            'due_amount': self.due_amount,
            'payment_mode': self.payment_mode,
            'is_self_pay': self.is_self_pay,
            'is_hybrid': self.is_hybrid,
            'online_payment': self.online_payment,
            'cash_payment': self.cash_payment,
            'in_openplace': self.in_openplace,
            'sent_by_name': self.sent_by_name,
            'description': self.description,
            'completion_notes': self.completion_notes,
            'is_offer': self.is_offer,
            'offer_reason': self.offer_reason,
            'offer_amount': self.offer_amount,
            'service_type': self.service.service_type if self.service else 'normal',
            'self_pay_revenue': self.self_pay_revenue or 0
        }

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    useridname = db.Column(db.String(50), unique=True, nullable=False)
    post = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    userfathername = db.Column(db.String(100), nullable=False)
    usermothername = db.Column(db.String(100), nullable=False)
    dateofbirth = db.Column(db.Date, nullable=False)
    useremail = db.Column(db.String(100), unique=True, nullable=False)
    userphone = db.Column(db.String(15), nullable=False)
    useremergencycontact = db.Column(db.String(15))
    useraddress = db.Column(db.Text, nullable=False)
    userpannumber = db.Column(db.String(50))
    useraadharnumber = db.Column(db.String(50))
    userdateofjoining = db.Column(db.Date, nullable=False)
    permanentaddressuser = db.Column(db.Text, nullable=False)
    currentaddressuser = db.Column(db.Text, nullable=False)
    promationdate = db.Column(db.Date)
    userpassword = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Add these missing fields
    branch_id = db.Column(db.Integer, db.ForeignKey('branch_new.id'), nullable=True)
    department = db.Column(db.String(100))
    designation = db.Column(db.String(100))
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    branch = db.relationship('BranchNew', backref='users', lazy=True)

    def set_password(self, password):
        """Hash and set password"""
        self.userpassword = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        """Check if password matches.

        Try bcrypt verification first. If stored password is legacy plain-text
        (or bcrypt check fails), fall back to direct comparison to avoid
        locking out users created before hashing was used.
        """
        try:
            return bcrypt.checkpw(password.encode('utf-8'), self.userpassword.encode('utf-8'))
        except Exception:
            # Fallback for legacy plain-text stored passwords
            try:
                return password == self.userpassword
            except Exception:
                return False

    def to_dict(self):
        """Convert user object to dictionary"""
        user_dict = {
            'id': self.id,
            'useridname': self.useridname,
            'post': self.post,
            'username': self.username,
            'userfathername': self.userfathername,
            'usermothername': self.usermothername,
            'dateofbirth': self.dateofbirth.strftime('%Y-%m-%d') if self.dateofbirth else None,
            'useremail': self.useremail,
            'userphone': self.userphone,
            'useremergencycontact': self.useremergencycontact,
            'useraddress': self.useraddress,
            'userpannumber': self.userpannumber,
            'useraadharnumber': self.useraadharnumber,
            'userdateofjoining': self.userdateofjoining.strftime('%Y-%m-%d') if self.userdateofjoining else None,
            'permanentaddressuser': self.permanentaddressuser,
            'currentaddressuser': self.currentaddressuser,
            'promationdate': self.promationdate.strftime('%Y-%m-%d') if self.promationdate else None,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }
        
        # Add branch info if available
        if hasattr(self, 'branch_id'):
            user_dict['branch_id'] = self.branch_id
            user_dict['branch_name'] = self.branch.name if self.branch else None
        
        # Add department and designation if available
        if hasattr(self, 'department'):
            user_dict['department'] = self.department
        if hasattr(self, 'designation'):
            user_dict['designation'] = self.designation
            
        return user_dict

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    roleidname = db.Column(db.String(50), unique=True, nullable=False)
    rolename = db.Column(db.String(100), nullable=False)
    roledetails = db.Column(db.Text, nullable=False)

class Branch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text)
    phone = db.Column(db.String(15))
    email = db.Column(db.String(100))
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    manager = db.relationship('User', foreign_keys=[manager_id], backref='managed_branches', lazy=True)

class Status(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    statusid = db.Column(db.Integer, unique=True, nullable=False)
    statusname = db.Column(db.String(100), nullable=False)
    statusdetails = db.Column(db.Text, nullable=False)

class Priority(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    priorityid = db.Column(db.Integer, unique=True, nullable=False)
    priorityname = db.Column(db.String(100), nullable=False)
    prioritydetails = db.Column(db.Text, nullable=False)

class Normalservice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    normalserviceid = db.Column(db.Integer, unique=True, nullable=False)
    normalservicename = db.Column(db.String(100), nullable=False)
    normalserviceprice = db.Column(db.Float, nullable=False)
    normalservicefees = db.Column(db.Float, nullable=False)
    normalservicecharges = db.Column(db.Float, nullable=False)
    normalservicelink = db.Column(db.String(200), nullable=False)
    normalservicedetails = db.Column(db.Text, nullable=False)

class Quickservice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quickserviceid = db.Column(db.Integer, unique=True, nullable=False)
    quickservicename = db.Column(db.String(100), nullable=False)
    quickserviceprice = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(50), default='Per')
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')

    def to_dict(self):
        return {
            'id': self.quickserviceid,
            'name': self.quickservicename,
            'price': self.quickserviceprice,
            'unit': self.unit or 'Per',
            'description': self.description or '',
            'status': self.status or 'active'
        }

# ================= QUICK TASK MODELS =================
class QuickTask(db.Model):
    """Model to store quick service orders/transactions"""
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    transaction_id = db.Column(db.String(50), unique=True, nullable=False)
    
    # Customer Information
    customer_name = db.Column(db.String(100), default='Walk-in Customer')
    customer_phone = db.Column(db.String(15))
    customer_email = db.Column(db.String(100))
    
    # Staff Information
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    staff_name = db.Column(db.String(100), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch_new.id'), nullable=True)
    branch_name = db.Column(db.String(100))
    
    # Amount Details
    subtotal = db.Column(db.Float, default=0)
    tax = db.Column(db.Float, default=0)
    discount = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, nullable=False)
    amount_received = db.Column(db.Float, nullable=False)
    change_amount = db.Column(db.Float, default=0)
    
    # Payment Details
    payment_method = db.Column(db.String(20), nullable=False)  # cash, card, upi, online, etc.
    
    # Status and Timestamps
    status = db.Column(db.String(20), default='completed')
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    staff = db.relationship('User', backref='quick_tasks', lazy=True)
    branch = db.relationship('BranchNew', backref='quick_tasks', lazy=True)
    items = db.relationship('QuickTaskItem', backref='task', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_number': self.order_number,
            'transaction_id': self.transaction_id,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'customer_email': self.customer_email,
            'staff_name': self.staff_name,
            'branch_name': self.branch_name,
            'subtotal': self.subtotal,
            'tax': self.tax,
            'discount': self.discount,
            'total_amount': self.total_amount,
            'amount_received': self.amount_received,
            'change_amount': self.change_amount,
            'payment_method': self.payment_method,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'items_count': len(self.items) if self.items else 0
        }

class QuickTaskItem(db.Model):
    """Model to store individual items in a quick service order"""
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('quick_task.id'), nullable=False)
    
    # Service Information
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=True)
    service_name = db.Column(db.String(200), nullable=False)
    service_code = db.Column(db.String(50))
    
    # Quantity and Pricing
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    
    # Additional Details
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    service = db.relationship('Service', backref='quick_task_items', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'service_name': self.service_name,
            'service_code': self.service_code,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'total_price': self.total_price,
            'description': self.description
        }

class Typecustomer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    typecustomerid = db.Column(db.Integer, unique=True, nullable=False)
    typecustomername = db.Column(db.String(100), nullable=False)
    typecustomerdetails = db.Column(db.Text, nullable=False)

# ================= SERVICE MODELS =================
class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    service_type = db.Column(db.String(20), default='normal')  # normal, business
    price = db.Column(db.Float, default=0)
    fee = db.Column(db.Float, default=0)
    charge = db.Column(db.Float, default=0)
    description = db.Column(db.Text)
    estimated_time = db.Column(db.String(50))  # e.g., "2 hours", "1 day"
    department = db.Column(db.String(100))
    fee_pay_mode = db.Column(db.String(20), default='direct')  # direct, self_pay
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        """Convert service object to dictionary"""
        return {
            'id': self.id,
            'service_code': self.service_code,
            'name': self.name,
            'service_type': self.service_type,
            'price': self.price,
            'fee': self.fee,
            'charge': self.charge,
            'description': self.description,
            'estimated_time': self.estimated_time,
            'department': self.department,
            'fee_pay_mode': self.fee_pay_mode or 'direct',
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }


@event.listens_for(Service, 'before_insert')
def _ensure_service_code(mapper, connection, target):
    """Auto-generate a service_code if missing to avoid NOT NULL errors.

    Generates a timestamp-based code like SRV1700000000000.
    """
    if not getattr(target, 'service_code', None):
        ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        target.service_code = f"SRV{ts}"

class ServiceMessage(db.Model):
    """Service messages model"""
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=True)
    service_name = db.Column(db.String(100), nullable=False)
    message_type = db.Column(db.String(50), nullable=False)  # 'checkin_message', 'status_change', 'general'
    message = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        """Convert message object to dictionary"""
        return {
            'id': self.id,
            'service_id': self.service_id,
            'service_name': self.service_name,
            'message_type': self.message_type,
            'message': self.message,
            'created_by': self.created_by,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

class BranchNew(db.Model):
    """New Branch model with more fields"""
    __tablename__ = 'branch_new'  # Different name to avoid conflict
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text)
    phone = db.Column(db.String(15))
    email = db.Column(db.String(100))
    manager = db.Column(db.String(100))
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        """Convert branch object to dictionary"""
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'address': self.address,
            'phone': self.phone,
            'email': self.email,
            'manager': self.manager,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }

# ================= ATTENDANCE MODEL =================
class Attendance(db.Model):
    """Attendance model for staff check-in/check-out"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch_new.id'), nullable=True)
    branch_name = db.Column(db.String(100), nullable=False)
    check_in = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    check_out = db.Column(db.DateTime)
    total_hours = db.Column(db.Float)
    status = db.Column(db.String(20), default='checked_in')  # checked_in, checked_out
    online_cash = db.Column(db.Float, default=0.0)
    extra_amount = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationship
    user = db.relationship('User', backref='attendance_records', lazy=True)
    
    def to_dict(self):
        """Convert attendance object to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'branch_id': self.branch_id,
            'branch_name': self.branch_name,
                'check_in': self.check_in.isoformat() if self.check_in else None,
            'check_out': self.check_out.strftime('%Y-%m-%d %H:%M:%S') if self.check_out else None,
            'total_hours': self.total_hours,
            'status': self.status,
            'online_cash': self.online_cash,
            'extra_amount': self.extra_amount,
            'created_at': self.created_at.strftime('%Y-%m-%d') if self.created_at else None
        }

class PendingTaskReason(db.Model):
    """Model to store reasons for tasks remaining pending during checkout"""
    __tablename__ = 'pending_task_reasons'
    id = db.Column(db.Integer, primary_key=True)
    attendance_id = db.Column(db.Integer, db.ForeignKey('attendance.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    attendance = db.relationship('Attendance', backref='pending_reasons', lazy=True)
    task = db.relationship('Task', backref='pending_reasons', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'attendance_id': self.attendance_id,
            'task_id': self.task_id,
            'reason': self.reason,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# ================= REPORTING MODELS =================
class StaffPerformance(db.Model):
    """Staff performance metrics"""
    __tablename__ = 'staff_performance'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=lambda: datetime.now(timezone.utc).date())
    
    # Task metrics
    total_tasks = db.Column(db.Integer, default=0)
    completed_tasks = db.Column(db.Integer, default=0)
    pending_tasks = db.Column(db.Integer, default=0)
    cancelled_tasks = db.Column(db.Integer, default=0)
    in_progress_tasks = db.Column(db.Integer, default=0)
    
    # Time metrics
    avg_completion_time = db.Column(db.Float, default=0)  # in hours
    total_working_hours = db.Column(db.Float, default=0)
    
    # Quality metrics
    task_quality_score = db.Column(db.Float, default=0)  # 0-100
    customer_rating = db.Column(db.Float, default=0)  # 0-5
    
    # Financial metrics
    total_revenue = db.Column(db.Float, default=0)
    revenue_target = db.Column(db.Float, default=0)
    
    # Efficiency metrics
    tasks_per_hour = db.Column(db.Float, default=0)
    completion_rate = db.Column(db.Float, default=0)  # percentage
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = db.relationship('User', backref='performance_metrics', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.useridname if self.user else None,
            'name': self.user.username if self.user else None,
            'date': self.date.isoformat(),
            'total_tasks': self.total_tasks,
            'completed_tasks': self.completed_tasks,
            'pending_tasks': self.pending_tasks,
            'cancelled_tasks': self.cancelled_tasks,
            'in_progress_tasks': self.in_progress_tasks,
            'avg_completion_time': self.avg_completion_time,
            'total_working_hours': self.total_working_hours,
            'task_quality_score': self.task_quality_score,
            'customer_rating': self.customer_rating,
            'total_revenue': self.total_revenue,
            'revenue_target': self.revenue_target,
            'tasks_per_hour': self.tasks_per_hour,
            'completion_rate': self.completion_rate,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class BranchPerformance(db.Model):
    """Branch performance metrics"""
    __tablename__ = 'branch_performance'
    
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch_new.id'), nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1-12
    year = db.Column(db.Integer, nullable=False)
    
    # Task metrics
    total_tasks = db.Column(db.Integer, default=0)
    completed_tasks = db.Column(db.Integer, default=0)
    pending_tasks = db.Column(db.Integer, default=0)
    cancelled_tasks = db.Column(db.Integer, default=0)
    
    # Service metrics
    normal_services_count = db.Column(db.Integer, default=0)
    quick_services_count = db.Column(db.Integer, default=0)
    business_services_count = db.Column(db.Integer, default=0)
    
    # Financial metrics
    total_revenue = db.Column(db.Float, default=0)
    normal_service_revenue = db.Column(db.Float, default=0)
    quick_service_revenue = db.Column(db.Float, default=0)
    business_service_revenue = db.Column(db.Float, default=0)
    fees = db.Column(db.Float, default=0)
    profit = db.Column(db.Float, default=0)
    
    # Staff metrics
    total_staff = db.Column(db.Integer, default=0)
    active_staff = db.Column(db.Integer, default=0)
    
    # Customer metrics
    new_customers = db.Column(db.Integer, default=0)
    returning_customers = db.Column(db.Integer, default=0)
    
    # Efficiency metrics
    avg_task_completion_time = db.Column(db.Float, default=0)
    customer_satisfaction = db.Column(db.Float, default=0)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    branch = db.relationship('BranchNew', backref='performance_metrics', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'branch_id': self.branch_id,
            'branch_name': self.branch.name if self.branch else None,
            'month': self.month,
            'year': self.year,
            'total_tasks': self.total_tasks,
            'completed_tasks': self.completed_tasks,
            'pending_tasks': self.pending_tasks,
            'cancelled_tasks': self.cancelled_tasks,
            'normal_services_count': self.normal_services_count,
            'quick_services_count': self.quick_services_count,
            'business_services_count': self.business_services_count,
            'total_revenue': self.total_revenue,
            'normal_service_revenue': self.normal_service_revenue,
            'quick_service_revenue': self.quick_service_revenue,
            'business_service_revenue': self.business_service_revenue,
            'fees': self.fees,
            'profit': self.profit,
            'total_staff': self.total_staff,
            'active_staff': self.active_staff,
            'new_customers': self.new_customers,
            'returning_customers': self.returning_customers,
            'avg_task_completion_time': self.avg_task_completion_time,
            'customer_satisfaction': self.customer_satisfaction,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class DailyReport(db.Model):
    """Daily report data"""
    __tablename__ = 'daily_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=lambda: datetime.now(timezone.utc).date())
    
    # Branch metrics
    branch_id = db.Column(db.Integer, db.ForeignKey('branch_new.id'), nullable=True)
    
    # Task metrics
    total_tasks = db.Column(db.Integer, default=0)
    completed_tasks = db.Column(db.Integer, default=0)
    pending_tasks = db.Column(db.Integer, default=0)
    in_progress_tasks = db.Column(db.Integer, default=0)
    cancelled_tasks = db.Column(db.Integer, default=0)
    critical_pending_tasks = db.Column(db.Integer, default=0)
    
    # Service metrics
    normal_services = db.Column(db.Integer, default=0)
    quick_services = db.Column(db.Integer, default=0)
    business_services = db.Column(db.Integer, default=0)
    offers_applied = db.Column(db.Integer, default=0)
    
    # Financial metrics
    total_revenue = db.Column(db.Float, default=0)
    cash_collected = db.Column(db.Float, default=0)
    online_collected = db.Column(db.Float, default=0)
    due_amount = db.Column(db.Float, default=0)
    
    # Staff metrics
    staff_present = db.Column(db.Integer, default=0)
    staff_absent = db.Column(db.Integer, default=0)
    staff_late = db.Column(db.Integer, default=0)
    
    # Customer metrics
    new_customers = db.Column(db.Integer, default=0)
    returning_customers = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    branch = db.relationship('BranchNew', backref='daily_reports', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'branch_id': self.branch_id,
            'branch_name': self.branch.name if self.branch else None,
            'total_tasks': self.total_tasks,
            'completed_tasks': self.completed_tasks,
            'pending_tasks': self.pending_tasks,
            'in_progress_tasks': self.in_progress_tasks,
            'cancelled_tasks': self.cancelled_tasks,
            'critical_pending_tasks': self.critical_pending_tasks,
            'normal_services': self.normal_services,
            'quick_services': self.quick_services,
            'business_services': self.business_services,
            'offers_applied': self.offers_applied,
            'total_revenue': self.total_revenue,
            'cash_collected': self.cash_collected,
            'online_collected': self.online_collected,
            'due_amount': self.due_amount,
            'staff_present': self.staff_present,
            'staff_absent': self.staff_absent,
            'staff_late': self.staff_late,
            'new_customers': self.new_customers,
            'returning_customers': self.returning_customers,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# ================= HELPER FUNCTIONS =================
def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    """Validate phone number - exactly 10 digits, no special characters"""
    if not phone:
        return False
    # Remove any whitespace
    phone = phone.strip()
    # Check if exactly 10 digits
    pattern = r'^[0-9]{10}$'
    return re.match(pattern, phone) is not None

def validate_name(name):
    """Validate customer name - no emojis or special Unicode characters"""
    if not name:
        return False
    # Allow letters (any language), spaces, dots, hyphens, apostrophes
    # Reject emojis and special characters
    # This pattern allows basic letters, spaces, and common name punctuation
    pattern = r'^[a-zA-Z\s.\-\']+$'
    if not re.match(pattern, name):
        return False
    # Additional check: reject if contains emoji ranges (common emoji Unicode ranges)
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    if emoji_pattern.search(name):
        return False
    return True


def create_default_roles():
    """Create default roles if not exists"""
    try:
        default_roles = [
            {'roleidname': 'admin', 'rolename': 'admin', 'roledetails': 'Administrator - Full system access'},
            {'roleidname': 'manager', 'rolename': 'manager', 'roledetails': 'Manager - Branch and team management'},
            {'roleidname': 'staff', 'rolename': 'staff', 'roledetails': 'Staff - Basic access'},
        ]
        
        for role_data in default_roles:
            if not Role.query.filter_by(roleidname=role_data['roleidname']).first():
                role = Role(
                    roleidname=role_data['roleidname'],
                    rolename=role_data['rolename'],
                    roledetails=role_data['roledetails']
                )
                db.session.add(role)
        
        db.session.commit()
        print("Default roles created successfully")
    except Exception as e:
        print(f"Error creating roles: {e}")
        db.session.rollback()

def create_admin_user():
    """Create admin user if not exists"""
    try:
        if not User.query.filter_by(useridname='admin').first():
            admin = User(
                useridname='admin',
                post='admin',
                username='System Administrator',
                userfathername='',
                usermothername='',
                dateofbirth=datetime.now().date(),
                useremail='admin@system.com',
                userphone='0000000000',
                useremergencycontact='',
                useraddress='System',
                userpannumber='',
                useraadharnumber='',
                userdateofjoining=datetime.now().date(),
                permanentaddressuser='System',
                currentaddressuser='System'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin user created: admin/admin123")
    except Exception as e:
        print(f"⚠️ Error creating admin user: {e}")

# ================= CREATE TABLES =================
with app.app_context():
    db.create_all()
    create_default_roles()
    create_admin_user()

# ==================== DECORATORS ====================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # If this is an API request, return a JSON 401 instead of redirecting
            if request.path.startswith('/api/') or request.headers.get('Accept', '').startswith('application/json'):
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                if request.path.startswith('/api/') or request.headers.get('Accept', '').startswith('application/json'):
                    return jsonify({'error': 'Authentication required'}), 401
                return redirect(url_for('login'))

            user_role = session.get('role')
            if user_role not in roles:
                # For API requests return 403 JSON, otherwise flash and redirect
                if request.path.startswith('/api/') or request.headers.get('Accept', '').startswith('application/json'):
                    return jsonify({'error': 'Forbidden', 'message': 'You do not have permission to access this resource'}), 403

                flash('You do not have permission to access this page', 'error')
                # Redirect to appropriate dashboard based on role
                if user_role == 'staff':
                    return redirect(url_for('staff_dashboard'))
                elif user_role == 'manager':
                    return redirect(url_for('manager_dashboard'))
                elif user_role == 'admin':
                    return redirect(url_for('service_database'))
                else:
                    return redirect(url_for('dashboard'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ==================== CHAT ROUTES ====================

@app.route('/api/chat/messages', methods=['GET'])
@login_required
def get_chat_messages():
    try:
        limit = request.args.get('limit', 50, type=int)
        messages = chat_db.get_messages(limit)
        return jsonify({'messages': messages})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/send', methods=['POST'])
@login_required
def send_chat_message():
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        message_text = request.form.get('message')
        file = request.files.get('file')
        
        file_path = None
        file_name = None
        file_type = None
        
        if file and file.filename:
            filename = secure_filename(file.filename)
            # Create a unique filename with timestamp
            unique_filename = f"{int(datetime.now().timestamp())}_{filename}"
            upload_folder = os.path.join('static', 'uploads', 'chat')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            
            file.save(os.path.join(upload_folder, unique_filename))
            file_path = f"/static/uploads/chat/{unique_filename}"
            file_name = filename
            file_type = 'image' if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')) else 'pdf' if filename.lower().endswith('.pdf') else 'other'
        
        if not message_text and not file_path:
            return jsonify({'error': 'Empty message'}), 400
            
        chat_db.save_message(
            sender_id=user.id,
            sender_name=user.username,
            sender_role=session.get('role'),
            message=message_text,
            file_path=file_path,
            file_name=file_name,
            file_type=file_type
        )
        
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error sending chat message: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/unread', methods=['GET'])
@login_required
def get_unread_count():
    try:
        user_id = session.get('user_id')
        count = chat_db.get_unread_count(user_id)
        return jsonify({'count': count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/mark-read', methods=['POST'])
@login_required
def mark_messages_read():
    try:
        user_id = session.get('user_id')
        # Get all messages and mark them as read
        messages = chat_db.get_messages(limit=1000)
        for msg in messages:
            if msg['sender_id'] != user_id:
                chat_db.mark_as_read(msg['id'], user_id)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== ROUTES ====================

@app.route('/')
def index():
    if 'user_id' not in session:
        print("No session found, redirecting to login")
        return redirect(url_for('login'))
    
    user_role = session.get('role')
    print(f"User role in index: {user_role}")
    
    if user_role == 'staff':
        # Check if staff has checked in today
        user_id = session.get('user_id')
        today = datetime.now(timezone.utc).date()
        existing_checkin = Attendance.query.filter(
            Attendance.user_id == user_id,
            db.func.date(Attendance.created_at) == today,
            Attendance.status == 'checked_in'
        ).first()
        
        if not existing_checkin:
            # Redirect to checking page if not checked in
            print("Staff not checked in, redirecting to checking")
            return redirect(url_for('staff_checking'))
        else:
            # Already checked in, go to dashboard
            print("Staff checked in, redirecting to dashboard")
            return redirect(url_for('staff_dashboard'))
    
    elif user_role == 'admin':
        print("Redirecting admin to service database")
        return redirect(url_for('service_database'))
    
    elif user_role == 'manager':
        print("Redirecting manager to manager dashboard")
        return redirect(url_for('manager_dashboard'))
    
    else:
        print("Redirecting to default dashboard")
        return redirect(url_for('dashboard'))

@app.route('/branch')
@login_required
def branch_page():
    """Render branch management page"""
    user = User.query.get(session.get('user_id'))

    # Use normalized role from session (set at login) if available
    session_role = (session.get('role') or '').lower()
    user_post = (user.post or '').lower() if user else ''

    # Determine effective role: prefer session_role, fall back to DB value
    effective_role = session_role or user_post

    # Allow variants like 'administrator' by checking for 'admin' substring
    is_admin = effective_role == 'admin' or 'admin' in effective_role
    is_manager = effective_role == 'manager' or 'manager' in effective_role

    if not (is_admin or is_manager):
        flash('Access denied. Admin or Manager only.', 'error')
        if 'staff' in effective_role:
            return redirect('/staff/dashboard')
        else:
            return redirect('/login')

    return render_template('branch.html',
                           user_id=user.id if user else None,
                           user_name=user.username if user else '',
                           username=user.useridname if user else '',
                           user_role='admin' if is_admin else ('manager' if is_manager else effective_role),
                           user_branch=session.get('branch_id'))

# REDUNDANT BRANCH ROUTES REMOVED (Duplicate of 3376+)

#=====================login===================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        print(f"Login attempt - Username: {username}")
        
        if not username or not password:
            return render_template('login.html', error='Username and password are required')
        
        # Query user from database
        user = User.query.filter_by(useridname=username).first()
        
        if user and user.check_password(password):
            print(f"Login successful - User: {user.username}, Role: {user.post}")
            
            # IMPORTANT: Clear session first
            session.clear()
            
            # Set session data
            session['user_id'] = user.id
            session['username'] = user.useridname
            session['name'] = user.username
            # Normalize role values to canonical names used by decorators
            # Since we're now storing roles as lowercase, this is simpler
            post_lower = (user.post or '').lower().strip()
            if post_lower in ['admin', 'manager', 'staff']:
                role_value = post_lower
            elif 'admin' in post_lower or 'administrator' in post_lower:
                role_value = 'admin'
            elif 'manager' in post_lower:
                role_value = 'manager'
            elif 'staff' in post_lower:
                role_value = 'staff'
            else:
                role_value = post_lower
            session['role'] = role_value
            session['email'] = user.useremail
            # Store branch info if available
            if user.branch:
                session['branch_id'] = user.branch.id
                session['branch_name'] = user.branch.name
                session['branch_code'] = user.branch.code
                session['branch'] = user.branch.name # For backward compatibility
            
            # IMPORTANT: Make session permanent
            session.permanent = True
            
            # CRITICAL: Mark session as modified to ensure it's saved
            session.modified = True
            
            # Log session data for debugging
            print(f"Session set - user_id: {session['user_id']}, role: {session['role']}")
            
            # IMPORTANT: Force session to save immediately
            # This ensures the session is written to the client
            try:
                session_cookie = app.session_interface.get_signing_serializer(app).dumps(dict(session))
                # The session is now properly saved
            except:
                pass
            
            # After login, for staff/manager require check-in (attendance) first
            post_lower = (user.post or '').lower()
            if post_lower in ['staff', 'manager']:
                try:
                    today_status = None
                    if hasattr(db, 'get_today_status') and callable(getattr(db, 'get_today_status')):
                        today_status = db.get_today_status(user.id)

                    # If no check-in found for today, redirect to checking page
                    if not today_status or not today_status.get('check_in'):
                        return redirect(url_for('staff_checking'))
                except Exception:
                    # On error, allow normal redirect but log
                    app.logger.exception('Error checking attendance during login')

            # Redirect based on role
            if post_lower == 'staff':
                print("Redirecting staff to tasks page")
                return redirect(url_for('staff_tasks'))
            elif post_lower == 'admin':
                print("Redirecting admin to service database")
                return redirect(url_for('service_database'))
            elif post_lower == 'manager':
                print("Redirecting manager to manager dashboard")
                return redirect(url_for('manager_dashboard'))
            else:
                print("Redirecting to default dashboard")
                return redirect(url_for('dashboard'))
        
        else:
            print(f"Login failed for username: {username}")
            return render_template('login.html', error='Invalid username or password')
    
    # GET request - show login form
    return render_template('login.html')
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get user data for template
    user_data = {
        'user_id': session.get('user_id'),
        'user_name': session.get('name'),
        'user_role': session.get('role'),
        'username': session.get('username')
    }
    return render_template('task.html', **user_data)

@app.route('/chat-test')
@login_required
def chat_test():
    """Test page for chat widget"""
    return render_template('chat_test.html')

#=====================service_database==================

@app.route('/service_database', endpoint='service_database')
@login_required
def service_database_page():
    """Render service database page"""
    # Check authentication
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    
    user = User.query.get(session['user_id'])
    

    return render_template('service_database.html', 
                         user_id=user.id,
                         user_name=user.username,
                         username=user.useridname,
                         user_role=user.post)
    
    return render_template('service_database.html', 
                         user_id=user.id,
                         user_name=user.username,
                         username=user.useridname,
                         user_role=user.post)

@app.route('/api/services', methods=['GET'])
@login_required
def get_services():
    """Get all services (API endpoint)"""
    try:
        services = Service.query.order_by(Service.created_at.desc()).all()
        services_data = [service.to_dict() for service in services]
        return jsonify(services_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/services/<int:service_id>', methods=['GET'])
@login_required
def get_service(service_id):
    """Get single service (API endpoint)"""
    try:
        service = Service.query.get_or_404(service_id)
        return jsonify(service.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/api/services', methods=['POST'])
@login_required
def create_service():
    """Create new service (API endpoint)"""
    try:
        user = User.query.get(session['user_id'])
        
        # Check if user is admin or manager
        user_role = user.post.lower() if user.post else ''
        if user_role not in ['admin', 'administrator', 'manager']:
            return jsonify({'error': 'Access denied'}), 403
            
        data = request.json
        
        # Validation
        required_fields = ['name']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Create new service
        new_service = Service(
            name=data['name'],
            price=float(data.get('price', 0)),
            fee=float(data.get('fee', 0)),
            charge=float(data.get('charge', 0)),
            description=data.get('description', ''),
            estimated_time=data.get('estimated_time', ''),
            department=data.get('department', ''),
            service_type=data.get('service_type', 'normal'),
            fee_pay_mode=data.get('fee_pay_mode', 'direct'),
            status=data.get('status', 'active')
        )
        
        db.session.add(new_service)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Service created successfully',
            'service': new_service.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/services/<int:service_id>', methods=['PUT'])
@login_required
def update_service(service_id):
    """Update service (API endpoint)"""
    try:
        user = User.query.get(session['user_id'])
        
        # Check if user is admin or manager - handle role variations
        user_role = user.post.lower() if user.post else ''
        if user_role not in ['admin', 'administrator', 'manager']:
            return jsonify({'error': 'Access denied - Admin or Manager role required'}), 403
            
        service = Service.query.get_or_404(service_id)
        data = request.json
        
        # Update service fields
        if 'name' in data:
            service.name = data['name']
        if 'price' in data:
            service.price = float(data['price'])
        if 'fee' in data:
            service.fee = float(data['fee'])
        if 'charge' in data:
            service.charge = float(data['charge'])
        if 'description' in data:
            service.description = data['description']
        if 'estimated_time' in data:
            service.estimated_time = data['estimated_time']
        if 'department' in data:
            service.department = data['department']
        if 'status' in data:
            service.status = data['status']
        if 'service_type' in data:
            service.service_type = data['service_type']
        if 'fee_pay_mode' in data:
            service.fee_pay_mode = data['fee_pay_mode']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Service updated successfully',
            'service': service.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/services/<int:service_id>', methods=['DELETE'])
@login_required
def delete_service(service_id):
    """Delete service (API endpoint)"""
    try:
        user = User.query.get(session['user_id'])
        
        # Check if user is admin or manager - handle role variations
        user_role = user.post.lower() if user.post else ''
        if user_role not in ['admin', 'administrator', 'manager']:
            return jsonify({'error': 'Access denied - Admin or Manager role required'}), 403
            
        service = Service.query.get_or_404(service_id)
        
        # Check if there are tasks associated with this service
        associated_tasks = Task.query.filter_by(service_id=service_id).count()
        if associated_tasks > 0:
            return jsonify({
                'error': f'Cannot delete service. {associated_tasks} task(s) are associated with this service. Please reassign or delete those tasks first.'
            }), 400
        
        # Also delete associated messages
        ServiceMessage.query.filter_by(service_id=service_id).delete()
        
        db.session.delete(service)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Service deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/service_messages', methods=['GET'])
@login_required
def get_service_messages():
    """Get service messages (API endpoint)"""
    try:
        service_id = request.args.get('service_id')
        message_type = request.args.get('message_type')
        
        query = ServiceMessage.query
        
        if service_id and service_id != 'all':
            query = query.filter_by(service_id=service_id)
        
        if message_type:
            query = query.filter_by(message_type=message_type)
        
        messages = query.order_by(ServiceMessage.created_at.desc()).all()
        messages_data = [message.to_dict() for message in messages]
        
        return jsonify(messages_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/service_messages', methods=['POST'])
@login_required
def create_service_message():
    """Create service message (API endpoint)"""
    try:
        user = User.query.get(session['user_id'])
        
        # Check if user is admin or manager
        if user.post.lower() not in ['admin', 'manager']:
            return jsonify({'error': 'Access denied'}), 403
            
        data = request.json
        
        # Validation
        required_fields = ['message', 'created_by']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Create new message
        new_message = ServiceMessage(
            service_id=data.get('service_id'),
            service_name=data.get('service_name', 'All Services'),
            message_type=data.get('message_type', 'general'),
            message=data['message'],
            created_by=data['created_by']
        )
        
        db.session.add(new_message)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Service message created successfully',
            'service_message': new_message.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/service_messages/<int:message_id>', methods=['DELETE'])
@login_required
def delete_service_message(message_id):
    """Delete service message (API endpoint)"""
    try:
        user = User.query.get(session['user_id'])
        
        # Check if user is admin or manager
        if user.post.lower() not in ['admin', 'manager']:
            return jsonify({'error': 'Access denied'}), 403
            
        message = ServiceMessage.query.get_or_404(message_id)
        
        db.session.delete(message)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Service message deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
#=================manager report=============
@app.route('/reports')
@login_required
@role_required(['admin', 'manager','staff'])
def reports_page():
    """Render reports page - For admin, manager and staff"""
    user = User.query.get(session['user_id'])
    user_role = session.get('role', '').lower()
    
    return render_template(
        'adminreport.html',
        user_id=user.id,
        user_branch=user.branch_id,
        user_name=user.username,
        username=user.useridname,
        user_role=user.post
    )


@app.route('/api/admin/report/summary', methods=['GET'])
@login_required
@role_required(['admin','manager','staff'])
def api_admin_report_summary():
    """Return summary stats for admin report dashboard."""
    try:
        # Restriction for staff: only show today's stats for their own tasks
        user_role = session.get('role', '').lower()
        user_id = session.get('user_id')
        today = datetime.now(timezone.utc).date()

        if user_role == 'staff':
            total_tasks = Task.query.filter_by(assigned_to_id=user_id).count()
            completed_tasks = Task.query.filter_by(assigned_to_id=user_id, status='completed').count()
            pending_tasks = Task.query.filter(Task.assigned_to_id == user_id, Task.status.in_(['pending', 'in_progress', 'on_hold'])).count()
            total_revenue = db.session.query(func.coalesce(func.sum(Task.paid_amount), 0)).filter_by(assigned_to_id=user_id).scalar() or 0
            
            # Today's stats for current staff
            today_tasks = Task.query.filter(Task.assigned_to_id == user_id, func.date(Task.created_at) == today).count()
            today_revenue = db.session.query(func.coalesce(func.sum(Task.paid_amount), 0)).filter(Task.assigned_to_id == user_id, func.date(Task.created_at) == today).scalar() or 0
            today_tasks_query = Task.query.filter(Task.assigned_to_id == user_id, func.date(Task.created_at) == today)
            today_tasks = today_tasks_query.count()
            
            today_revenue = 0
            for t in today_tasks_query.all():
                # If self-pay, only service fee is counted as company revenue
                revenue = t.service_fee if t.is_self_pay else t.total_amount
                today_revenue += float(revenue or 0)

            return jsonify({
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'pending_tasks': pending_tasks,
                'total_revenue': float(total_revenue),
                'today_tasks': today_tasks,
                'today_revenue': float(today_revenue),
                'total_customers': Customer.query.count(), # Keeping totals for context
                'total_staff': 1,
                'total_branches': 1
            })

        total_tasks = Task.query.count()
        completed_tasks = Task.query.filter_by(status='completed').count()
        pending_tasks = Task.query.filter(Task.status.in_(['pending','in_progress','on_hold'])).count()
        
        
        # Correct revenue calculation: Exclude offers and due amounts on completed tasks
        # Use service_fee for self-pay, otherwise calculate based on task status
        from sqlalchemy import case
        revenue_case = case(
            # Offers: no revenue
            (Task.is_offer == True, 0),
            # Self-pay: only service fee counts
            (Task.is_self_pay == True, Task.service_fee),
            # Completed with due: only count paid amount (exclude due)
            ((Task.status == 'completed') & (Task.due_amount > 0), Task.paid_amount),
            # Normal case: use total amount
            else_=Task.total_amount
        )
        total_revenue = db.session.query(func.coalesce(func.sum(revenue_case), 0)).scalar() or 0
        
        # Quick service transactions stats
        quick_service_tasks = Task.query.filter_by(department='Quick Services').count()
        quick_service_revenue = db.session.query(
            func.coalesce(func.sum(Task.paid_amount), 0)
        ).filter_by(department='Quick Services').scalar() or 0
        
        # Today's quick service transactions
        today_quick_services = Task.query.filter(
            Task.department == 'Quick Services',
            func.date(Task.created_at) == today
        ).count()
        today_quick_revenue = db.session.query(
            func.coalesce(func.sum(Task.paid_amount), 0)
        ).filter(
            Task.department == 'Quick Services',
            func.date(Task.created_at) == today
        ).scalar() or 0
        
        total_customers = Customer.query.count()
        total_staff = User.query.count()
        total_branches = Branch.query.count()

        return jsonify({
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'pending_tasks': pending_tasks,
            'total_revenue': float(total_revenue),
            'quick_service_tasks': quick_service_tasks,
            'quick_service_revenue': float(quick_service_revenue),
            'today_quick_services': today_quick_services,
            'today_quick_revenue': float(today_quick_revenue),
            'total_customers': total_customers,
            'total_staff': total_staff,
            'total_branches': total_branches
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/report/staff-performance', methods=['GET'])
@login_required
@role_required(['admin','manager','staff'])
def api_admin_report_staff_performance():
    """Return basic staff performance metrics: tasks completed per staff."""
    try:
        # Aggregate completed tasks per staff
        results = db.session.query(
            User.id,
            User.username,
            func.count(Task.id).label('completed_count')
        ).join(Task, Task.assigned_to_id == User.id)
        results = results.filter(Task.status == 'completed')
        results = results.group_by(User.id).order_by(func.count(Task.id).desc()).all()

        data = [
            {'user_id': r[0], 'username': r[1], 'completed_count': int(r[2])}
            for r in results
        ]

        return jsonify({'staff_performance': data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/staffreport')
@login_required
@role_required(['staff','admin','manager'])
def staffreport():
    """Staff Performance Report Page"""
    try:
        user = User.query.get(session['user_id'])
        return render_template('adminreport.html', 
                             user_id=user.id,
                             user_name=user.username,
                             user_role=user.post,
                             username=user.useridname,
                             user_branch=user.branch_id or 1)
    except Exception as e:
        print(f"Error in staffreport route: {str(e)}")
        return redirect(url_for('login'))


# ================= REPORTING API ENDPOINTS =================


@app.route('/api/reports/financial', methods=['GET'])
@login_required
@role_required(['admin', 'manager', 'staff'])
def get_financial_report():
    """Get financial report with role-based restrictions and hybrid payment support"""
    try:
        user = User.query.get(session['user_id'])
        user_role = session.get('role', '').lower()
        
        # Get filter parameters
        branch_id = request.args.get('branch_id')
        service_id = request.args.get('service_id')
        staff_id = request.args.get('staff_id')
        # Get date range using helper
        date_from_dt, date_to_dt = get_date_range()
        if date_from_dt.tzinfo: date_from_dt = date_from_dt.replace(tzinfo=None)
        if date_to_dt.tzinfo: date_to_dt = date_to_dt.replace(tzinfo=None)

        # ENFORCE RESTRICTIONS (3-day limit for Managers/Staff)
        if user_role in ['manager', 'staff']:
            max_past_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=3)
            if date_from_dt < max_past_date:
                date_from_dt = max_past_date
                print(f"Restricted date_from to {date_from_dt} for {user_role}")

        # Build query
        query = Task.query.filter(
            Task.created_at >= date_from_dt,
            Task.created_at < date_to_dt
        )
        
        # Apply branch/role filters
        query = apply_role_filter(query)
        
        if branch_id and branch_id != 'all':
            try:
                query = query.filter(Task.branch_id == int(branch_id))
            except ValueError:
                pass
        
        if service_id and service_id != 'all':
            try:
                query = query.filter(Task.service_id == int(service_id))
            except ValueError:
                pass
                
        if staff_id and staff_id != 'all':
            try:
                query = query.filter(Task.assigned_to_id == int(staff_id))
            except ValueError:
                pass
        
        tasks = query.all()
        
        # Calculate financial metrics (include offer/due tasks: revenue = actual collected)
        total_revenue = 0
        cash_revenue = 0
        online_revenue = 0
        due_amount = 0
        task_revenues = {}  # task_id -> revenue, for trend consistency
        for t in tasks:
            due_amount += float(t.due_amount or 0)
            # Revenue = actual amount collected (paid_amount) for completed tasks
            # Offer/due tasks still contribute paid_amount as revenue
            if t.status == 'completed':
                task_revenue = float(t.paid_amount or 0)
            elif t.is_self_pay:
                task_revenue = float(t.service_fee or 0)
            else:
                task_revenue = float(t.service_price or t.total_amount or 0)
            task_revenues[t.id] = task_revenue
            # For self-pay completed with due: we already use paid_amount above
            total_revenue += task_revenue
            # Handle hybrid payments for cash/online breakdown
            if t.is_hybrid:
                cash_revenue += (t.cash_payment or 0)
                online_revenue += (t.online_payment or 0)
            else:
                if t.payment_mode == 'cash':
                    cash_revenue += task_revenue
                elif t.payment_mode in ['online', 'card', 'upi', 'bank_transfer']:
                    online_revenue += task_revenue



        # MASK SENSITIVE DATA FOR MANAGERS/STAFF
        # They CAN see Total and Cash Revenue, but NOT Due Amount or Monthly Report
        response_data = {
            'success': True,
            'total_revenue': round(total_revenue, 2),
            'cash_revenue': round(cash_revenue, 2),
            'online_revenue': round(online_revenue, 2),
            'revenue_trend': {'dates': [], 'revenue': []},
            'payment_methods': {'Cash': round(cash_revenue, 2), 'Online': round(online_revenue, 2)},
        }

        # Calculate actual fees for the selection (completed tasks only usually)
        total_selection_fees = sum(float((0 if t.is_self_pay else (t.service_fee or 0)) or 0) for t in tasks)
        total_selection_profit = total_revenue - total_selection_fees
        
        # Always return due_amount and monthly summary for all authorized roles now
        response_data['due_amount'] = round(due_amount, 2)
        response_data['monthly_report'] = [
            {
                'month': 'Selection', 
                'revenue': round(total_revenue, 2), 
                'fees': round(total_selection_fees, 2), 
                'profit': round(total_selection_profit, 2), 
                'growth': 0
            }
        ]

        # Generate revenue trend (daily granularity, same revenue rule as total)
        current_date_loop = date_from_dt
        while current_date_loop < date_to_dt:
            date_str = current_date_loop.strftime('%b %d')
            day_tasks = [t for t in tasks if t.created_at.date() == current_date_loop.date()]
            day_revenue = sum(task_revenues.get(t.id, 0) for t in day_tasks)
            response_data['revenue_trend']['dates'].append(date_str)
            response_data['revenue_trend']['revenue'].append(round(day_revenue, 2))
            current_date_loop += timedelta(days=1)
            
        return jsonify(response_data)
    except Exception as e:
        print(f"Error in get_financial_report: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/reports/service', methods=['GET'])
@login_required
@role_required(['admin', 'manager','staff'])
def get_service_report():
    """Get service report with all services from database"""
    try:
        user = User.query.get(session['user_id'])
        
        # Get filter parameters
        search = request.args.get('search', '')
        service_type = request.args.get('type', '')
        service_id = request.args.get('service_id')
        staff_id = request.args.get('staff_id')
        branch_id = request.args.get('branch_id', '')
        date_from = request.args.get('date_from') or request.args.get('start_date', '')
        date_to = request.args.get('date_to') or request.args.get('end_date', '')
        
        # Get date range using helper
        date_from_dt, date_to_dt = get_date_range()
        if date_from_dt.tzinfo: date_from_dt = date_from_dt.replace(tzinfo=None)
        if date_to_dt.tzinfo: date_to_dt = date_to_dt.replace(tzinfo=None)
        
        # Ensure naive datetimes
        if date_from_dt.tzinfo: date_from_dt = date_from_dt.replace(tzinfo=None)
        if date_to_dt.tzinfo: date_to_dt = date_to_dt.replace(tzinfo=None)
        
        # Get all services from database
        query = Service.query
        
        # Apply search filter
        if search:
            query = query.filter(
                (Service.name.ilike(f'%{search}%')) | 
                (Service.service_type.ilike(f'%{search}%'))
            )
        
        # Apply type filter
        if service_type and service_type != 'all':
            query = query.filter(Service.service_type.ilike(f'%{service_type}%'))
            
        # Apply specific service filter
        if service_id and service_id != 'all':
            try:
                query = query.filter(Service.id == int(service_id))
            except ValueError:
                pass
        
        services = query.all()
        print(f"Found {len(services)} services")
        
        # Get tasks in date range
        task_query = Task.query.filter(
            Task.created_at >= date_from_dt,
            Task.created_at < date_to_dt
        )
        
        # Apply branch filter
        user_role = getattr(user, 'post', None) or session.get('role', '')
        if user_role and user_role.lower() == 'manager' and user.branch_id:
            task_query = task_query.filter(Task.branch_id == user.branch_id)
        elif branch_id and branch_id != 'all':
            try:
                task_query = task_query.filter(Task.branch_id == int(branch_id))
            except ValueError:
                pass
                
        # Apply staff filter
        if staff_id and staff_id != 'all':
            try:
                task_query = task_query.filter(Task.assigned_to_id == int(staff_id))
            except ValueError:
                pass
                
        # Also filter tasks by service_id if provided
        if service_id and service_id != 'all':
            try:
                task_query = task_query.filter(Task.service_id == int(service_id))
            except ValueError:
                pass
        
        tasks = task_query.all()
        print(f"Found {len(tasks)} tasks for service report")
        
        # Calculate service statistics
        services_list = []
        service_categories = {}
        total_services_count = len(tasks)
        normal_services_count = 0
        quick_services_count = 0
        business_services_count = 0
        
        # Group tasks by service
        service_tasks = {}
        for task in tasks:
            service_id = task.service_id
            if service_id not in service_tasks:
                service_tasks[service_id] = []
            service_tasks[service_id].append(task)
        
        # Process all services from database
        for service in services:
            service_task_list = service_tasks.get(service.id, [])
            total_tasks = len(service_task_list)
            completed_tasks = len([t for t in service_task_list if t.status == 'completed'])
            
            # Calculate metrics - exclude offers and due amounts on completed tasks
            avg_price = sum(float(t.service_price or 0) for t in service_task_list) / total_tasks if total_tasks > 0 else float(service.price or 0)
            total_revenue = sum(
                float(t.paid_amount or 0) 
                for t in service_task_list 
                if not t.is_offer
            )
            
            # Calculate average completion time
            completed_service_tasks = [t for t in service_task_list if t.status == 'completed' and t.completed_at and t.created_at]
            avg_time_hours = 0
            if completed_service_tasks:
                try:
                    total_time = 0
                    for t in completed_service_tasks:
                        # Ensure both datetimes are naive
                        created = t.created_at.replace(tzinfo=None) if t.created_at.tzinfo else t.created_at
                        completed = t.completed_at.replace(tzinfo=None) if t.completed_at.tzinfo else t.completed_at
                        total_time += (completed - created).total_seconds() / 3600
                    avg_time_hours = total_time / len(completed_service_tasks)
                except Exception as e:
                    print(f"Error calculating avg time: {e}")
                    avg_time_hours = 0
            
            # Calculate rating based on completion rate
            rating = (completed_tasks / total_tasks * 5) if total_tasks > 0 else 4.0
            
            # Get service type (normalize to lowercase)
            svc_type = (service.service_type or 'normal').lower()
            
            service_data = {
                'id': service.id,
                'name': service.name,
                'type': svc_type,
                'service_type': svc_type,
                'price': round(float(service.price or 0), 2),
                'service_price': round(float(service.price or 0), 2),
                'service_fee': round(float(service.fee or 0), 2),
                'charge': round(float(service.charge or 0), 2),
                'service_charge': round(float(service.charge or 0), 2),
                'status': 'active',
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'avg_price': round(avg_price, 2),
                'avg_time': f"{avg_time_hours:.1f} hrs" if avg_time_hours > 0 else 'N/A',
                'average_time': avg_time_hours,
                'rating': round(rating, 2),
                'revenue': round(total_revenue, 2),
                'completion_rate': round((completed_tasks / total_tasks * 100), 2) if total_tasks > 0 else 0
            }
            
            services_list.append(service_data)
            
            # Update category counts
            service_categories[svc_type] = service_categories.get(svc_type, 0) + total_tasks
            
            # Update type counts
            if svc_type == 'normal':
                normal_services_count += total_tasks
            elif svc_type == 'quick':
                quick_services_count += total_tasks
            elif svc_type == 'business':
                business_services_count += total_tasks
        
        # Sort by revenue descending
        services_list.sort(key=lambda x: x['revenue'], reverse=True)
        
        # Generate service trend (last 7 days)
        service_trend = {'dates': [], 'normal': [], 'quick': [], 'business': []}
        current_date = date_from_dt
        days_to_show = min(7, (date_to_dt - date_from_dt).days)
        
        for i in range(days_to_show):
            current_date = date_from_dt + timedelta(days=i)
            date_str = current_date.strftime('%b %d')
            # Filter tasks with null check and ensure naive datetime
            day_tasks = [t for t in tasks if t.created_at and (t.created_at.replace(tzinfo=None) if t.created_at.tzinfo else t.created_at).date() == current_date.date()]
            
            # Count by service type
            normal_count = 0
            quick_count = 0
            business_count = 0
            
            for task in day_tasks:
                service = next((s for s in services if s.id == task.service_id), None)
                if service:
                    svc_type = (service.service_type or 'normal').lower()
                    if svc_type == 'normal':
                        normal_count += 1
                    elif svc_type == 'quick':
                        quick_count += 1
                    else:
                        business_count += 1
                else:
                    normal_count += 1
            
            service_trend['dates'].append(date_str)
            service_trend['normal'].append(normal_count)
            service_trend['quick'].append(quick_count)
            service_trend['business'].append(business_count)
        
        return jsonify({
            'success': True,
            'total_services': total_services_count,
            'normal_services': normal_services_count,
            'quick_services': quick_services_count,
            'business_services': business_services_count,
            'services': services_list,
            'service_performance': services_list,
            'service_trend': service_trend,
            'service_categories': service_categories,
            'services_found': len(services_list),
            'filters': {
                'search': search,
                'type': service_type,
                'branch_id': branch_id,
                'date_from': date_from,
                'date_to': date_to
            }
        })
        
    except Exception as e:
        print(f"Error in get_service_report: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/reports/offers', methods=['GET'])
@login_required
@role_required(['admin', 'manager', 'staff'])
def get_offer_report():
    """Get all tasks marked as offers with date filtering"""
    try:
        user = User.query.get(session['user_id'])
        user_role = session.get('role', '').lower()
        
        # Get filter parameters
        branch_id = request.args.get('branch_id')
        service_id = request.args.get('service_id')
        staff_id = request.args.get('staff_id')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        # Parse date range
        if date_from:
            try:
                date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
            except:
                date_from_dt = datetime.now(timezone.utc) - timedelta(days=30)
        else:
            date_from_dt = datetime.now(timezone.utc) - timedelta(days=30)
            
        if date_to:
            try:
                date_to_dt = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            except:
                date_to_dt = datetime.now(timezone.utc) + timedelta(days=1)
        else:
            date_to_dt = datetime.now(timezone.utc) + timedelta(days=1)
        
        # Build query for offers
        query = Task.query.filter(
            Task.is_offer == True,
            Task.created_at >= date_from_dt,
            Task.created_at < date_to_dt
        )
        
        # Apply role-based filters (staff see only their tasks)
        if user_role == 'staff':
            query = query.filter(Task.assigned_to_id == user.id)
        elif user_role == 'manager' and user.branch_id:
            query = query.filter(Task.branch_id == user.branch_id)
        
        # Apply additional filters
        if branch_id and branch_id != 'all':
            try:
                query = query.filter(Task.branch_id == int(branch_id))
            except ValueError:
                pass
                
        if service_id and service_id != 'all':
            try:
                query = query.filter(Task.service_id == int(service_id))
            except ValueError:
                pass
                
        if staff_id and staff_id != 'all':
            try:
                query = query.filter(Task.assigned_to_id == int(staff_id))
            except ValueError:
                pass
        
        offers = query.order_by(Task.created_at.desc()).all()
        
        # Calculate totals
        total_offer_amount = sum(float(t.offer_amount or 0) for t in offers)
        
        offers_data = [{
            'id': t.id,
            'order_no': t.order_no,
            'customer_name': t.customer_name,
            'customer_phone': t.customer_phone,
            'service_name': t.service_name,
            'offer_amount': float(t.offer_amount or 0),
            'offer_reason': t.offer_reason or '',
            'created_at': t.created_at.isoformat() if t.created_at else None,
            'assigned_to_name': t.assigned_to_name or 'Unassigned',
            'branch_name': t.branch_name or 'N/A',
            'status': t.status
        } for t in offers]
        
        return jsonify({
            'success': True,
            'offers': offers_data,
            'total_offer_amount': round(total_offer_amount, 2),
            'total_offers': len(offers)
        })
    except Exception as e:
        print(f"Error in get_offer_report: {str(e)}") 
        traceback.print_exc()
        return jsonify({'error': str(e), 'success': False}), 500

#======================user===================

@app.route('/user_management')
@login_required
@role_required(['admin', 'manager'])
def user_management():
    # Get user data for template
    user_data = {
        'user_id': session.get('user_id'),
        'user_name': session.get('name'),
        'user_role': session.get('role'),
        'username': session.get('username')
    }
    return render_template('user.html', **user_data)
@app.route('/users', methods=['GET'])
def users_page():
    """Render users page"""
    try:
        # Query actual roles from database
        roles = Role.query.all()
        return render_template('user.html', roles=roles)
    except Exception as e:
        print(f"Error loading roles: {e}")
        return render_template('user.html', roles=[])

@app.route('/api/roles', methods=['GET'])
@login_required
def get_roles():
    """Get all available roles (API endpoint)"""
    try:
        roles = Role.query.all()
        roles_data = [
            {
                'id': role.id,
                'roleidname': role.roleidname,
                'rolename': role.rolename,
                'roledetails': role.roledetails
            }
            for role in roles
        ]
        return jsonify(roles_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all users (API endpoint)"""
    try:
        users = User.query.order_by(User.created_at.desc()).all()
        users_data = [user.to_dict() for user in users]
        return jsonify(users_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get single user (API endpoint)"""
    try:
        user = User.query.get_or_404(user_id)
        return jsonify(user.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/api/users', methods=['POST'])
@login_required
@role_required(['admin'])
def create_user():
    """Create new user (API endpoint) - Admin only"""
    try:
        data = request.json
        
        # Validation
        required_fields = ['useridname', 'post', 'username', 'useremail', 'userphone', 'userpassword']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if username or email already exists
        if User.query.filter_by(useridname=data['useridname']).first():
            return jsonify({'error': 'Username already exists'}), 400
        
        if User.query.filter_by(useremail=data['useremail']).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        # Validate email
        if not validate_email(data['useremail']):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate phone
        if not validate_phone(data['userphone']):
            return jsonify({'error': 'Phone number must be 10 digits'}), 400
        
        # Security: Prevent non-admin users from creating admin accounts
        if data.get('post', '').lower() == 'admin':
            # Only allow current admin to create new admins (already checked by @role_required)
            pass  # Already protected by @role_required(['admin']) decorator
        
        # Create new user
        new_user = User(
            useridname=data['useridname'],
            post=data['post'].lower().strip(),  # Normalize to lowercase for consistency
            username=data['username'],
            userfathername=data.get('userfathername', ''),
            usermothername=data.get('usermothername', ''),
            dateofbirth=datetime.strptime(data['dateofbirth'], '%Y-%m-%d').date() if data.get('dateofbirth') else datetime.now().date(),
            useremail=data['useremail'],
            userphone=data['userphone'],
            useremergencycontact=data.get('useremergencycontact', ''),
            useraddress=data.get('useraddress', ''),
            userpannumber=data.get('userpannumber', ''),
            useraadharnumber=data.get('useraadharnumber', ''),
            userdateofjoining=datetime.strptime(data['userdateofjoining'], '%Y-%m-%d').date() if data.get('userdateofjoining') else datetime.now().date(),
            permanentaddressuser=data.get('permanentaddressuser', ''),
            currentaddressuser=data.get('currentaddressuser', ''),
            promationdate=datetime.strptime(data['promationdate'], '%Y-%m-%d').date() if data.get('promationdate') else None
        )
        
        # Set password
        new_user.set_password(data['userpassword'])
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'User created successfully',
            'user': new_user.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
@role_required(['admin'])
def update_user(user_id):
    """Update user (API endpoint) - Admin only"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.json
        
        # Check if username already exists (excluding current user)
        if 'useridname' in data and data['useridname'] != user.useridname:
            if User.query.filter_by(useridname=data['useridname']).first():
                return jsonify({'error': 'Username already exists'}), 400
        
        # Check if email already exists (excluding current user)
        if 'useremail' in data and data['useremail'] != user.useremail:
            if User.query.filter_by(useremail=data['useremail']).first():
                return jsonify({'error': 'Email already exists'}), 400
            
            # Validate email
            if not validate_email(data['useremail']):
                return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate phone if provided
        if 'userphone' in data and data['userphone']:
            if not validate_phone(data['userphone']):
                return jsonify({'error': 'Phone number must be 10 digits'}), 400
        
        # Update user fields
        update_fields = [
            'useridname', 'username', 'userfathername', 'usermothername',
            'useremail', 'userphone', 'useremergencycontact', 'useraddress',
            'userpannumber', 'useraadharnumber', 'permanentaddressuser',
            'currentaddressuser'
        ]
        
        for field in update_fields:
            if field in data:
                setattr(user, field, data[field])
        
        # Normalize post (role) to lowercase for consistency
        if 'post' in data and data['post']:
            user.post = data['post'].lower().strip()
        
        # Update dates
        if 'dateofbirth' in data and data['dateofbirth']:
            user.dateofbirth = datetime.strptime(data['dateofbirth'], '%Y-%m-%d').date()
        
        if 'userdateofjoining' in data and data['userdateofjoining']:
            user.userdateofjoining = datetime.strptime(data['userdateofjoining'], '%Y-%m-%d').date()
        
        if 'promationdate' in data and data['promationdate']:
            user.promationdate = datetime.strptime(data['promationdate'], '%Y-%m-%d').date()
        
        # Update password if provided
        if 'userpassword' in data and data['userpassword']:
            user.set_password(data['userpassword'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'User updated successfully',
            'user': user.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def delete_user(user_id):
    """Delete user (API endpoint) - Admin only"""
    try:
        user = User.query.get_or_404(user_id)
        current_user = User.query.filter_by(useridname=session.get('username')).first()
        
        # Don't allow deleting users with admin post
        if user.post.lower() == 'admin':
            return jsonify({'error': 'Cannot delete admin users. Only super admins can manage admins.'}), 403
        
        # Don't allow users to delete themselves
        if user.id == current_user.id:
            return jsonify({'error': 'Cannot delete your own account'}), 400
        # Reassign tasks and remove relations that would be nullified by SQLAlchemy
        try:
            admin = User.query.filter_by(useridname='admin').first()
            admin_id = admin.id if admin else None
            if not admin_id:
                return jsonify({'error': 'Admin account not found; cannot reassign tasks'}), 500

            # Reassign tasks where this user is the creator -> set to admin
            Task.query.filter(Task.created_by_id == user.id).update({Task.created_by_id: admin_id}, synchronize_session='fetch')

            # Unassign tasks assigned to this user (assigned_to_id is nullable)
            Task.query.filter(Task.assigned_to_id == user.id).update({Task.assigned_to_id: None, Task.assigned_to_name: None}, synchronize_session='fetch')

            # Delete related attendance records first to avoid FK NOT NULL errors
            Attendance.query.filter(Attendance.user_id == user.id).delete(synchronize_session='fetch')
            db.session.flush()
        except Exception:
            db.session.rollback()
            return jsonify({'error': 'Failed to reassign related records before deletion'}), 500

        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'User deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@role_required(['admin'])
def toggle_user_status(user_id):
    """Toggle user active status (API endpoint) - Admin only"""
    try:
        user = User.query.get_or_404(user_id)
        current_user = User.query.filter_by(useridname=session.get('username')).first()
        
        # Don't allow toggling admin status
        if user.post.lower() == 'admin':
            return jsonify({'error': 'Cannot deactivate admin users. Only super admins can manage admins.'}), 403
        
        # Don't allow users to deactivate themselves
        if user.id == current_user.id:
            return jsonify({'error': 'Cannot deactivate your own account'}), 400
        
        user.is_active = not user.is_active
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'User {"activated" if user.is_active else "deactivated"} successfully',
            'is_active': user.is_active
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== STAFF ROUTES ====================

@app.route('/staff/dashboard')
@login_required
@role_required(['staff','manager','admin'])
def staff_dashboard():
    # Check if staff has checked in today
    user_id = session.get('user_id')
    today = datetime.now(timezone.utc).date()
    existing_checkin = Attendance.query.filter(
        Attendance.user_id == user_id,
        db.func.date(Attendance.created_at) == today,
        Attendance.status == 'checked_in'
    ).first()
    
    if not existing_checkin:
        print("Staff not checked in, redirecting to checking page")
        return redirect(url_for('staff_checking'))
    
    # Get user data for template
    user = User.query.get(user_id)
    user_data = {
        'user_id': user_id,
        'user_name': session.get('name'),
        'user_role': session.get('role'),
        'username': session.get('username'),
        'branch_id': user.branch_id if user else None,
        'branch_name': user.branch.name if user and user.branch else None
    }
    print(f"Rendering staff dashboard for user: {user_data}")
    return render_template('adminreport.html', **user_data)

@app.route('/tasks')
@login_required
@role_required(['staff', 'manager','admin'])
def staff_tasks_staff():
    # Get user data for template
    role = session.get('role')
    mode = session.get('mode') or request.args.get('mode')
    user_data = {
        'user_id': session.get('user_id'),
        'user_name': session.get('name'),
        'user_role': role,
        'username': session.get('username')
    }
    # include branch for templates that expect it
    user_data['user_branch'] = session.get('branch_id') or None

    # Manager can switch to staff mode via session or query param
    if role == 'manager' and mode == 'staff':
        return render_template('task.html', **user_data)
    if role == 'manager':
        return render_template('task.html', **user_data)

    # Default for staff and other allowed roles
    return render_template('task.html', **user_data)



@app.route('/staff/todays')
@login_required
@role_required(['staff','manager','admin'])
def staff_todays_view():
    # Get user data for template
    user_data = {
        'user_id': session.get('user_id'),
        'user_name': session.get('name'),
        'user_role': session.get('role'),
        'username': session.get('username')
    }
    return render_template('today.html', **user_data)

@app.route('/staff/previous')
@login_required
@role_required(['staff','manager','admin'])
def staff_previous_view():
    # Get user data for template
    user_data = {
        'user_id': session.get('user_id'),
        'user_name': session.get('name'),
        'user_role': session.get('role'),
        'username': session.get('username')
    }
    return render_template('previous.html', **user_data)

@app.route('/staff/total_tasks')
@login_required
@role_required(['staff','manager','admin'])
def staff_total_tasks():
    # Get user data for template
    user_data = {
        'user_id': session.get('user_id'),
        'user_name': session.get('name'),
        'user_role': session.get('role'),
        'username': session.get('username')
    }
    return render_template('total_tasks.html', **user_data)

@app.route('/overtake')
@login_required
def overtake():
    # Get user data for template
    user_data = {
        'user_id': session.get('user_id'),
        'user_name': session.get('name'),
        'user_role': session.get('role'),
        'username': session.get('username')
    }
    return render_template('overtake.html', **user_data)

@app.route('/staff/ask')
@login_required
@role_required(['staff'])
def staff_ask():
    # Get user data for template
    user_data = {
        'user_id': session.get('user_id'),
        'user_name': session.get('name'),
        'user_role': session.get('role'),
        'username': session.get('username')
    }
    return render_template('ask.html', **user_data)

@app.route('/staff/checking')
@login_required
@role_required(['staff', 'manager'])
def staff_checking():
    # Get user data for template
    user_data = {
        'user_id': session.get('user_id'),
        'user_name': session.get('name'),
        'user_role': session.get('role'),
        'username': session.get('username')
    }
    return render_template('staffchecking.html', **user_data)

@app.route('/staff/checkin_complete', methods=['POST'])
@login_required
@role_required(['staff', 'manager'])
def staff_checkin_complete():
    """Handle check-in completion and redirect to appropriate dashboard"""
    role = session.get('role')
    if role == 'manager':
        return redirect(url_for('manager_dashboard'))
    return redirect(url_for('staff_dashboard'))

# ==================== API ROUTES ====================

# ----- USER API -----
@app.route('/api/users', methods=['GET', 'POST'])
@login_required
def api_users():
    if request.method == 'GET':
        search = request.args.get('search', '')
        role = request.args.get('role', '')
        users = db.get_all_users(search, role)
        return jsonify(users)
    
    elif request.method == 'POST':
        try:
            data = request.json
            user_id = db.create_user(data)
            return jsonify({'success': True, 'message': 'User created', 'id': user_id})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/users/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def api_user(user_id):
    if request.method == 'GET':
        user = db.get_user_by_id(user_id)
        if user:
            return jsonify(user)
        return jsonify({'error': 'User not found'}), 404
    
    elif request.method == 'PUT':
        try:
            data = request.json
            success = db.update_user(user_id, data)
            if success:
                return jsonify({'success': True, 'message': 'User updated'})
            return jsonify({'error': 'User not found'}), 404
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
    
    elif request.method == 'DELETE':
        try:
            # Perform deletion here to ensure related Attendance rows are removed
            user = User.query.get(user_id)
            if not user:
                return jsonify({'error': 'User not found'}), 404

            if getattr(user, 'useridname', None) == 'admin':
                return jsonify({'error': 'Cannot delete admin user'}), 400

            # Reassign tasks and remove relations that would be nullified by SQLAlchemy
            try:
                admin = User.query.filter_by(useridname='admin').first()
                admin_id = admin.id if admin else None
                if not admin_id:
                    return jsonify({'error': 'Admin account not found; cannot reassign tasks'}), 500

                Task.query.filter(Task.created_by_id == user.id).update({Task.created_by_id: admin_id}, synchronize_session='fetch')
                Task.query.filter(Task.assigned_to_id == user.id).update({Task.assigned_to_id: None, Task.assigned_to_name: None}, synchronize_session='fetch')

                Attendance.query.filter(Attendance.user_id == user.id).delete(synchronize_session='fetch')
                db.session.flush()
            except Exception:
                db.session.rollback()
                return jsonify({'error': 'Failed to reassign related records before deletion'}), 500

            # Delete the user
            db.session.delete(user)
            db.session.commit()
            return jsonify({'success': True, 'message': 'User deleted'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400

# ----- SERVICE API -----
@app.route('/api/services', methods=['GET', 'POST'])
@login_required
def api_services():
    if request.method == 'GET':
        search = request.args.get('search', '')
        service_type = request.args.get('type', '')
        
        try:
            if service_type:
                services = db.get_services_by_type(service_type)
            else:
                services = db.get_all_services(search)
            return jsonify(services)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.json
            service_id = db.create_service(data)
            return jsonify({'success': True, 'message': 'Service created', 'id': service_id})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/services/<int:service_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def api_service(service_id):
    if request.method == 'GET':
        service = db.get_service_by_id(service_id)
        if service:
            return jsonify(service)
        return jsonify({'error': 'Service not found'}), 404
    
    elif request.method == 'PUT':
        data = request.json
        success = db.update_service(service_id, data)
        if success:
            return jsonify({'success': True, 'message': 'Service updated'})
        return jsonify({'error': 'Service not found'}), 404
    
    elif request.method == 'DELETE':
        success = db.delete_service(service_id)
        if success:
            return jsonify({'success': True, 'message': 'Service deleted'})
        return jsonify({'error': 'Service not found'}), 404

# ----- SERVICE MESSAGES API -----
@app.route('/api/service_messages', methods=['GET', 'POST'])
@login_required
def api_service_messages():
    if request.method == 'GET':
        service_id = request.args.get('service_id', None)
        message_type = request.args.get('message_type', None)
        
        if service_id:
            service_id = int(service_id) if service_id != 'null' else None
        
        messages = db.get_service_messages(service_id, message_type)
        return jsonify(messages)
    
    elif request.method == 'POST':
        try:
            data = request.json
            message_id = db.create_service_message(data)
            return jsonify({'success': True, 'message': 'Message created', 'id': message_id})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400

# ----- TASK API -----
@app.route('/api/tasks', methods=['GET'])
@login_required
def api_tasks():
    """Get tasks based on user role"""
    # Get tasks based on user role
    user_role = session.get('role')
    username = session.get('username')
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    branch_id = request.args.get('branch', '')
    staff_username = request.args.get('staff', '')
    service_type = request.args.get('service_type', '')
    
    try:
        query = Task.query

        # Handle staff filter first for admin/manager
        if staff_username and user_role and user_role.lower() in ['admin', 'manager']:
            # For admin/manager, allow filtering by any staff member
            staff_user = User.query.filter((User.useridname == staff_username) | (User.username == staff_username)).first()
            if staff_user:
                query = query.filter(Task.assigned_to_id == staff_user.id)
        elif user_role and user_role.lower() == 'staff':
            # For staff users, restrict to their own tasks
            user = User.query.filter((User.username == username) | (User.useridname == username)).first()
            if user:
                if user.branch_id:
                    query = query.filter((Task.assigned_to_id == user.id) | ((Task.in_openplace == True) & (Task.branch_id == user.branch_id)))
                else:
                    query = query.filter((Task.assigned_to_id == user.id) | (Task.in_openplace == True))
        
        # Apply other filters
        if status:
            query = query.filter(Task.status == status)
        if priority:
            query = query.filter(Task.priority == priority)
        if branch_id:
            query = query.filter(Task.branch_id == branch_id)
        if service_type:
            query = query.join(Service).filter(Service.service_type == service_type)

        tasks = query.order_by(Task.created_at.desc()).all()
        tasks_data = [t.to_dict() for t in tasks]
        return jsonify(tasks_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/openplace', methods=['GET'])
@login_required
def get_openplace_tasks():
    """Get all tasks assigned to open place"""
    try:
        user = User.query.get(session['user_id'])
        service_type = request.args.get('service_type', '')
        priority = request.args.get('priority', '')
        
        # Build query for open place tasks
        query = Task.query.filter_by(in_openplace=True, status='pending')
        
        # Get staff filter parameter
        staff_username = request.args.get('staff', '')
        
        # Handle staff filter for admin/manager
        if staff_username and user.post and user.post.lower() in ['admin', 'manager']:
            # For admin/manager, allow filtering by any staff member
            staff_user = User.query.filter((User.useridname == staff_username) | (User.username == staff_username)).first()
            if staff_user:
                query = query.filter(Task.assigned_to_id == staff_user.id)
        # Filter by branch if staff or manager
        elif user.post.lower() == 'staff' and user.branch_id:
            query = query.filter(Task.branch_id == user.branch_id)
        elif user.post.lower() == 'manager' and user.branch_id:
            query = query.filter(Task.branch_id == user.branch_id)
        
        if service_type:
            query = query.join(Service).filter(Service.service_type == service_type)
        if priority:
            query = query.filter(Task.priority == priority)
            
        openplace_tasks = query.order_by(Task.created_at.desc()).all()
        tasks_data = [task.to_dict() for task in openplace_tasks]
        return jsonify(tasks_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/openplace/count', methods=['GET'])
@login_required
def get_openplace_count():
    """Get count of open place tasks"""
    try:
        user = User.query.get(session['user_id'])
        query = Task.query.filter_by(in_openplace=True, status='pending')
        
        # Filter by branch if staff or manager
        if user.post.lower() == 'staff' and user.branch_id:
            query = query.filter(Task.branch_id == user.branch_id)
        elif user.post.lower() == 'manager' and user.branch_id:
            query = query.filter(Task.branch_id == user.branch_id)
        # Admin can see all
        
        count = query.count()
        return jsonify({'count': count})
    except Exception as e:
        return jsonify({'error': str(e), 'count': 0}), 500

@app.route('/api/tasks/today', methods=['GET'])
@login_required
def get_today_tasks():
    """Get today's tasks"""
    try:
        user = User.query.get(session['user_id'])
        today = datetime.now(timezone.utc).date()
        service_type = request.args.get('service_type', '')
        priority = request.args.get('priority', '')
        status = request.args.get('status', '')
        
        # Build query
        query = Task.query.filter(db.func.date(Task.created_at) == today)
        
        # Get staff filter parameter
        staff_username = request.args.get('staff', '')
        
        # Handle staff filter for admin/manager
        if staff_username and user.post and user.post.lower() in ['admin', 'manager']:
            # For admin/manager, allow filtering by any staff member
            staff_user = User.query.filter((User.useridname == staff_username) | (User.username == staff_username)).first()
            if staff_user:
                query = query.filter(Task.assigned_to_id == staff_user.id)
        # If staff, only show their tasks or open place tasks from their branch
        elif user.post.lower() == 'staff':
            if user.branch_id:
                query = query.filter(
                    (Task.assigned_to_id == user.id) | 
                    ((Task.in_openplace == True) & (Task.branch_id == user.branch_id))
                )
            else:
                query = query.filter(
                    (Task.assigned_to_id == user.id) | 
                    (Task.in_openplace == True)
                )
        # Filter by branch if manager
        elif user.post.lower() == 'manager' and user.branch_id:
            query = query.filter(Task.branch_id == user.branch_id)
        
        if service_type:
            query = query.join(Service).filter(Service.service_type == service_type)
        if priority:
            query = query.filter(Task.priority == priority)
        if status:
            query = query.filter(Task.status == status)
            
        tasks = query.order_by(Task.created_at.desc()).all()
        tasks_data = [task.to_dict() for task in tasks]
        return jsonify(tasks_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tasks/pending', methods=['GET'])
@login_required
def get_pending_tasks():
    """Get pending tasks"""
    try:
        user = User.query.get(session.get('user_id'))
        service_type = request.args.get('service_type', '')
        priority = request.args.get('priority', '')

        query = Task.query.filter(Task.status == 'pending')
        
        # Get staff filter parameter
        staff_username = request.args.get('staff', '')
        
        # Handle staff filter for admin/manager
        if user and hasattr(user, 'post') and user.post and staff_username and user.post.lower() in ['admin', 'manager']:
            # For admin/manager, allow filtering by any staff member
            staff_user = User.query.filter((User.useridname == staff_username) | (User.username == staff_username)).first()
            if staff_user:
                query = query.filter(Task.assigned_to_id == staff_user.id)
        elif user and hasattr(user, 'post') and user.post and user.post.lower() == 'staff':
            if user.branch_id:
                query = query.filter((Task.assigned_to_id == user.id) | ((Task.in_openplace == True) & (Task.branch_id == user.branch_id)))
            else:
                query = query.filter((Task.assigned_to_id == user.id) | (Task.in_openplace == True))
        elif user and hasattr(user, 'post') and user.post and user.post.lower() == 'manager' and getattr(user, 'branch_id', None):
            query = query.filter(Task.branch_id == user.branch_id)

        if service_type:
            query = query.join(Service).filter(Service.service_type == service_type)
        if priority:
            query = query.filter(Task.priority == priority)

        tasks = query.order_by(Task.created_at.desc()).all()
        tasks_data = [task.to_dict() for task in tasks]
        return jsonify(tasks_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/previous', methods=['GET'])
@login_required
def get_previous_tasks():
    """Get previous tasks (last 7 days)"""
    try:
        # Build query for previous tasks: show pending and on_hold tasks
        user = User.query.get(session.get('user_id'))
        service_type = request.args.get('service_type', '')
        priority = request.args.get('priority', '')

        query = Task.query.filter(Task.status.in_(['pending', 'on_hold']))
        
        # Get staff filter parameter
        staff_username = request.args.get('staff', '')
        
        # Handle staff filter for admin/manager
        if user and getattr(user, 'post', None) and user.post and staff_username and user.post.lower() in ['admin', 'manager']:
            # For admin/manager, allow filtering by any staff member
            staff_user = User.query.filter((User.useridname == staff_username) | (User.username == staff_username)).first()
            if staff_user:
                query = query.filter(Task.assigned_to_id == staff_user.id)
        # Staff should only see their own or openplace tasks from their branch
        elif user and getattr(user, 'post', None) and user.post.lower() == 'staff':
            if user.branch_id:
                query = query.filter((Task.assigned_to_id == user.id) | ((Task.in_openplace == True) & (Task.branch_id == user.branch_id)))
            else:
                query = query.filter((Task.assigned_to_id == user.id) | (Task.in_openplace == True))
        # Manager limited to their branch if branch_id present
        elif user and getattr(user, 'post', None) and user.post.lower() == 'manager' and getattr(user, 'branch_id', None):
            query = query.filter(Task.branch_id == user.branch_id)

        if service_type:
            query = query.join(Service).filter(Service.service_type == service_type)
        if priority:
            query = query.filter(Task.priority == priority)

        tasks = query.order_by(Task.created_at.desc()).all()
        tasks_data = [t.to_dict() for t in tasks]
        return jsonify(tasks_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/total', methods=['GET'])
@login_required
def get_total_tasks():
    """Get total tasks count and statistics"""
    try:
        # Return full task list (respecting staff/manager scoping)
        user = User.query.get(session.get('user_id'))
        service_type = request.args.get('service_type', '')
        priority = request.args.get('priority', '')
        status = request.args.get('status', '')

        query = Task.query
        
        # Get staff filter parameter
        staff_username = request.args.get('staff', '')
        
        # Handle staff filter for admin/manager
        if user and getattr(user, 'post', None) and user.post and staff_username and user.post.lower() in ['admin', 'manager']:
            # For admin/manager, allow filtering by any staff member
            staff_user = User.query.filter((User.useridname == staff_username) | (User.username == staff_username)).first()
            if staff_user:
                query = query.filter(Task.assigned_to_id == staff_user.id)
        elif user and getattr(user, 'post', None) and user.post.lower() == 'staff':
            if user.branch_id:
                query = query.filter((Task.assigned_to_id == user.id) | ((Task.in_openplace == True) & (Task.branch_id == user.branch_id)))
            else:
                query = query.filter((Task.assigned_to_id == user.id) | (Task.in_openplace == True))
        elif user and getattr(user, 'post', None) and user.post.lower() == 'manager' and getattr(user, 'branch_id', None):
            query = query.filter(Task.branch_id == user.branch_id)

        if service_type:
            query = query.join(Service).filter(Service.service_type == service_type)
        if priority:
            query = query.filter(Task.priority == priority)
        if status:
            query = query.filter(Task.status == status)

        tasks = query.order_by(Task.created_at.desc()).all()
        tasks_data = [t.to_dict() for t in tasks]
        return jsonify(tasks_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tasks/overtake', methods=['GET'])
@login_required
def get_overtake_tasks():
    """Get tasks older than X days (query param `days`). Optional `status` filter.

    Examples:
      /api/tasks/overtake?days=30
      /api/tasks/overtake?days=90&status=pending
    """
    try:
        # default to 30 days if not provided
        days_param = request.args.get('days', None)
        try:
            days = int(days_param) if days_param is not None else 30
        except ValueError:
            return jsonify({'error': 'Invalid days parameter'}), 400

        status = request.args.get('status', None)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        service_type = request.args.get('service_type', '')
        priority = request.args.get('priority', '')

        query = Task.query.filter(Task.created_at <= cutoff)

        if status:
            query = query.filter(Task.status == status)

        # Apply role-based visibility similar to other list endpoints
        user = None
        if session.get('user_id'):
            user = User.query.get(session.get('user_id'))
        
        # Get staff filter parameter
        staff_username = request.args.get('staff', '')
        
        if user and hasattr(user, 'post') and user.post:
            post = user.post.lower()
            # Handle staff filter for admin/manager
            if staff_username and post in ['admin', 'manager']:
                # For admin/manager, allow filtering by any staff member
                staff_user = User.query.filter((User.useridname == staff_username) | (User.username == staff_username)).first()
                if staff_user:
                    query = query.filter(Task.assigned_to_id == staff_user.id)
            elif post == 'staff':
                if user.branch_id:
                    query = query.filter((Task.assigned_to_id == user.id) | ((Task.in_openplace == True) & (Task.branch_id == user.branch_id)))
                else:
                    query = query.filter((Task.assigned_to_id == user.id) | (Task.in_openplace == True))
            elif post == 'manager' and getattr(user, 'branch_id', None):
                query = query.filter(Task.branch_id == user.branch_id)

        if service_type:
            query = query.join(Service).filter(Service.service_type == service_type)
        if priority:
            query = query.filter(Task.priority == priority)

        tasks = query.order_by(Task.created_at.desc()).all()
        tasks_data = [t.to_dict() for t in tasks]
        return jsonify(tasks_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ----- CUSTOMER API -----
@app.route('/api/customers/check', methods=['GET'])
@login_required
def check_customer():
    """Check if customer exists by phone number"""
    phone = request.args.get('phone', '')
    if phone:
        customer = db.get_customer_by_phone(phone)
        if customer:
            return jsonify({
                'exists': True,
                'name': customer['name'],
                'total_services': customer['total_services'],
                'total_spent': customer['total_spent']
            })
        return jsonify({'exists': False})
    return jsonify({'exists': False})

@app.route('/api/customers/suggest', methods=['GET'])
@login_required
def customer_suggestions():
    phone = request.args.get('phone', '')
    if phone and len(phone) >= 3:
        customers = db.get_all_customers(phone)
        suggestions = [{'name': c['name'], 'phone': c['contact_number']} for c in customers[:5]]
        return jsonify(suggestions)
    return jsonify([])

@app.route('/api/customers/search', methods=['GET'])
@login_required
def search_customers():
    search_term = request.args.get('q', '')
    if search_term:
        customers = db.get_all_customers(search_term)
        return jsonify(customers)
    return jsonify([])

@app.route('/api/customers', methods=['GET', 'POST'])
@login_required
def api_customers():
    if request.method == 'GET':
        search = request.args.get('search', '')
        customers = db.get_all_customers(search)
        return jsonify(customers)
    
    elif request.method == 'POST':
        try:
            data = request.json
            # Create or update customer
            contact_number = data.get('contact_number')
            if contact_number:
                success = db.update_customer(contact_number, data)
                if success:
                    return jsonify({'success': True, 'message': 'Customer updated'})
                else:
                    # Create new customer
                    # You might want to add a create_customer method in database.py
                    return jsonify({'success': True, 'message': 'Customer processed'})
            else:
                return jsonify({'success': False, 'error': 'Contact number required'}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400

# REDUNDANT ATTENDANCE ROUTES REMOVED (Duplicate of 6727+)


# ----- INQUIRY API -----
@app.route('/api/inquiries', methods=['POST'])
@login_required
def create_inquiry():
    try:
        data = request.json
        data['created_by'] = session.get('username', '')
        # Save inquiry to database
        inquiry_id = db.create_inquiry(data)
        return jsonify({'success': True, 'message': 'Inquiry submitted successfully', 'id': inquiry_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/inquiries', methods=['GET'])
@login_required
def get_inquiries():
    try:
        status = request.args.get('status', '')
        inquiries = db.get_inquiries(status)
        return jsonify(inquiries)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/inquiries/<int:inquiry_id>/status', methods=['PUT'])
@login_required
def update_inquiry_status(inquiry_id):
    try:
        data = request.json
        status = data.get('status')
        if not status:
            return jsonify({'success': False, 'error': 'Status is required'}), 400
        
        resolved_by = session.get('username') if status == 'resolved' else None
        success = db.update_inquiry_status(inquiry_id, status, resolved_by)
        
        if success:
            return jsonify({'success': True, 'message': 'Inquiry status updated'})
        return jsonify({'success': False, 'error': 'Inquiry not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ----- STATS API -----
@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    """Get dashboard statistics"""
    try:
        now = datetime.now(timezone.utc)
        total_tasks = Task.query.count()
        pending = Task.query.filter(Task.status == 'pending').count()
        in_progress = Task.query.filter(Task.status == 'in_progress').count()
        completed = Task.query.filter(Task.status == 'completed').count()
        # Tasks older than 7 days and not completed
        overdue = Task.query.filter(Task.status != 'completed', Task.created_at < (now - timedelta(days=7))).count()
        users_count = User.query.count()
        branches_count = BranchNew.query.count()
        total_revenue = db.session.query(func.sum(Task.total_amount)).scalar() or 0

        stats = {
            'total_tasks': total_tasks,
            'pending': pending,
            'in_progress': in_progress,
            'completed': completed,
            'overdue': overdue,
            'users': users_count,
            'branches': branches_count,
            'total_revenue': float(total_revenue)
        }

        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats/services', methods=['GET'])
@login_required
def get_service_stats():
    """Get service statistics"""
    try:
        # Count tasks per service
        rows = db.session.query(Task.service_name, func.count(Task.id).label('count')).group_by(Task.service_name).all()
        stats = [{'service_name': r[0], 'count': r[1]} for r in rows]
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ----- BRANCH API -----
@app.route('/api/branches', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
@role_required(['admin', 'manager'])
def api_branches():
    """API for Branches using BranchNew model"""
    if request.method == 'GET':
        try:
            branches = BranchNew.query.all()
            return jsonify([b.to_dict() for b in branches])
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.json
            if not data.get('name'):
                return jsonify({'success': False, 'error': 'Branch name is required'}), 400
            
            # Use provided code or call the existing generate local route (abstracted logic)
            code = data.get('code')
            if not code:
                # Basic prefix-based auto-gen if code missing
                prefix = data['name'][:2].upper()
                count = BranchNew.query.filter(BranchNew.code.like(f'{prefix}%')).count()
                code = f"{prefix}{10 + count:05d}"
            
            # Check for duplicate code
            if BranchNew.query.filter_by(code=code).first():
                return jsonify({'success': False, 'error': f'Branch code {code} already exists'}), 400

            branch = BranchNew(
                code=code,
                name=data['name'],
                address=data.get('address'),
                phone=data.get('phone'),
                email=data.get('email'),
                manager=data.get('manager'),
                status=data.get('status', 'active')
            )
            db.session.add(branch)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Branch created successfully', 'id': branch.id})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
    
    elif request.method == 'PUT':
        try:
            branch_id = request.args.get('id')
            if not branch_id:
                return jsonify({'success': False, 'error': 'Branch ID is required'}), 400
            
            branch = BranchNew.query.get(branch_id)
            if not branch:
                return jsonify({'success': False, 'error': 'Branch not found'}), 404
            
            data = request.json
            if data.get('name'): branch.name = data['name']
            if data.get('code'): 
                # Check for duplicate if code changed
                if data['code'] != branch.code and BranchNew.query.filter_by(code=data['code']).first():
                     return jsonify({'success': False, 'error': f'Branch code {data["code"]} already exists'}), 400
                branch.code = data['code']
            
            branch.address = data.get('address', branch.address)
            branch.phone = data.get('phone', branch.phone)
            branch.email = data.get('email', branch.email)
            branch.manager = data.get('manager', branch.manager)
            branch.status = data.get('status', branch.status)
            
            db.session.commit()
            return jsonify({'success': True, 'message': 'Branch updated successfully'})
                
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
    
    elif request.method == 'DELETE':
        try:
            branch_id = request.args.get('id')
            if not branch_id:
                return jsonify({'success': False, 'error': 'Branch ID is required'}), 400
            
            branch = BranchNew.query.get(branch_id)
            if branch:
                db.session.delete(branch)
                db.session.commit()
                return jsonify({'success': True, 'message': 'Branch deleted successfully'})
            else:
                return jsonify({'success': False, 'error': 'Branch not found'}), 404
                
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
# Add these routes to your existing Flask app.py

@app.route('/api/branches/all', methods=['GET'])
@login_required
def get_all_branches():
    """Get all branches for dropdown"""
    try:
        branches = BranchNew.query.filter_by(status='active').all()
        branches_data = [{
            'id': branch.id,
            'name': branch.name,
            'code': branch.code
        } for branch in branches]
        return jsonify(branches_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/bill', methods=['GET'])
@login_required
def get_task_bill(task_id):
    """Generate bill for task"""
    try:
        task = Task.query.get_or_404(task_id)
        
        # Create bill HTML (simplified version)
        bill_html = f"""
        <html>
        <head>
            <title>Bill - {task.order_no}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .bill-details {{ margin-bottom: 20px; }}
                .bill-details table {{ width: 100%; border-collapse: collapse; }}
                .bill-details th, .bill-details td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .bill-details th {{ background-color: #f2f2f2; }}
                .total {{ font-weight: bold; font-size: 18px; margin-top: 20px; }}
                .footer {{ margin-top: 40px; font-size: 12px; color: #666; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>INVOICE</h1>
                <h3>Order No: {task.order_no}</h3>
            </div>
            
            <div class="bill-details">
                <table>
                    <tr>
                        <th>Customer Name</th>
                        <td>{task.customer_name}</td>
                    </tr>
                    <tr>
                        <th>Phone Number</th>
                        <td>{task.customer_phone}</td>
                    </tr>
                    <tr>
                        <th>Service</th>
                        <td>{task.service_name}</td>
                    </tr>
                    <tr>
                        <th>Service Price</th>
                        <td>₹{task.service_price}</td>
                    </tr>
                    <tr>
                        <th>Service Fee</th>
                        <td>₹{task.service_fee}</td>
                    </tr>
                    <tr>
                        <th>Total Amount</th>
                        <td>₹{task.total_amount}</td>
                    </tr>
                    <tr>
                        <th>Paid Amount</th>
                        <td>₹{task.paid_amount}</td>
                    </tr>
                    <tr>
                        <th>Due Amount</th>
                        <td>₹{task.due_amount}</td>
                    </tr>
                    <tr>
                        <th>Payment Mode</th>
                        <td>{task.payment_mode or 'Cash'}</td>
                    </tr>
                    <tr>
                        <th>Status</th>
                        <td>{task.status.replace('_', ' ').title()}</td>
                    </tr>
                    <tr>
                        <th>Created Date</th>
                        <td>{task.created_at.strftime('%Y-%m-%d %H:%M:%S')}</td>
                    </tr>
                </table>
            </div>
            
            <div class="total">
                Total Amount: ₹{task.total_amount}
            </div>
            
            <div class="footer">
                <p>Thank you for your business!</p>
                <p>This is a computer generated invoice.</p>
            </div>
        </body>
        </html>
        """
        
        return bill_html
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/mark-offer', methods=['POST'])
@login_required
def mark_task_as_offer(task_id):
    """Mark the remaining/due amount of a task as an offer"""
    try:
        task = Task.query.get_or_404(task_id)
        data = request.json
        
        reason = data.get('reason', '')
        
        # Mark as offer
        task.is_offer = True
        task.offer_amount = task.due_amount or 0
        task.offer_reason = reason
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Task marked as offer successfully',
            'task': task.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
@app.route('/api/branches/<int:branch_id>', methods=['GET'])
@login_required
@role_required(['admin', 'manager'])
def api_branch_detail(branch_id):
    """Get single branch details"""
    try:
        branch = db.get_branch_by_id(branch_id)
        if branch:
            return jsonify(branch)
        return jsonify({'error': 'Branch not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/branches/generate-code', methods=['GET'])
@login_required
@role_required(['admin', 'manager'])
def generate_branch_code_api():
    """Generate branch code from name"""
    try:
        branch_name = request.args.get('name', '')
        if not branch_name:
            return jsonify({'error': 'Branch name is required'}), 400
        
        code = db.generate_branch_code(branch_name)
        return jsonify({'code': code})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ----- TASK DETAILS API -----
@app.route('/api/tasks/<int:task_id>/details', methods=['GET'])
@login_required
def get_task_details(task_id):
    try:
        task = db.get_task_with_details(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Get status history
        status_history = []
        try:
            with db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT * FROM status_history 
                    WHERE task_id = ? 
                    ORDER BY changed_at DESC
                ''', (task_id,))
                status_history = [dict(row) for row in cursor.fetchall()]
        except:
            pass
        
        return jsonify({
            'task': task,
            'status_history': status_history
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ----- ONLINE TASK COMPLETE API -----
@app.route('/api/tasks/<int:task_id>/online-complete', methods=['PUT'])
@login_required
def complete_online_task(task_id):
    try:
        data = request.json
        task = db.get_task_by_id(task_id)
        
        if not task:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        # Calculate due amount
        paid_amount = data.get('paid_amount', task['service_price'])
        due_amount = task['service_price'] - paid_amount
        
        # Update task status
        success = db.update_task_status(task_id, 'completed', 'Task completed', session.get('username', ''))
        
        if success:
            # Update payment details
            with db.get_cursor() as cursor:
                cursor.execute('''
                    UPDATE tasks 
                    SET paid_amount = ?,
                        due_amount = ?,
                        extra_charges = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (
                    paid_amount, 
                    due_amount, 
                    json.dumps(data.get('extra_charges', {})), 
                    task_id
                ))
            
            return jsonify({'success': True, 'message': 'Task completed'})
        
        return jsonify({'success': False, 'error': 'Failed to update task'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ----- QUICK STATUS UPDATE API -----
@app.route('/api/tasks/<int:task_id>/quick-status', methods=['PUT'])
@login_required
def quick_update_status(task_id):
    try:
        data = request.json
        new_status = data.get('status')
        changed_by = data.get('changed_by', '')
        
        if not new_status:
            return jsonify({'success': False, 'error': 'Status is required'}), 400
        
        success = db.update_task_status(task_id, new_status, 'Quick status update', changed_by)
        
        if success:
            return jsonify({'success': True, 'message': 'Status updated'})
        
        return jsonify({'success': False, 'error': 'Task not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ----- ONLINE TASK RECORD API -----
@app.route('/api/tasks/<int:task_id>/online-record', methods=['POST'])
@login_required
def create_online_task_record(task_id):
    try:
        data = request.json
        online_task_id = db.create_online_task(task_id, data)
        
        if online_task_id:
            return jsonify({'success': True, 'message': 'Online task record created'})
        return jsonify({'success': False, 'error': 'Failed to create online task record'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# ==================== HELPER FUNCTIONS ====================

def generate_status_message(status, reason):
    """Generate customer message based on status change"""
    messages = {
        'pending': 'Your service request has been received and is pending processing.',
        'in_progress': 'Your service request is currently being processed by our team.',
        'on_hold': f'Your service request is on hold. Reason: {reason}' if reason else 'Your service request is on hold.',
        'completed': 'Congratulations! Your service request has been completed successfully.',
        'cancelled': f'We regret to inform you that your service request has been cancelled. Reason: {reason}' if reason else 'Your service request has been cancelled.',
        'delayed': f'Your service request has been delayed. Reason: {reason}' if reason else 'Your service request has been delayed.'
    }
    
    default_msg = f'Your service request status has been updated to {status.replace("_", " ").title()}.'
    
    return messages.get(status, default_msg) + (f' Reason: {reason}' if reason and status not in messages else '')

# ----- QUICK SERVICES ROUTES -----
@app.route('/quick_services')
@login_required
@role_required(['admin', 'manager','staff'])
def quick_services():
    """Quick Service Database Page"""
    user_data = {
        'user_id': session.get('user_id'),
        'user_name': session.get('name'),
        'user_role': session.get('role'),
        'username': session.get('username')
    }
    return render_template('quick_service_database.html', **user_data)

@app.route('/api/quick_services', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
@role_required(['admin', 'manager','staff'])
def api_quick_services():
    """API for Quick Services Management"""
    if request.method == 'GET':
        try:
            # Only show active services unless specified
            show_all = request.args.get('all', 'false').lower() == 'true'
            if show_all:
                quick_services = Quickservice.query.all()
            else:
                quick_services = Quickservice.query.filter_by(status='active').all()
            
            return jsonify([qs.to_dict() for qs in quick_services])
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.json
            # Get next quickserviceid
            max_id = db.session.query(func.max(Quickservice.quickserviceid)).scalar() or 0
            new_id = max_id + 1
            
            new_service = Quickservice(
                quickserviceid=new_id,
                quickservicename=data.get('name', ''),
                quickserviceprice=float(data.get('price', 0)),
                unit=data.get('unit', 'Per'),
                description=data.get('description', ''),
                status='active'
            )
            db.session.add(new_service)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Service added successfully', 'service': new_service.to_dict()})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
    
    elif request.method == 'PUT':
        try:
            data = request.json
            service_id = request.args.get('id')
            if not service_id:
                return jsonify({'success': False, 'error': 'Service ID required'}), 400
            
            service = Quickservice.query.filter_by(quickserviceid=int(service_id)).first()
            if not service:
                return jsonify({'success': False, 'error': 'Service not found'}), 404
            
            if 'name' in data: service.quickservicename = data['name']
            if 'price' in data: service.quickserviceprice = float(data['price'])
            if 'unit' in data: service.unit = data['unit']
            if 'description' in data: service.description = data['description']
            if 'status' in data: service.status = data['status']
            
            db.session.commit()
            return jsonify({'success': True, 'message': 'Service updated successfully', 'service': service.to_dict()})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
            
    elif request.method == 'DELETE':
        try:
            service_id = request.args.get('id')
            if not service_id:
                return jsonify({'success': False, 'error': 'Service ID required'}), 400
            
            service = Quickservice.query.filter_by(quickserviceid=int(service_id)).first()
            if not service:
                return jsonify({'success': False, 'error': 'Service not found'}), 404
            
            # Use soft delete (deactivate)
            service.status = 'inactive'
            db.session.commit()
            return jsonify({'success': True, 'message': 'Service deactivated successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400

# ----- QUICK SERVICE INTERFACE -----
@app.route('/quick')
@login_required
def quick_service_page():
    """Quick Service Interface for Staff"""
    if session.get('role') not in ['staff', 'admin', 'manager']:
        return redirect(url_for('dashboard'))
    
    user_data = {
        'user_id': session.get('user_id'),
        'user_name': session.get('name'),
        'user_role': session.get('role'),
        'username': session.get('username'),
        'branch': session.get('branch', '')
    }
    return render_template('quick.html', **user_data)

@app.route('/api/quick_services/all', methods=['GET'])
@login_required
def get_all_quick_services_api():
    """Get all active services from Quickservice model for the interface"""
    try:
        search = request.args.get('search', '')
        query = Quickservice.query.filter_by(status='active')
        if search:
            like_term = f"%{search}%"
            query = query.filter(Quickservice.quickservicename.ilike(like_term))

        quick_services = query.all()
        services = []
        for qs in quick_services:
            services.append({
                'id': qs.quickserviceid,
                'name': qs.quickservicename,
                'price': qs.quickserviceprice,
                'unit': getattr(qs, 'unit', 'Per'),
                'icon': 'fa-cog',  # Default icon for quick services
                'category': 'quick'
            })

        return jsonify(services)
    except Exception as e:
        print(f"Error fetching quick services: {e}")
        return jsonify([]), 200

@app.route('/api/quick_services/transaction', methods=['POST'])
@login_required
def create_quick_service_transaction():
    """Create a new quick service transaction"""
    try:
        data = request.json
        
        # Validate required data
        required_fields = ['services_data', 'total_amount', 'amount_received', 'payment_method']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'{field} is required'}), 400
        
        # Calculate change
        change_amount = data['amount_received'] - data['total_amount']
        if change_amount < 0:
            change_amount = 0
        
        # Generate order number and transaction ID
        order_number = f"QS-{datetime.now().strftime('%Y%m%d')}-{QuickTask.query.count() + 99:04d}"
        transaction_id = f"TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{session.get('user_id',0)}"
        
        # Create QuickTask record - MAIN RECORD FOR QUICK SERVICE ORDER
        quick_task = QuickTask(
            order_number=order_number,
            transaction_id=transaction_id,
            customer_name=data.get('customer_name', 'Walk-in Customer'),
            customer_phone=data.get('customer_phone'),
            customer_email=data.get('customer_email'),
            staff_id=session.get('user_id'),
            staff_name=session.get('name', 'Unknown Staff'),
            branch_id=session.get('branch_id'),
            branch_name=session.get('branch_name') or session.get('branch', ''),
            subtotal=data.get('subtotal', data['total_amount']),
            tax=data.get('tax', 0),
            discount=data.get('discount', 0),
            total_amount=data['total_amount'],
            amount_received=data['amount_received'],
            change_amount=change_amount,
            payment_method=data['payment_method'],
            status='completed',
            notes=data.get('notes', '')
        )
        db.session.add(quick_task)
        db.session.flush()  # Get the ID before adding items
        
        # Add QuickTaskItems for each service
        if data.get('services_data') and isinstance(data['services_data'], list):
            for service_item in data['services_data']:
                quick_task_item = QuickTaskItem(
                    task_id=quick_task.id,
                    service_name=service_item.get('name', 'Unknown Service'),
                    service_code=service_item.get('service_code'),
                    quantity=service_item.get('quantity', 1),
                    unit_price=service_item.get('price', 0),
                    total_price=service_item.get('total', service_item.get('price', 0) * service_item.get('quantity', 1)),
                    description=service_item.get('description', '')
                )
                db.session.add(quick_task_item)
        
        # Also create a Task record for backward compatibility and reporting
        service = Service.query.filter_by(service_type='normal').first()
        if not service:
            # Create a default service
            service = Service(
                service_code='QS-DEFAULT',
                name='Quick Service',
                service_type='normal',
                price=0,
                fee=0,
                charge=0,
                description='Quick service transaction',
                department='Quick Services',
                status='active'
            )
            db.session.add(service)
            db.session.flush()
        
        # Create task for quick service transaction (for reporting)
        task = Task(
            order_no=order_number,
            customer_name=data.get('customer_name', 'Walk-in Customer'),
            customer_phone=data.get('customer_phone', ''),
            customer_email=data.get('customer_email', ''),
            customer_type='visiting',
            service_id=service.id,
            service_name='Quick Service Transaction',
            service_price=0,
            service_fee=0,
            service_charge=data['total_amount'],
            assigned_to_id=session.get('user_id'),
            assigned_to_name=session.get('name'),
            branch_id=session.get('branch_id'),
            branch_name=session.get('branch_name') or session.get('branch', ''),
            payment_mode=data['payment_method'],
            total_amount=data['total_amount'],
            paid_amount=data['amount_received'],
            due_amount=max(0, data['total_amount'] - data['amount_received']),
            status='completed',
            priority='medium',
            department='Quick Services',
            created_by_id=session.get('user_id'),
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            completion_notes=f"Quick Service Transaction. Services: {json.dumps(data['services_data'])}",
            description=f"Quick Service Transaction - {len(data.get('services_data', []))} items"
        )
        db.session.add(task)
        db.session.flush()
        
        # Add payment record
        if data['amount_received'] > 0:
            payment = TaskPayment(
                task_id=task.id,
                amount=data['amount_received'],
                payment_mode=data['payment_method'],
                payment_date=datetime.now(timezone.utc),
                collected_by=session.get('name', 'Staff'),
                notes='Quick service payment'
            )
            db.session.add(payment)
        
        # Update or create customer record
        if data.get('customer_phone'):
            customer = Customer.query.filter_by(phone=data['customer_phone']).first()
            if customer:
                # Update existing customer
                customer.total_services += 1
                customer.total_spent += data['total_amount']
                customer.last_service_date = datetime.now(timezone.utc)
            else:
                # Create new customer
                customer = Customer(
                    phone=data['customer_phone'],
                    name=data.get('customer_name', 'Walk-in Customer'),
                    email=data.get('customer_email', ''),
                    total_services=1,
                    total_spent=data['total_amount'],
                    last_service_date=datetime.now(timezone.utc)
                )
                db.session.add(customer)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Transaction completed successfully',
            'order_number': order_number,
            'transaction_id': transaction_id,
            'quick_task_id': quick_task.id,
            'task_id': task.id,
            'change_amount': change_amount
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/quick_services/transactions', methods=['GET'])
@login_required
@role_required(['admin', 'manager', 'staff'])
def get_quick_service_transactions():
    """Get quick service transactions.

    Admin/manager can filter by branch/staff/date. Staff can only view their own transactions.
    Accepts query params: date=today | from / to (YYYY-MM-DD) | staff (username) | staff_id | branch_id
    """
    try:
        user = User.query.get(session['user_id'])

        # Get filter parameters (support multiple param names from the frontend)
        date_param = request.args.get('date')
        start_date = request.args.get('from') or request.args.get('start_date')
        end_date = request.args.get('to') or request.args.get('end_date')
        staff_param = request.args.get('staff') or request.args.get('staff_username')
        staff_id = request.args.get('staff_id')
        branch_id = request.args.get('branch') or request.args.get('branch_id')

        # Build base query
        query = Task.query.filter_by(department='Quick Services', status='completed')

        # Quick "today" shortcut
        if date_param == 'today':
            today = datetime.utcnow().date()
            start_dt = datetime.combine(today, datetime.min.time())
            end_dt = start_dt + timedelta(days=1)
            query = query.filter(Task.created_at >= start_dt, Task.created_at < end_dt)

        # Apply explicit from/to date filters if provided
        if start_date:
            try:
                sd = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(Task.created_at >= sd)
            except ValueError:
                pass
        if end_date:
            try:
                ed = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(Task.created_at < ed)
            except ValueError:
                pass

        # Branch scoping: managers see their branch by default
        if user.post and user.post.lower() == 'manager' and user.branch_id:
            query = query.filter(Task.branch_id == user.branch_id)
        elif branch_id and branch_id != 'all':
            try:
                query = query.filter(Task.branch_id == int(branch_id))
            except (TypeError, ValueError):
                pass

        # Staff scoping: staff can only view their own transactions
        if user.post and user.post.lower() == 'staff':
            query = query.filter(Task.assigned_to_id == user.id)
        else:
            # For admin/manager, apply staff filter if provided
            if staff_id and staff_id != 'all':
                try:
                    query = query.filter(Task.assigned_to_id == int(staff_id))
                except (TypeError, ValueError):
                    pass
            elif staff_param and staff_param != 'all':
                # try to resolve username to user id
                staff_user = User.query.filter((User.useridname == staff_param) | (User.username == staff_param)).first()
                if staff_user:
                    query = query.filter(Task.assigned_to_id == staff_user.id)

        # Order by date (newest first)
        query = query.order_by(Task.created_at.desc())
        
        # Limit results
        limit = request.args.get('limit', 100, type=int)
        tasks = query.limit(limit).all()
        
        # Format transactions
        transactions = []
        for task in tasks:
            # Parse services from completion_notes if available
            services_data = []
            try:
                if task.completion_notes and 'Services:' in task.completion_notes:
                    services_str = task.completion_notes.split('Services:')[1].strip()
                    services_data = json.loads(services_str)
            except:
                services_data = [{'name': task.service_name, 'quantity': 1, 'price': task.total_amount}]
            
            transactions.append({
                'id': task.id,
                'order_no': task.order_no,
                'transaction_id': task.order_no,
                'customer_name': task.customer_name,
                'customer_phone': task.customer_phone,
                'customer_email': task.customer_email,
                'services': services_data,
                'total_amount': float(task.total_amount),
                'paid_amount': float(task.paid_amount),
                'due_amount': float(task.due_amount),
                'change_amount': float(task.paid_amount - task.total_amount) if task.paid_amount > task.total_amount else 0,
                'payment_method': task.payment_mode,
                'staff_name': task.assigned_to_name or 'N/A',
                'branch_name': task.branch_name or 'N/A',
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None
            })
        
        return jsonify({
            'success': True,
            'transactions': transactions,
            'total': len(transactions)
        })
    except Exception as e:
        print(f"Error in get_quick_service_transactions: {e}")
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/quick_tasks', methods=['GET'])
@login_required
@role_required(['admin', 'manager', 'staff'])
def get_quick_tasks():
    """Get all quick service tasks/orders"""
    try:
        # Filter by staff if not admin/manager
        user = User.query.get(session.get('user_id'))
        if user and user.post not in ['admin', 'manager']:
            # Staff can only see their own tasks
            quick_tasks = QuickTask.query.filter_by(staff_id=session.get('user_id')).all()
        else:
            # Admin and managers can see all
            quick_tasks = QuickTask.query.all()
        
        # Apply filters
        customer_phone = request.args.get('customer_phone')
        if customer_phone:
            quick_tasks = [qt for qt in quick_tasks if qt.customer_phone == customer_phone]
        
        start_date = request.args.get('start_date')
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
            quick_tasks = [qt for qt in quick_tasks if qt.created_at >= start_dt]
        
        end_date = request.args.get('end_date')
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
            quick_tasks = [qt for qt in quick_tasks if qt.created_at <= end_dt]
        
        # Convert to list of dicts
        tasks_data = []
        for task in quick_tasks:
            task_dict = task.to_dict()
            task_dict['items'] = [item.to_dict() for item in task.items]
            tasks_data.append(task_dict)
        
        # Sort by created_at descending
        tasks_data.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'tasks': tasks_data,
            'total': len(tasks_data)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/quick_tasks/<int:task_id>', methods=['GET'])
@login_required
def get_quick_task_detail(task_id):
    """Get detailed information for a specific quick task"""
    try:
        quick_task = QuickTask.query.get(task_id)
        if not quick_task:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        # Check permissions
        user = User.query.get(session.get('user_id'))
        if user and user.post not in ['admin', 'manager']:
            if quick_task.staff_id != session.get('user_id'):
                return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        task_dict = quick_task.to_dict()
        task_dict['items'] = [item.to_dict() for item in quick_task.items]
        
        return jsonify({
            'success': True,
            'task': task_dict
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/quick_services/stats', methods=['GET'])
@login_required
def get_quick_service_stats():
    """Get quick service statistics"""
    try:
        period = request.args.get('period', 'today')
        today = datetime.now(timezone.utc).date()
        
        # Query tasks that are quick service transactions (completed today)
        if period == 'today':
            tasks = Task.query.filter(
                Task.department == 'Quick Services',
                func.date(Task.created_at) == today,
                Task.status == 'completed'
            ).all()
        else:
            # For other periods, you can extend this
            tasks = Task.query.filter(
                Task.department == 'Quick Services',
                Task.status == 'completed'
            ).all()
        
        total_orders = len(tasks)
        total_revenue = sum(task.total_amount for task in tasks)
        unique_customers = len(set(task.customer_phone for task in tasks if task.customer_phone))
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        return jsonify({
            'total_orders': total_orders,
            'total_revenue': float(total_revenue),
            'unique_customers': unique_customers,
            'avg_order_value': float(avg_order_value)
        })
    except Exception as e:
        print(f"Error in get_quick_service_stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/quick_services/customer', methods=['GET'])
@login_required
def get_quick_service_customer():
    """Get customer info for quick services"""
    try:
        phone = request.args.get('phone', '').strip()
        if phone:
            # Check in Customer table
            customer = Customer.query.filter_by(phone=phone).first()
            if customer:
                return jsonify({
                    'exists': True,
                    'name': customer.name,
                    'email': customer.email or '',
                    'total_transactions': customer.total_services,
                    'total_spent': customer.total_spent,
                    'last_service_date': customer.last_service_date.strftime('%Y-%m-%d') if customer.last_service_date else None
                })
            # Also check in Task table for existing customers
            task_customer = Task.query.filter_by(customer_phone=phone).order_by(Task.created_at.desc()).first()
            if task_customer:
                # Count total services from tasks
                total_tasks = Task.query.filter_by(customer_phone=phone).count()
                total_spent = db.session.query(func.sum(Task.total_amount)).filter_by(customer_phone=phone).scalar() or 0
                return jsonify({
                    'exists': True,
                    'name': task_customer.customer_name,
                    'email': task_customer.customer_email or '',
                    'total_transactions': total_tasks,
                    'total_spent': float(total_spent),
                    'last_service_date': None
                })
        return jsonify({'exists': False})
    except Exception as e:
        print(f"Error in get_quick_service_customer: {e}")
        return jsonify({'exists': False, 'error': str(e)}), 500

@app.route('/api/quick_services/search', methods=['GET'])
@login_required
def search_quick_services():
    """Search quick services"""
    try:
        query = request.args.get('q', '')
        if not query or len(query) < 2:
            return jsonify([])
        
        services = db.search_quick_services(query)
        return jsonify(services)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ================= STAFF PERFORMANCE REPORT ENDPOINT =================
@app.route('/api/reports/staff-performance', methods=['GET'])
@login_required
@role_required(['admin', 'manager', 'staff'])
def get_staff_performance_detailed_report():
    """Get detailed staff performance report for Admin Report > Staff Performance tab"""
    try:
        user = User.query.get(session['user_id'])
        
        # Get parameters
        staff_id = request.args.get('staff_id')
        branch_id = request.args.get('branch_id')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Base query
        query = Task.query
        
        # Date filter
        if date_from:
            try:
                start_dt = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(Task.created_at >= start_dt)
            except ValueError:
                pass
        
        if date_to:
            try:
                end_dt = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(Task.created_at < end_dt)
            except ValueError:
                pass
                
        # Role-based scoping
        if user.post.lower() == 'staff':
            # Staff can only see their own tasks
            query = query.filter(Task.assigned_to_id == user.id)
        elif user.post.lower() == 'manager':
            # Manager sees branch tasks, or specific staff if selected
            if user.branch_id:
                query = query.filter(Task.branch_id == user.branch_id)
            if staff_id and staff_id != 'all':
                query = query.filter(Task.assigned_to_id == int(staff_id))
        elif user.post.lower() == 'admin':
            if branch_id and branch_id != 'all':
                query = query.filter(Task.branch_id == int(branch_id))
            if staff_id and staff_id != 'all':
                query = query.filter(Task.assigned_to_id == int(staff_id))
                
        tasks = query.order_by(Task.created_at.desc()).all()
        
        # --- Metrics Calculation ---
        total_tasks = len(tasks)
        completed_tasks = [t for t in tasks if t.status == 'completed']
        pending_tasks = [t for t in tasks if t.status == 'pending']
        in_progress_tasks = [t for t in tasks if t.status == 'in_progress']
        cancelled_tasks = [t for t in tasks if t.status == 'cancelled']
        
        completion_rate = (len(completed_tasks) / total_tasks * 100) if total_tasks > 0 else 0
        
        # Calculate total revenue correctly based on payment mode
        total_revenue = 0
        for t in tasks:
            if t.is_self_pay:
                total_revenue += float(t.service_fee or 0)
            else:
                total_revenue += float(t.service_price or t.total_amount or 0)
        
        # Avg completion time (simple approximation)
        total_hours = 0
        count_with_time = 0
        for t in completed_tasks:
            if t.created_at and t.completed_at:
                diff = (t.completed_at - t.created_at).total_seconds() / 3600
                total_hours += diff
                count_with_time += 1
        avg_time = (total_hours / count_with_time) if count_with_time > 0 else 0
        
        # Tasks per day (approximate based on date range or 30 days)
        days_span = 30
        if date_from and date_to:
            try:
                d1 = datetime.strptime(date_from, '%Y-%m-%d')
                d2 = datetime.strptime(date_to, '%Y-%m-%d')
                days_span = max(1, (d2 - d1).days + 1)
            except:
                pass
        avg_tasks_per_day = total_tasks / days_span
        avg_revenue = total_revenue / days_span
        
        metrics = {
            'avg_completion_time': round(avg_time, 1),
            'completion_rate': round(completion_rate, 1),
            'avg_tasks_per_day': round(avg_tasks_per_day, 1),
            'avg_revenue': round(avg_revenue, 2)
        }
        
        # --- Trend Data (Last 7 days or range) ---
        trend_dates = []
        trend_completed = []
        trend_pending = []
        
        # Iterate last 7 days from today (or based on query)
        base_date = datetime.now()
        for i in range(6, -1, -1):
            d = base_date - timedelta(days=i)
            d_str = d.strftime('%Y-%m-%d')
            display_date = d.strftime('%d %b')
            
            # Simple count for that day in result set
            day_tasks = [t for t in tasks if t.created_at and t.created_at.strftime('%Y-%m-%d') == d_str]
            c_count = len([t for t in day_tasks if t.status == 'completed'])
            p_count = len([t for t in day_tasks if t.status == 'pending'])
            
            trend_dates.append(display_date)
            trend_completed.append(c_count)
            trend_pending.append(p_count)
            
        trend_data = {
            'dates': trend_dates,
            'completed': trend_completed,
            'pending': trend_pending
        }
        
        # --- Breakdown ---
        breakdown = [
            {'status': 'completed', 'count': len(completed_tasks), 'percentage': (len(completed_tasks)/total_tasks*100) if total_tasks else 0},
            {'status': 'pending', 'count': len(pending_tasks), 'percentage': (len(pending_tasks)/total_tasks*100) if total_tasks else 0},
            {'status': 'in_progress', 'count': len(in_progress_tasks), 'percentage': (len(in_progress_tasks)/total_tasks*100) if total_tasks else 0},
            {'status': 'cancelled', 'count': len(cancelled_tasks), 'percentage': (len(cancelled_tasks)/total_tasks*100) if total_tasks else 0}
        ]
        
        # --- Task Details (Top 100 for table) ---
        task_details = []
        for t in tasks[:100]:
            # Calculate revenue correctly for each task
            if t.is_self_pay:
                revenue = float(t.service_fee or 0)
            else:
                revenue = float(t.service_price or t.total_amount or 0)
            
            task_details.append({
                'id': t.id,
                'order_no': t.order_no or t.id,
                'task_name': t.service_name or 'N/A', # Fallback for old code
                'service_name': t.service_name or 'N/A',
                'customer_name': t.customer_name or 'Walk-in',
                'service_type': 'Normal', # Simplified
                'assigned_date': t.created_at.isoformat() if t.created_at else None,
                'completed_date': t.completed_at.isoformat() if t.completed_at else None,
                'status': t.status,
                'rating': 0, # Placeholder
                'revenue': revenue
            })
            
        return jsonify({
            'success': True,
            'metrics': metrics,
            'trend_data': trend_data,
            'breakdown': breakdown,
            'task_details': task_details,
            'today_data': [len(completed_tasks), len(pending_tasks), len(in_progress_tasks), len(cancelled_tasks)] # Simplified for pie chart
        })
        
    except Exception as e:
        print(f"Error in detailed staff performance report: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ================= QUICK SERVICE REPORT ENDPOINT =================
@app.route('/api/reports/quick-services', methods=['GET'])
@login_required
@role_required(['admin', 'manager', 'staff'])
def get_quick_service_report():
    """Get comprehensive quick service report - ENHANCED VERSION"""
    try:
        user = User.query.get(session['user_id'])
        
        # Get filter parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        branch_id = request.args.get('branch_id')
        
        # Parse dates
        try:
            if start_date:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            else:
                start_dt = datetime.now() - timedelta(days=30)
            
            if end_date:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            else:
                end_dt = datetime.now() + timedelta(days=1)
        except ValueError:
            return jsonify({'error': 'Invalid date format', 'success': False}), 400
            
        # Ensure naive datetimes
        if start_dt.tzinfo: start_dt = start_dt.replace(tzinfo=None)
        if end_dt.tzinfo: end_dt = end_dt.replace(tzinfo=None)
        
        # Get additional filter parameters
        service_id = request.args.get('service_id')
        staff_id = request.args.get('staff_id')
        
        query = Task.query.filter(
            Task.department == 'Quick Services',
            Task.status == 'completed',
            Task.created_at >= start_dt,
            Task.created_at < end_dt
        )
        
        # Apply additional filters
        if service_id and service_id != 'all':
            try:
                query = query.filter(Task.service_id == int(service_id))
            except ValueError:
                pass
        
        if staff_id and staff_id != 'all':
            try:
                query = query.filter(Task.assigned_to_id == int(staff_id))
            except ValueError:
                pass
        
        # Apply branch filter
        user_role = getattr(user, 'post', None) or session.get('role', '')
        if user_role and user_role.lower() == 'manager' and user.branch_id:
            query = query.filter(Task.branch_id == user.branch_id)
        elif branch_id and branch_id != 'all':
            try:
                query = query.filter(Task.branch_id == int(branch_id))
            except ValueError:
                pass
        
        tasks = query.order_by(Task.created_at.desc()).all()
        
        # Calculate statistics
        total_orders = len(tasks)
        total_revenue = sum(float(t.total_amount or 0) for t in tasks)
        total_paid = sum(float(t.paid_amount or 0) for t in tasks)
        total_due = sum(float(t.due_amount or 0) for t in tasks)
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        unique_customers = len(set(t.customer_phone for t in tasks if t.customer_phone))
        
        # Payment methods
        payment_methods = {}
        for task in tasks:
            method = task.payment_mode or 'Cash'
            payment_methods[method] = payment_methods.get(method, 0) + 1
        
        # Hourly data (24 hours)
        hourly_data = {str(i): 0 for i in range(24)}
        for task in tasks:
            if task.created_at:
                hour = task.created_at.hour
                hourly_data[str(hour)] = hourly_data.get(str(hour), 0) + float(task.total_amount or 0)
        
        # Daily trend
        daily_trend = []
        current_date = start_dt
        while current_date < end_dt:
            # Filter tasks ensuring naive date comparison
            day_tasks = [t for t in tasks if t.created_at and (t.created_at.replace(tzinfo=None) if t.created_at.tzinfo else t.created_at).date() == current_date.date()]
            daily_trend.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'revenue': sum(float(t.total_amount or 0) for t in day_tasks),
                'orders': len(day_tasks)
            })
            current_date += timedelta(days=1)
        
        # Format transactions
        transactions = []
        for task in tasks[:100]:  # Limit to 100 most recent
            transactions.append({
                'id': task.id,
                'order_no': task.order_no,
                'customer_name': task.customer_name or 'Walk-in',
                'customer_phone': task.customer_phone or '',
                'total_amount': float(task.total_amount or 0),
                'paid_amount': float(task.paid_amount or 0),
                'payment_method': task.payment_mode or 'Cash',
                'staff_name': task.assigned_to_name or 'N/A',
                'branch_name': task.branch_name or 'N/A',
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'service_type': 'Quick Service'
            })
        
        return jsonify({
            'success': True,
            'statistics': {
                'total_orders': total_orders,
                'total_revenue': round(total_revenue, 2),
                'total_paid': round(total_paid, 2),
                'total_due': round(total_due, 2),
                'avg_order_value': round(avg_order_value, 2),
                'unique_customers': unique_customers
            },
            'payment_methods': payment_methods,
            'hourly_data': hourly_data,
            'daily_trend': daily_trend,
            'transactions': transactions
        })
        
    except Exception as e:
        print(f"Error in get_quick_service_report: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e), 'success': False}), 500



@app.route('/api/reports/debug', methods=['GET'])
@login_required
@role_required(['admin'])
def debug_reports():
    """Debug endpoint to check data availability"""
    try:
        # Count tasks
        total_tasks = Task.query.count()
        completed_tasks = Task.query.filter_by(status='completed').count()
        quick_tasks = Task.query.filter_by(department='Quick Services').count()
        
        # Count users
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        
        # Count branches
        total_branches = BranchNew.query.count()
        
        # Count attendance
        total_attendance = Attendance.query.count()
        
        # Sample task
        sample_task = Task.query.first()
        
        return jsonify({
            'success': True,
            'counts': {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'quick_tasks': quick_tasks,
                'total_users': total_users,
                'active_users': active_users,
                'total_branches': total_branches,
                'total_attendance': total_attendance
            },
            'sample_task': sample_task.to_dict() if sample_task else None,
            'user_role': session.get('role'),
            'user_id': session.get('user_id')
        })
        
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500
    
# Add cleanup function
@atexit.register
def cleanup():
    """Clean up database connections on shutdown"""
    print("Cleaning up database connections...")
    try:
        db.close_connection()
    except:
        pass

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# ==================== INITIALIZATION ====================

def initialize_database():
    """Initialize database on startup"""
    try:
        # This will trigger database initialization
        print("Initializing database...")
        # The database is already initialized in the Database class __init__
    except Exception as e:
        print(f"Error initializing database: {e}")
#=================Manager=====================
@app.route('/manager')
def manager_dashboard():
    """Render manager dashboard page"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    # Only allow managers and admins to access this page
    if user.post.lower() not in ['admin', 'manager']:
        flash('This page is only accessible to managers and administrators', 'error')
        
        # Check if staff has checked in today
        today = datetime.now(timezone.utc).date()
        existing_checkin = Attendance.query.filter(
            Attendance.user_id == user.id,
            db.func.date(Attendance.created_at) == today,
            Attendance.status == 'checked_in'
        ).first()
        
        if existing_checkin:
            return redirect(url_for('staff_dashboard'))
        else:
            return redirect(url_for('staff_checking'))
    
    return render_template('task.html',
                         user_id=user.id,
                         user_name=user.username,
                         username=user.useridname,
                         user_role=user.post)

@app.route('/api/staff', methods=['GET'])
@login_required
def get_staff_api():
    """Get staff members - accessible to all authenticated users"""
    try:
        user = User.query.get(session['user_id'])
        
        # Build query
        query = User.query.filter(User.is_active == True)
        
        # Managers can only see staff from their branch
        if user.post.lower() == 'manager' and user.branch_id:
            query = query.filter(User.branch_id == user.branch_id)
        
        # Exclude admins
        query = query.filter(User.post != 'Administrator')
        
        # Get staff
        staff = query.order_by(User.username).all()
        
        # Convert to dictionary
        staff_data = []
        for s in staff:
            staff_data.append({
                'id': s.id,
                'username': s.useridname,
                'name': s.username,
                'post': s.post,
                'role': s.post,  # Alias for compatibility
                'email': s.useremail,
                'phone': s.userphone,
                'branch_id': s.branch_id,
                'branch_name': s.branch.name if s.branch else None,
                'department': s.department,
                'is_active': s.is_active
            })
        
        return jsonify(staff_data)
        
    except Exception as e:
        print(f"Error in get_staff_api: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/manager/staff', methods=['GET'])
@login_required
def get_manager_staff_api():
    """Get staff members for manager"""
    try:
        user = User.query.get(session['user_id'])
        
        if user.post.lower() not in ['admin', 'manager']:
            return jsonify({'error': 'Access denied'}), 403
        
        # Build query
        query = User.query.filter(User.is_active == True)
        
        # Managers can only see staff from their branch
        if user.post.lower() == 'manager' and user.branch_id:
            query = query.filter(User.branch_id == user.branch_id)
        
        # Exclude admins
        query = query.filter(User.post != 'Administrator')
        
        # Get staff
        staff = query.order_by(User.username).all()
        
        # Convert to dictionary
        staff_data = []
        for s in staff:
            staff_data.append({
                'id': s.id,
                'username': s.useridname,
                'name': s.username,
                'post': s.post,
                'email': s.useremail,
                'phone': s.userphone,
                'branch_id': s.branch_id,
                'branch_name': s.branch.name if s.branch else None,
                'department': s.department,
                'is_active': s.is_active
            })
        
        return jsonify(staff_data)
        
    except Exception as e:
        print(f"Error in get_manager_staff_api: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks', methods=['POST'])
@login_required
def create_task_api():
    """Create a new task"""
    try:
        # Eagerly load the branch relationship to ensure it's available
        user = db.session.query(User).options(db.joinedload(User.branch)).filter_by(id=session['user_id']).first()
        today = datetime.now(timezone.utc)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        print(f"DEBUG: Creating task for user {user.username}")
        print(f"DEBUG: User branch_id: {user.branch_id}")
        if user.branch:
            print(f"DEBUG: User branch name: {user.branch.name}, code: {user.branch.code}")
        else:
            print("DEBUG: user.branch is None")
        print(f"DEBUG: Session branch_id: {session.get('branch_id')}, branch_code: {session.get('branch_code')}")
        
        data = request.json
        
        # Validate required fields
        if not data.get('customer_name'):
            return jsonify({'error': 'Customer name is required'}), 400
        if not data.get('customer_phone'):
            return jsonify({'error': 'Customer phone is required'}), 400
        if not data.get('service_id'):
            return jsonify({'error': 'Service is required'}), 400
        
        # Order Number will be set to ID after flush
        order_no = "PENDING"
        
        # Get service details
        service_id = data.get('service_id')
        service = Service.query.get(service_id) if service_id else None
        
        if not service:
            return jsonify({'error': 'Service not found'}), 404
        
        # Calculate total amount
        is_self_pay_service = service.fee_pay_mode == 'self_pay'
        
        # Use service_price from the request data (which now correctly sends service.price from frontend)
        # Fallback to service.price from database (total customer pays)
        service_price_value = float(data.get('service_price', service.price))
        
        # If self-pay, we only collect the fee, not the full price
        if is_self_pay_service:
            total_amount_to_collect = service.fee
        else:
            # For regular payments, total_amount should be the service price (total customer pays)
            total_amount_to_collect = service_price_value
            
        paid_amount = float(data.get('paid_amount', 0))
        due_amount = max(0, total_amount_to_collect - paid_amount)
        
        # Handle assignment
        assignment_type = data.get('assignment_type', 'myself')
        assigned_to_id = None
        in_openplace = False
        
        if assignment_type == 'myself':
            assigned_to_id = user.id
            assigned_to_name = user.username
        elif assignment_type == 'openplace':
            in_openplace = True
            assigned_to_id = None
            assigned_to_name = None
        elif assignment_type == 'specific':
            # Handle both user ID and username
            assigned_to_value = data.get('assigned_to')
            if assigned_to_value:
                # If it's a username (string), find the user by username
                if isinstance(assigned_to_value, str) and not assigned_to_value.isdigit():
                    assigned_staff = User.query.filter_by(useridname=assigned_to_value).first()
                    assigned_to_id = assigned_staff.id if assigned_staff else None
                else:
                    # It's a numeric ID
                    assigned_to_id = int(assigned_to_value)
                    assigned_staff = User.query.get(assigned_to_id)
            else:
                assigned_staff = None
                assigned_to_id = None
            assigned_to_name = assigned_staff.username if assigned_staff else None
        
        # Create task
        task = Task(
            order_no=order_no,
            customer_name=data['customer_name'],
            customer_phone=data['customer_phone'],
            customer_email=data.get('customer_email'),
            customer_type=data.get('customer_type', 'visiting'),
            service_id=service.id,
            service_name=service.name,
            service_price=service.price,
            service_fee=service.fee,
            service_charge=service.charge, # Keep original service charge (Total)
            assigned_to_id=assigned_to_id,
            assigned_to_name=assigned_to_name,
            assignment_type=assignment_type,
            in_openplace=in_openplace,
            branch_id=user.branch_id,
            branch_name=user.branch.name if user.branch else None,
            payment_mode=data.get('payment_mode', 'cash'),
            total_amount=total_amount_to_collect,
            paid_amount=paid_amount,
            due_amount=due_amount,
            is_self_pay=is_self_pay_service or data.get('payment_mode') == 'self_pay',
            priority=data.get('priority', 'medium'),
            description=data.get('description'),
            created_by_id=user.id,
            created_at=today
        )
        
        # Ensure branch_name is set properly (fix for when user.branch relationship isn't loaded)
        if not task.branch_name and task.branch_id:
            # Try session first
            if session.get('branch_name'):
                task.branch_name = session.get('branch_name')
            else:
                # Fallback to explicit query
                branch = BranchNew.query.get(task.branch_id)
                if branch:
                    task.branch_name = branch.name
        
        # Handle hybrid payment
        if data.get('payment_mode') == 'hybrid':
            task.is_hybrid = True
            task.online_payment = float(data.get('online_amount', 0))
            task.cash_payment = float(data.get('cash_amount', 0))
        
        # Add self-pay details
        if task.is_self_pay:
            task.self_pay_service_price = service.price
            task.self_pay_service_fee = service.fee
            task.self_pay_customer_pays = service.price + service.fee
            task.self_pay_revenue = service.fee # Updated: Service Fee is our revenue in self-pay
        
        db.session.add(task)
        db.session.flush() # Generate ID
        
        # Format Order Number: use BranchNew.code when available, else session, else HO
        # Example: {BRANCH_CODE}-{YYYYMMDDHHMMSS}
        branch_code = "HO"  # Default for Admin/No Branch / legacy users
        try:
            # For new schema, user.branch is a BranchNew instance
            if getattr(user, "branch", None) and getattr(user.branch, "code", None):
                branch_code = user.branch.code
            elif session.get('branch_code'):
                # Fallback to session if user.branch not set (e.g., just checked in)
                branch_code = session.get('branch_code')
        except Exception:
            # Fallback to numeric branch id if something goes wrong
            if getattr(user, "branch_id", None):
                branch_code = f"BR{user.branch_id}"
            elif session.get('branch_id'):
                branch_code = f"BR{session.get('branch_id')}"
            
        timestamp_str = today.strftime('%Y%m%d%H%M%S')
        task.order_no = f"{branch_code}-{timestamp_str}"
        
        db.session.commit()
        
        # Create status history entry
        status_history = TaskStatusHistory(
            task_id=task.id,
            new_status='pending',
            changed_by=user.username,
            changed_at=today
        )
        db.session.add(status_history)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Task created successfully',
            'task_id': task.id,
            'order_no': task.order_no
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in create_task_api: {str(e)}")
        return jsonify({'error': str(e)}), 500
@app.route('/api/tasks/<int:task_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def task_detail_api(task_id):
    """Get, update, or delete a task"""
    try:
        user = User.query.get(session['user_id'])
        
        if request.method == 'GET':
            task = Task.query.get(task_id)
            if not task:
                return jsonify({'error': 'Task not found'}), 404
            
            # Get status history
            status_history = TaskStatusHistory.query.filter_by(task_id=task_id).order_by(TaskStatusHistory.changed_at.desc()).all()
            
            # Get payments
            payments = TaskPayment.query.filter_by(task_id=task_id).order_by(TaskPayment.payment_date.desc()).all()
            
            # Get messages
            messages = TaskMessage.query.filter_by(task_id=task_id).order_by(TaskMessage.created_at.desc()).all()
            
            task_data = task.to_dict()
            
            # Add additional data
            task_data['status_history'] = [{
                'old_status': h.old_status,
                'new_status': h.new_status,
                'reason': h.reason,
                'changed_by': h.changed_by,
                'changed_at': h.changed_at.isoformat() if h.changed_at else None
            } for h in status_history]
            
            task_data['payments'] = [{
                'amount': p.amount,
                'payment_mode': p.payment_mode,
                'payment_date': p.payment_date.isoformat() if p.payment_date else None,
                'collected_by': p.collected_by,
                'notes': p.notes
            } for p in payments]
            
            task_data['messages'] = [{
                'sender_name': m.sender_name,
                'message': m.message,
                'created_at': m.created_at.isoformat() if m.created_at else None
            } for m in messages]
            
            return jsonify(task_data)
            
        elif request.method == 'PUT':
            task = Task.query.get(task_id)
            if not task:
                return jsonify({'error': 'Task not found'}), 404
            
            data = request.json
            
            # Update task fields
            if 'customer_name' in data:
                task.customer_name = data['customer_name']
            if 'customer_phone' in data:
                task.customer_phone = data['customer_phone']
            if 'customer_email' in data:
                task.customer_email = data['customer_email']
            if 'priority' in data:
                task.priority = data['priority']
            if 'description' in data:
                task.description = data['description']
            
            task.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Task updated successfully'
            })
            
        elif request.method == 'DELETE':
            # Only allow deletion of pending tasks
            task = Task.query.get(task_id)
            if not task:
                return jsonify({'error': 'Task not found'}), 404
            
            if task.status != 'pending':
                return jsonify({'error': 'Only pending tasks can be deleted'}), 400
            
            # Check permissions (only admin/manager)
            if user.post.lower() not in ['admin', 'manager']:
                return jsonify({'error': 'Access denied'}), 403
            
            db.session.delete(task)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Task deleted successfully'
            })
            
    except Exception as e:
        db.session.rollback()
        print(f"Error in task_detail_api: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/assign', methods=['PUT'])
@login_required
def assign_task_api(task_id):
    """Assign a task to a staff member"""
    try:
        user = User.query.get(session['user_id'])
        
        if user.post.lower() not in ['admin', 'manager']:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.json
        assigned_to_value = data.get('assigned_to')
        
        if not assigned_to_value:
            return jsonify({'error': 'Staff ID or username is required'}), 400
        
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Handle both username (string) and ID (integer)
        if isinstance(assigned_to_value, str) and not assigned_to_value.isdigit():
            # It's a username, find by username
            staff = User.query.filter_by(useridname=assigned_to_value).first()
        else:
            # It's a numeric ID
            staff = User.query.get(int(assigned_to_value))
        
        if not staff:
            return jsonify({'error': 'Staff not found'}), 404
        
        # Update task assignment
        task.assigned_to_id = staff.id
        task.assigned_to_name = staff.username
        task.in_openplace = False
        task.assigned_at = datetime.now(timezone.utc)
        task.updated_at = datetime.now(timezone.utc)
        
        # Create status history
        status_history = TaskStatusHistory(
            task_id=task.id,
            old_status=task.status,
            new_status='pending',  # Reset to pending when assigned
            reason='Task assigned to staff',
            changed_by=user.username,
            changed_at=datetime.now(timezone.utc)
        )
        db.session.add(status_history)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Task assigned successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in assign_task_api: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/take', methods=['PUT'])
@login_required
def take_task_api(task_id):
    """Take a task from open place"""
    try:
        user = User.query.get(session['user_id'])
        
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        if not task.in_openplace:
            return jsonify({'error': 'Task is not in open place'}), 400
        
        # Verify branch match for staff
        if user.post.lower() == 'staff' and user.branch_id:
            if task.branch_id != user.branch_id:
                return jsonify({'error': 'You can only take tasks from your branch'}), 403
        
        # Take the task
        task.assigned_to_id = user.id
        task.assigned_to_name = user.username
        task.in_openplace = False
        task.assigned_at = datetime.now(timezone.utc)
        task.updated_at = datetime.now(timezone.utc)
        
        # Create status history
        status_history = TaskStatusHistory(
            task_id=task.id,
            old_status=task.status,
            new_status='pending',
            reason='Task taken from open place',
            changed_by=user.username,
            changed_at=datetime.now(timezone.utc)
        )
        db.session.add(status_history)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Task taken successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in take_task_api: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/send-to-openplace', methods=['PUT'])
@login_required
def send_to_openplace_api(task_id):
    """Send a task to open place - Admin can send any task, others can only send pending tasks"""
    try:
        user = User.query.get(session['user_id'])
        
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Check permissions: Admin can send any task, Manager/Staff can only send pending tasks
        user_role = user.post.lower() if user.post else 'staff'
        is_admin = user_role == 'admin'
        is_manager = user_role == 'manager'
        
        # Allow: Admin (any task), Manager (any task), Staff (own pending tasks only)
        if user_role == 'staff' and task.assigned_to_id != user.id:
            return jsonify({'error': 'You can only send your own tasks to open place'}), 403
        
        # For staff: task must be pending
        if user_role == 'staff' and task.status != 'pending':
            return jsonify({'error': 'Only pending tasks can be sent to open place'}), 400
        
        # Admin can send any task, any status
        # Manager can send any task, any status
        # Staff can only send their own pending tasks
        
        # Send to open place
        task.in_openplace = True
        task.assigned_to_id = None
        task.assigned_to_name = None
        task.sent_to_openplace_at = datetime.now(timezone.utc)
        task.sent_by_id = user.id
        task.sent_by_name = user.username
        task.updated_at = datetime.now(timezone.utc)
        
        # Create status history
        status_history = TaskStatusHistory(
            task_id=task.id,
            old_status=task.status,
            new_status=task.status,  # Keep the current status
            reason='Task sent to open place',
            changed_by=user.username,
            changed_at=datetime.now(timezone.utc)
        )
        db.session.add(status_history)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Task sent to open place successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in send_to_openplace_api: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/status', methods=['PUT'])
@login_required
def update_task_status_api(task_id):
    """Update task status"""
    try:
        user = User.query.get(session['user_id'])
        
        data = request.json
        new_status = data.get('status')
        reason = data.get('reason', '')
        payment_amount = float(data.get('payment_amount', 0))
        payment_mode = data.get('payment_mode', '')
        extra_charges = data.get('extra_charges', {})
        completion_notes = data.get('completion_notes', '') or data.get('notes', '')
        
        if not new_status:
            return jsonify({'error': 'Status is required'}), 400
        
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        old_status = task.status
        task.status = new_status
        task.updated_at = datetime.now(timezone.utc)
        
        # Handle payment if provided
        if payment_amount > 0 and payment_mode:
            current_paid = task.paid_amount or 0
            task.paid_amount = current_paid + payment_amount
            task.due_amount = max(0, (task.total_amount or 0) - task.paid_amount)
            task.payment_mode = payment_mode
            
            # Record payment
            payment = TaskPayment(
                task_id=task.id,
                amount=payment_amount,
                payment_mode=payment_mode,
                payment_date=datetime.now(timezone.utc),
                collected_by=user.username,
                notes=f'Payment during status change - {reason}'
            )
            db.session.add(payment)
        
        # Handle extra charges
        if extra_charges:
            for charge_type, charge_amount in extra_charges.items():
                if charge_amount and float(charge_amount) > 0:
                    extra_charge = TaskExtraCharge(
                        task_id=task.id,
                        charge_type=charge_type,
                        amount=float(charge_amount),
                        description=f'Extra {charge_type} charge',
                        added_by=user.username
                    )
                    db.session.add(extra_charge)
                    # Add to total amount
                    task.total_amount = (task.total_amount or 0) + float(charge_amount)
                    task.due_amount = max(0, task.total_amount - (task.paid_amount or 0))
        
        # If completing task, set completion time
        if new_status == 'completed':
            task.completed_at = datetime.now(timezone.utc)
            task.completion_notes = completion_notes
        
        # Create status history
        status_history = TaskStatusHistory(
            task_id=task.id,
            old_status=old_status,
            new_status=new_status,
            reason=reason,
            changed_by=user.username,
            changed_at=datetime.now(timezone.utc)
        )
        db.session.add(status_history)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Task status updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in update_task_status_api: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/hold', methods=['PUT'])
@login_required
def hold_task_api(task_id):
    """Put task on hold"""
    try:
        user = User.query.get(session['user_id'])
        
        data = request.json
        reason = data.get('reason', '')
        notes = data.get('notes', '')
        paid_amount = float(data.get('paid_amount', 0))
        payment_mode = data.get('payment_mode', '')
        
        if not reason:
            return jsonify({'error': 'Reason is required'}), 400
        
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        old_status = task.status
        task.status = 'on_hold'
        task.updated_at = datetime.utcnow()
        
        # Handle payment if provided
        if paid_amount > 0 and payment_mode:
            current_paid = task.paid_amount or 0
            task.paid_amount = current_paid + paid_amount
            task.due_amount = max(0, (task.total_amount or 0) - task.paid_amount)
            
            # Record payment
            payment = TaskPayment(
                task_id=task.id,
                amount=paid_amount,
                payment_mode=payment_mode,
                payment_date=datetime.utcnow(),
                collected_by=user.username,
                notes=f'Payment while on hold - {notes}' if notes else 'Payment while on hold'
            )
            db.session.add(payment)
        
        # Create status history
        status_reason = reason
        if notes:
            status_reason += f' - {notes}'
        
        status_history = TaskStatusHistory(
            task_id=task.id,
            old_status=old_status,
            new_status='on_hold',
            reason=status_reason,
            changed_by=user.username,
            changed_at=datetime.utcnow()
        )
        db.session.add(status_history)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Task put on hold successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in hold_task_api: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/complete', methods=['PUT'])
@login_required
def complete_task_api(task_id):
    """Complete a task"""
    try:
        user = User.query.get(session['user_id'])
        
        data = request.json
        # Support both 'notes' and 'completion_notes' for backward compatibility
        completion_notes = data.get('completion_notes') or data.get('notes', '')
        payment_amount = float(data.get('payment_amount', 0))
        payment_mode = data.get('payment_mode', 'cash')
        due_reason = data.get('due_reason', '')
        due_reason_type = data.get('due_reason_type', '')  # offer, plan, other
        offer_amount = float(data.get('offer_amount', 0))
        remaining_due = float(data.get('remaining_due', 0))
        extra_charges = data.get('extra_charges', {})
        
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # 1. Handle extra charges FIRST to update total_amount
        if extra_charges:
            for charge_type, charge_amount in extra_charges.items():
                if charge_amount and float(charge_amount) > 0:
                    extra_charge = TaskExtraCharge(
                        task_id=task.id,
                        charge_type=charge_type,
                        amount=float(charge_amount),
                        description=f'Extra {charge_type} charge',
                        added_by=user.username
                    )
                    db.session.add(extra_charge)
                    # Add to total amount
                    task.total_amount = (task.total_amount or 0) + float(charge_amount)

        # 2. Now calculate new amounts after total_amount is finalized
        current_paid = task.paid_amount or 0
        total_amount = task.total_amount or 0
        
        # Calculate new paid amount and due amount
        # payment_amount from frontend is already amountAppliedToService + extraChargesTotal (the full collected_amount)
        new_paid_amount = current_paid + payment_amount
        new_due_amount = max(0, total_amount - new_paid_amount)
        
        # 3. Validate amounts
        if new_due_amount > 0 and not due_reason:
            return jsonify({
                'error': 'Please provide a reason for the remaining due amount'
            }), 400
        
        if new_paid_amount > total_amount + 0.01: # Allow for small float precision
            return jsonify({
                'error': f'Payment amount (₹{new_paid_amount}) cannot exceed total amount (₹{total_amount})'
            }), 400
        
        # 4. Update task record
        old_status = task.status
        task.status = 'completed'
        task.completed_at = datetime.utcnow()
        task.completion_notes = completion_notes
        task.updated_at = datetime.utcnow()
        task.paid_amount = new_paid_amount
        task.due_amount = new_due_amount
        task.payment_mode = payment_mode
        # Due reason, offer tracking (when completing with due)
        if new_due_amount > 0 and due_reason:
            task.is_offer = (due_reason_type == 'offer')
            task.offer_amount = offer_amount
            type_label = 'Offer/Discount' if due_reason_type == 'offer' else 'Payment Plan' if due_reason_type == 'plan' else 'Other'
            task.offer_reason = f"{type_label}: {due_reason}"
        
        # Handle Self-Pay flag if explicitly sent
        if data.get('is_self_pay'):
            task.is_self_pay = True
            if not task.self_pay_revenue:
                task.self_pay_service_price = task.service_price
                task.self_pay_service_fee = task.service_fee
                task.self_pay_revenue = task.service_fee
        
        # 5. Record payment(s)
        if payment_amount > 0:
            is_self_pay_completion = data.get('is_self_pay', payment_mode == 'self_pay')
            other_amount = float(data.get('other_amount', 0))
            other_amount_mode = data.get('other_amount_mode', 'cash')
            
            provider_name = data.get('provider_name', '')
            provider_phone = data.get('provider_phone', '')
            
            # Primary Fee Amount (Total Collected - Extra Amount)
            fee_to_record = payment_amount - other_amount
            
            if fee_to_record > 0:
                payment_notes = 'Final payment (Fee)'
                if new_due_amount > 0 and due_reason:
                    payment_notes += f' - Remaining due: ₹{new_due_amount:.2f}. Reason: {due_reason}'
                
                payment = TaskPayment(
                    task_id=task.id,
                    amount=fee_to_record,
                    payment_mode=payment_mode,
                    payment_date=datetime.utcnow(),
                    collected_by=user.username,
                    notes=payment_notes,
                    is_self_pay=is_self_pay_completion,
                    self_pay_provider_name=provider_name,
                    self_pay_provider_phone=provider_phone
                )
                db.session.add(payment)
            
            # Secondary "Other Amount" Payment
            if other_amount > 0:
                payment_other = TaskPayment(
                    task_id=task.id,
                    amount=other_amount,
                    payment_mode=other_amount_mode,
                    payment_date=datetime.utcnow(),
                    collected_by=user.username,
                    notes='Additional collection received during completion',
                    is_self_pay=is_self_pay_completion,
                    self_pay_provider_name=provider_name,
                    self_pay_provider_phone=provider_phone
                )
                db.session.add(payment_other)
        
        # 6. Create status history
        status_reason = 'Task completed'
        if due_reason and new_due_amount > 0:
            status_reason = f'Task completed. Remaining due: ₹{new_due_amount}. Reason: {due_reason}'
        
        status_history = TaskStatusHistory(
            task_id=task.id,
            old_status=old_status,
            new_status='completed',
            reason=status_reason,
            changed_by=user.username,
            changed_at=datetime.utcnow()
        )
        db.session.add(status_history)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Task completed successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in complete_task_api: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/reopen', methods=['PUT'])
@login_required
def reopen_completed_task_api(task_id):
    """Reopen a completed task - Admin only"""
    try:
        user = User.query.get(session['user_id'])
        
        # Check if user is admin
        user_role = (user.post or '').lower() if user else ''
        session_role = (session.get('role') or '').lower()
        effective_role = session_role or user_role
        
        if effective_role != 'admin':
            return jsonify({'error': 'Only admin can reopen completed tasks'}), 403
        
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        if task.status != 'completed':
            return jsonify({'error': 'Only completed tasks can be reopened'}), 400
        
        # Store original completion data
        original_completed_at = task.completed_at
        original_completion_notes = task.completion_notes
        
        # Update task status to pending
        old_status = task.status
        task.status = 'pending'
        task.completed_at = None
        task.completion_notes = None
        task.updated_at = datetime.utcnow()
        
        # Create status history record
        status_history = TaskStatusHistory(
            task_id=task.id,
            old_status=old_status,
            new_status='pending',
            reason='Task reopened by admin',
            changed_by=user.username,
            changed_at=datetime.utcnow()
        )
        db.session.add(status_history)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Task reopened successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in reopen_completed_task_api: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/cancel', methods=['PUT'])

@login_required
def cancel_task_api(task_id):
    """Cancel a task"""
    try:
        user = User.query.get(session['user_id'])
        
        data = request.json
        reason = data.get('reason', '')
        refund_amount = float(data.get('refund_amount', 0))
        refund_mode = data.get('refund_mode', '')
        notes = data.get('notes', '')
        cancelled_by = data.get('cancelled_by', user.useridname)
        
        if not reason or not reason.strip():
            return jsonify({'error': 'Cancellation reason is required'}), 400
        
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Check if task can be cancelled
        if task.status == 'completed':
            return jsonify({'error': 'Completed tasks cannot be cancelled'}), 400
        
        if task.status == 'cancelled':
            return jsonify({'error': 'Task is already cancelled'}), 400
        
        old_status = task.status
        task.status = 'cancelled'
        task.updated_at = datetime.now(timezone.utc)
        
        # Build cancellation reason with all details
        cancel_reason = f'Cancellation: {reason}'
        if notes:
            cancel_reason += f' | Notes: {notes}'
        if refund_amount > 0:
            cancel_reason += f' | Refund: ₹{refund_amount} via {refund_mode}'
        
        # Create status history
        status_history = TaskStatusHistory(
            task_id=task.id,
            old_status=old_status,
            new_status='cancelled',
            reason=cancel_reason,
            changed_by=cancelled_by,
            changed_at=datetime.now(timezone.utc)
        )
        db.session.add(status_history)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Task cancelled successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in cancel_task_api: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/services/search', methods=['GET'])
@login_required
def search_services_api():
    """Search services by name"""
    try:
        query = request.args.get('q', '')
        
        if not query or len(query) < 2:
            return jsonify([])
        
        services = Service.query.filter(
            (Service.name.ilike(f'%{query}%')) |
            (Service.description.ilike(f'%{query}%'))
        ).limit(10).all()
        
        services_data = [{
            'id': s.id,
            'name': s.name,
            'price': s.price,
            'fee': s.fee,
            'charge': s.charge,
            'description': s.description,
            'service_type': s.service_type,
            'department': s.department,
            'estimated_time': s.estimated_time
        } for s in services]
        
        return jsonify(services_data)
        
    except Exception as e:
        print(f"Error in search_services_api: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/customers/check', methods=['GET'])
@login_required
def check_customer_api():
    """Check if customer exists by phone"""
    try:
        phone = request.args.get('phone', '')
        
        if not phone:
            return jsonify({'exists': False})
        
        # Check in Customer table
        customer = Customer.query.filter_by(phone=phone).first()
        if customer:
            return jsonify({
                'exists': True,
                'name': customer.name,
                'email': customer.email,
                'total_services': customer.total_services,
                'total_spent': customer.total_spent
            })
        
        # Also check in Task table for existing customers
        task_customer = Task.query.filter_by(customer_phone=phone).first()
        if task_customer:
            return jsonify({
                'exists': True,
                'name': task_customer.customer_name,
                'email': task_customer.customer_email
            })
        
        return jsonify({'exists': False})
        
    except Exception as e:
        print(f"Error in check_customer_api: {str(e)}")
        return jsonify({'error': str(e)}), 500
@app.route('/manager/view/<int:id>')
@login_required
def manager_view(id):
    task = Task.query.get_or_404(id)
    return render_template('view_task.html', task=task)


@app.route('/manager/update/<int:id>', methods=['GET', 'POST'])
@login_required
def manager_update(id):
    """Edit task route - redirects back to manager dashboard for now"""
    task = Task.query.get_or_404(id)
    
    # For now, redirect back to manager dashboard
    # TODO: Create an edit modal or page if needed
    return redirect(url_for('manager_dashboard'))

@app.route('/api/logout', methods=['POST'])
@login_required
def logout_api():
    """Logout API endpoint"""
    try:
        session.clear()
        return jsonify({'success': True, 'message': 'Logged out successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    """Check if user is authenticated"""
    if 'user_id' not in session:
        return jsonify({'authenticated': False}), 401
    
    # Get user info from database
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return jsonify({'authenticated': False}), 401
    
    return jsonify({
        'authenticated': True,
        'user': {
            'user_id': session['user_id'],
            'username': session.get('username'),
            'name': session.get('name'),
            'post': user.post if user else session.get('role')
        },
        'user_id': session['user_id'],
        'username': session.get('username'),
        'name': session.get('name'),
        'role': session.get('role'),
        'branch_id': session.get('branch_id'),
        'branch_name': session.get('branch_name')
    })
@app.route('/debug/session')
def debug_session():
    """Debug endpoint to check session data"""
    return jsonify({
        'session_data': dict(session),
        'user_id_in_session': 'user_id' in session,
        'role_in_session': 'role' in session
    })
#========== switch mode================
@app.route('/switch-to-staff')
@login_required
def switch_to_staff():
    user = User.query.get(session['user_id'])
    if user and user.post.lower() == 'manager':
        session['mode'] = 'staff'
    return redirect(url_for('tasks'))

@app.route('/switch-to-manager')
@login_required
def switch_to_manager():
    session['mode'] = 'manager'
    return redirect(url_for('tasks'))
# ==================== STAFF TASK VIEWS ====================
@app.route('/staff/tasks')
@login_required
@role_required(['staff','manager','admin'])
def staff_tasks():
    """Staff tasks view - shows all tasks by default"""
    user_data = {
        'user_id': session.get('user_id'),
        'user_name': session.get('name'),
        'user_role': session.get('role'),
        'username': session.get('username'),
        'initial_tab': 'today'  # Default tab
    }
    return render_template('task.html', **user_data)
@app.route('/staff/tasks/openplace', endpoint='staff_openplace')
@login_required
@role_required(['staff','manager','admin'])
def staff_openplace_staff():
    """Staff open place tasks view"""
    user_data = {
        'user_id': session.get('user_id'),
        'user_name': session.get('name'),
        'user_role': session.get('role'),
        'username': session.get('username')
    }
    return render_template('task.html', **user_data, initial_tab='openplace')
@app.route('/api/services/<int:service_id>', methods=['GET'])
@login_required
def get_single_service(service_id):
    """Get single service details"""
    try:
        service = Service.query.get(service_id)
        if not service:
            return jsonify({'error': 'Service not found'}), 404
        
        return jsonify({
            'id': service.id,
            'name': service.name,
            'price': service.price,
            'fee': service.fee,
            'charge': service.charge,
            'service_type': service.service_type,
            'department': service.department,
            'description': service.description,
            'estimated_time': service.estimated_time,
            'status': service.status,
            'service_code': service.service_code
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/update', methods=['PUT'])
@login_required
def update_task_complete(task_id):
    """Update task with all fields (for edit mode)"""
    try:
        user = User.query.get(session['user_id'])
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check permissions - Only Admin and Manager can edit task details
        if user.post.lower() not in ['admin', 'manager']:
            return jsonify({'error': 'Access denied: Staff cannot edit task details'}), 403

        data = request.json
        
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Update basic fields
        if 'customer_name' in data:
            task.customer_name = data['customer_name']
        if 'customer_phone' in data:
            task.customer_phone = data['customer_phone']
        if 'priority' in data:
            task.priority = data['priority']
        if 'description' in data:
            task.description = data['description']
        if 'service_type' in data:
            task.service_type = data['service_type']
        
        # Update status
        if 'status' in data:
            new_status = data['status']
            if task.status != new_status:
                old_status = task.status
                task.status = new_status
                
                # Create status history
                status_history = TaskStatusHistory(
                    task_id=task.id,
                    old_status=old_status,
                    new_status=new_status,
                    reason='Status updated via Edit Task',
                    changed_by=user.username,
                    changed_at=datetime.now(timezone.utc)
                )
                db.session.add(status_history)
        
        # Update payment
        if 'paid_amount' in data:
            paid_amount = float(data['paid_amount'])
            task.paid_amount = paid_amount
            task.due_amount = max(0, (task.total_amount or 0) - paid_amount)
        
        # Handle assignment changes
        if 'in_openplace' in data:
            task.in_openplace = data['in_openplace']
            if data['in_openplace']:
                task.assigned_to_id = None
                task.assigned_to_name = None
                task.sent_to_openplace_at = datetime.now(timezone.utc)
                task.sent_by_id = user.id
                task.sent_by_name = user.username
        
        if 'assigned_to' in data and data['assigned_to']:
            # Assign to specific staff - Handle both ID (int) and username (str)
            assigned_to_value = data['assigned_to']
            staff = None
            
            if isinstance(assigned_to_value, str) and not assigned_to_value.isdigit():
                 # It's a username
                 staff = User.query.filter_by(useridname=assigned_to_value).first()
            else:
                 # It's an ID
                 staff = User.query.get(int(assigned_to_value))
            
            if staff:
                task.assigned_to_id = staff.id
                task.assigned_to_name = staff.username
                task.in_openplace = False
        
        # Handle customer type
        if 'customer_type' in data:
            task.customer_type = data['customer_type']
            if data['customer_type'] == 'online':
                if 'branch_id' in data:
                    task.branch_id = data['branch_id']
                    # Get branch name
                    branch = BranchNew.query.get(data['branch_id'])
                    if branch:
                        task.branch_name = branch.name
                if 'payment_mode' in data:
                    task.payment_mode = data['payment_mode']
                    # Handle hybrid payment
                    if data['payment_mode'] == 'hybrid':
                        task.is_hybrid = True
                        task.online_payment = float(data.get('online_payment', 0))
                        task.cash_payment = float(data.get('cash_payment', 0))
                    else:
                        task.is_hybrid = False
        
        task.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Task updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in update_task_complete: {str(e)}")
        return jsonify({'error': str(e)}), 500
@app.route('/staff/pending', endpoint='staff_pending')
@login_required
@role_required(['staff','manager','admin'])
def staff_pending_staff():
    """Staff pending tasks view"""
    user_data = {
        'user_id': session.get('user_id'),
        'user_name': session.get('name'),
        'user_role': session.get('role'),
        'username': session.get('username')
    }
    return render_template('task.html', **user_data, initial_tab='pending')

@app.route('/staff/today', endpoint='staff_today')
@login_required
@role_required(['staff','manager','admin'])
def staff_today_staff():
    """Staff today's tasks view"""
    user_data = {
        'user_id': session.get('user_id'),
        'user_name': session.get('name'),
        'user_role': session.get('role'),
        'username': session.get('username')
    }
    return render_template('task.html', **user_data, initial_tab='today')

@app.route('/staff/previous', endpoint='staff_previous')
@login_required
@role_required(['staff','manager','admin'])
def staff_previous_staff():
    """Staff previous tasks view"""
    user_data = {
        'user_id': session.get('user_id'),
        'user_name': session.get('name'),
        'user_role': session.get('role'),
        'username': session.get('username')
    }
    return render_template('task.html', **user_data, initial_tab='previous')

@app.route('/staff/total_tasks')
@login_required
@role_required(['staff','manager','admin'])
def staff_total_staff():
    """Staff total tasks view"""
    user_data = {
        'user_id': session.get('user_id'),
        'user_name': session.get('name'),
        'user_role': session.get('role'),
        'username': session.get('username')
    }
    return render_template('task.html', **user_data, initial_tab='total')

@app.route('/staff/overdue', endpoint='staff_overdue')
@login_required
@role_required(['staff','manager','admin'])
def staff_overdue():
    """Staff overdue tasks view"""
    user_data = {
        'user_id': session.get('user_id'),
        'user_name': session.get('name'),
        'user_role': session.get('role'),
        'username': session.get('username')
    }
    return render_template('overdue.html', **user_data)
# Duplicate complete_task_api removed (existing implementation kept earlier)
# ==================== MAIN ====================


# ================= REPORT API ROUTES =================

def get_date_range():
    date_from = request.args.get('date_from') or request.args.get('start_date')
    date_to = request.args.get('date_to') or request.args.get('end_date')
    
    if not date_from:
        date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')
        
    try:
        start_date = datetime.strptime(date_from, '%Y-%m-%d')
        end_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1, microseconds=-1)
        return start_date, end_date
    except ValueError:
        return datetime.now() - timedelta(days=30), datetime.now()

def apply_role_filter(query, model=Task, user_col='assigned_to_id', branch_col='branch_id'):
    user_id = session.get('user_id')
    role = session.get('role')
    user = User.query.get(user_id) if user_id else None
    
    if role == 'staff':
        if hasattr(model, user_col): return query.filter(getattr(model, user_col) == user_id)
        elif hasattr(model, 'user_id'): return query.filter(getattr(model, 'user_id') == user_id)
    elif role == 'manager':
        if user and user.branch_id and hasattr(model, branch_col):
            return query.filter(getattr(model, branch_col) == user.branch_id)
        elif user and user.branch_id and hasattr(model, 'branch_id'):
            return query.filter(getattr(model, 'branch_id') == user.branch_id)
    return query

@app.route('/api/reports/services')
@login_required
def api_report_services():
    services = Service.query.filter_by(status='active').all()
    return jsonify({
        'success': True,
        'services': [s.to_dict() for s in services]
    })

@app.route('/api/reports/branches')
@login_required
def api_report_branches():
    query = BranchNew.query.filter_by(status='active')
    if session.get('role') == 'manager':
        user = User.query.get(session.get('user_id'))
        if user and user.branch_id:
            query = query.filter(BranchNew.id == user.branch_id)
    branches = query.all()
    return jsonify({'success': True, 'branches': [b.to_dict() for b in branches]})

@app.route('/api/reports/staff-list')
@login_required
def api_report_staff_list():
    query = User.query.filter_by(is_active=True)
    role = session.get('role')
    if role == 'manager':
        user = User.query.get(session.get('user_id'))
        if user and user.branch_id: query = query.filter(User.branch_id == user.branch_id)
    elif role == 'staff':
        query = query.filter(User.id == session.get('user_id'))
    staff = query.all()
    return jsonify({'success': True, 'staff': [u.to_dict() for u in staff]})

@app.route('/api/reports/staff')
@login_required
def api_report_staff_management():
    try:
        start_date, end_date = get_date_range()
        if start_date.tzinfo: start_date = start_date.replace(tzinfo=None)
        if end_date.tzinfo: end_date = end_date.replace(tzinfo=None)
        
        branch_id = request.args.get('branch_id')
        user_query = User.query
        role = session.get('role')
        user = User.query.get(session.get('user_id'))
        
        if role == 'manager' and user and user.branch_id:
            user_query = user_query.filter(User.branch_id == user.branch_id)
        elif role == 'staff':
            user_query = user_query.filter(User.id == user.id)
            
        if branch_id and branch_id != 'all' and role == 'admin':
            user_query = user_query.filter(User.branch_id == branch_id)

        all_staff = user_query.all()
        staff_details = []
        for staff in all_staff:
            tasks = Task.query.filter(
                Task.assigned_to_id == staff.id,
                Task.created_at >= start_date,
                Task.created_at < end_date
            ).all()
            completed = len([t for t in tasks if t.status == 'completed'])
            staff_details.append({
                'id': staff.id,
                'name': staff.username,
                'department': getattr(staff, 'department', 'N/A'),
                'is_active': staff.is_active,
                'total_tasks': len(tasks),
                'completed_tasks': completed,
                'pending_tasks': len(tasks) - completed,
                'critical_tasks': 0
            })
            
        total_pending = sum(s['pending_tasks'] for s in staff_details)
        total_critical = sum(s['critical_tasks'] for s in staff_details)
        
        return jsonify({
            'success': True,
            'statistics': {
                'total_staff': len(all_staff),
                'active_staff': len([s for s in all_staff if s.is_active]),
                'inactive_staff': len([s for s in all_staff if not s.is_active]),
                'pending_tasks': total_pending,
                'critical_pending': total_critical,
                'new_joining': 0
            },
            'staff_details': staff_details,
            'staff_status': [len([s for s in all_staff if s.is_active]), len([s for s in all_staff if not s.is_active])],
            'task_distribution': [s['total_tasks'] for s in staff_details],
            'chart_labels': [s['name'] for s in staff_details]
        })
    except Exception as e:
         return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reports/branch-performance')
@login_required
def report_branch_performance():
    try:
        start_date, end_date = get_date_range()
        if start_date.tzinfo: start_date = start_date.replace(tzinfo=None)
        if end_date.tzinfo: end_date = end_date.replace(tzinfo=None)
        
        query = Task.query.filter(Task.created_at >= start_date, Task.created_at < end_date)
        query = apply_role_filter(query)
        
        branch_id = request.args.get('branch_id')
        if branch_id and branch_id != 'all' and session.get('role') == 'admin':
             query = query.filter(Task.branch_id == branch_id)
             
        tasks = query.all()
        branch_stats = {}
        branch_ranking_data = {}

        for t in tasks:
            # Stats for charts
            b_name = t.branch_name or (t.branch.name if t.branch else 'Unknown')
            if b_name not in branch_stats: branch_stats[b_name] = {'revenue': 0, 'tasks': 0}
            branch_stats[b_name]['revenue'] += (t.total_amount or 0)
            branch_stats[b_name]['tasks'] += 1
            
            # Data for ranking
            b_id = t.branch_id or 'unknown'
            if b_id not in branch_ranking_data:
                branch_ranking_data[b_id] = {
                    'name': b_name,
                    'code': t.branch.code if t.branch else 'N/A',
                    'total_tasks': 0,
                    'completed_tasks': 0,
                    'revenue': 0,
                    'rating': 0 # Placeholder as Task has no rating
                }
            
            branch_ranking_data[b_id]['total_tasks'] += 1
            branch_ranking_data[b_id]['revenue'] += (t.total_amount or 0)
            if t.status == 'completed':
                branch_ranking_data[b_id]['completed_tasks'] += 1

        # Calculate efficiency and format ranking
        ranking = []
        for b_data in branch_ranking_data.values():
            efficiency = (b_data['completed_tasks'] / b_data['total_tasks'] * 100) if b_data['total_tasks'] > 0 else 0
            ranking.append({
                'name': b_data['name'],
                'code': b_data['code'],
                'total_tasks': b_data['total_tasks'],
                'completed_tasks': b_data['completed_tasks'],
                'revenue': b_data['revenue'],
                'efficiency': round(efficiency, 1),
                'rating': 5.0 # Default rating
            })
            
        # Sort by revenue desc
        ranking.sort(key=lambda x: x['revenue'], reverse=True)

        # Calculate Service Distribution
        service_counts = {}
        for t in tasks:
            s_type = t.service_name or 'Normal' # Or use t.service_type if available and reliable
            # To make it cleaner, maybe group by actual service type if available
            if hasattr(t, 'service') and t.service:
                 s_type = t.service.service_type or 'Normal'
            elif hasattr(t, 'service_type') and t.service_type:
                 s_type = t.service_type
            
            # Capitalize first letter
            s_type = s_type.title()
            service_counts[s_type] = service_counts.get(s_type, 0) + 1

        return jsonify({
            'success': True,
            'ranking': ranking,
            'performance': {
                'labels': list(branch_stats.keys()),
                'revenue': [s['revenue'] for s in branch_stats.values()],
                'tasks': [s['tasks'] for s in branch_stats.values()]
            },
            'service_distribution': {
                'labels': list(service_counts.keys()),
                'data': list(service_counts.values())
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reports/staff-performance')
@login_required
def report_staff_performance():
    try:
        start_date, end_date = get_date_range()
        if start_date.tzinfo: start_date = start_date.replace(tzinfo=None)
        if end_date.tzinfo: end_date = end_date.replace(tzinfo=None)
        
        query = Task.query.filter(Task.created_at >= start_date, Task.created_at < end_date)
        query = apply_role_filter(query)
        
        staff_id = request.args.get('staff_id')
        if staff_id and staff_id != 'all': query = query.filter(Task.assigned_to_id == staff_id)
        
        tasks = query.all()
        task_details = []
        for t in tasks:
            # Calculate correct revenue based on payment mode:
            # - Regular payment (cash/upi/card): Company collects full service_price (includes govt fee)
            # - Self-pay: Company only collects service_fee (govt fee), customer pays provider directly
            if t.is_self_pay:
                revenue = float(t.service_fee or 0)
            else:
                revenue = float(t.service_price or t.total_amount or 0)
            
            task_details.append({
                'id': t.id,
                'name': t.service_name or 'Unknown',
                'service_type': t.service_name or 'Normal',
                'assigned_date': t.created_at.strftime('%Y-%m-%d') if t.created_at else None,
                'completed_date': t.completed_at.strftime('%Y-%m-%d') if t.completed_at else None,
                'status': t.status,
                'rating': 0, 
                'revenue': revenue
            })

        completed = [t for t in tasks if t.status == 'completed']
        times = [(t.completed_at - t.created_at).total_seconds() / 3600 for t in completed if t.completed_at and t.created_at]
        status_counts = {}
        for t in tasks: status_counts[t.status] = status_counts.get(t.status, 0) + 1
        breakdown = [{'status': s, 'count': c, 'percentage': (c/len(tasks)*100) if tasks else 0} for s, c in status_counts.items()]
        
        # Calculate total revenue correctly
        total_revenue = 0
        for t in tasks:
            if t.is_self_pay:
                total_revenue += float(t.service_fee or 0)
            else:
                total_revenue += float(t.service_price or t.total_amount or 0)
        
        # Calculate Trend Data (Last 7 days or selected range)
        trend_data = {'dates': [], 'completed': [], 'pending': []}
        curr = start_date
        while curr < end_date:
            d_str = curr.strftime('%b %d')
            nxt = curr + timedelta(days=1)
            day_tasks = [t for t in tasks if t.created_at and curr <= t.created_at.replace(tzinfo=None) < nxt.replace(tzinfo=None)]
            
            trend_data['dates'].append(d_str)
            trend_data['completed'].append(len([t for t in day_tasks if t.status == 'completed']))
            trend_data['pending'].append(len([t for t in day_tasks if t.status in ['pending', 'in_progress']]))
            curr = nxt

        # Calculate Today's Data
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_tasks = [t for t in tasks if t.created_at and t.created_at.replace(tzinfo=None) >= today_start]
        t_completed = len([t for t in today_tasks if t.status == 'completed'])
        t_pending = len([t for t in today_tasks if t.status == 'pending'])
        t_progress = len([t for t in today_tasks if t.status == 'in_progress'])
        t_cancelled = len([t for t in today_tasks if t.status == 'cancelled'])
        
        return jsonify({
            'success': True,
            'task_details': task_details,
            'metrics': {
                'avg_completion_time': round(sum(times)/len(times) if times else 0, 1),
                'completion_rate': round(len(completed)*100/len(tasks) if tasks else 0, 1),
                'avg_tasks_per_day': round(len(tasks)/7 if (end_date - start_date).days < 7 else len(tasks)/((end_date - start_date).days or 1), 1),
                'avg_revenue': round(total_revenue/len(tasks) if tasks else 0, 1)
            },
            'breakdown': breakdown,
            'today_data': [t_completed, t_pending, t_progress, t_cancelled],
            'trend_data': trend_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reports/attendance')
@login_required
def report_attendance():
    try:
        start_date, end_date = get_date_range()
        if start_date.tzinfo: start_date = start_date.replace(tzinfo=None)
        if end_date.tzinfo: end_date = end_date.replace(tzinfo=None)
        
        query = Attendance.query.filter(Attendance.check_in.between(start_date, end_date))
        role = session.get('role')
        user = User.query.get(session.get('user_id'))
        
        if role == 'staff': query = query.filter(Attendance.user_id == user.id)
        elif role == 'manager' and user and user.branch_id: query = query.filter(Attendance.branch_id == user.branch_id)
        
        branch_id = request.args.get('branch_id')
        if branch_id and branch_id != 'all' and role == 'admin':
            query = query.filter(Attendance.branch_id == branch_id)
            
        records = query.all()
        today = datetime.now().date()
        today_records = [r for r in records if r.check_in.date() == today]
        present_today = len([r for r in today_records if r.status == 'checked_in'])
        total_hours = sum(r.total_hours for r in records if r.total_hours)
        avg_hours = total_hours / len(records) if records else 0
        
        # New aggregate metrics for manager settlement
        total_online_cash = sum(r.online_cash for r in records if r.online_cash)
        total_extra_amount = sum(r.extra_amount for r in records if r.extra_amount)
        
        # Calculate daily aggregate data
        daily_agg = {}
        for r in records:
            if not r.check_in: continue
            
            d_str = r.check_in.date().isoformat()
            if d_str not in daily_agg:
                daily_agg[d_str] = {
                    'date': d_str, 
                    'present': 0, 
                    'absent': 0, 
                    'late': 0, 
                    'avg_hours': 0, 
                    'total_h': 0, 
                    'count': 0,
                    'online_cash': 0,
                    'extra_amount': 0
                }
            
            daily_agg[d_str]['count'] += 1
            if r.status == 'checked_in':
                daily_agg[d_str]['present'] += 1
            
            if r.status == 'late': 
                daily_agg[d_str]['late'] += 1
                
            if r.total_hours:
                daily_agg[d_str]['total_h'] += float(r.total_hours)
            
            if r.online_cash:
                daily_agg[d_str]['online_cash'] += float(r.online_cash)
            if r.extra_amount:
                daily_agg[d_str]['extra_amount'] += float(r.extra_amount)
        
        for d in daily_agg.values():
            if d['count'] > 0:
                d['avg_hours'] = round(d['total_h'] / d['count'], 1)
        
        daily_data = sorted(daily_agg.values(), key=lambda x: x['date'], reverse=True)

        return jsonify({
            'success': True,
            'today': {'present': present_today, 'absent': 0, 'late': 0},
            'average_hours': round(avg_hours, 1),
            'total_online_cash': total_online_cash,
            'total_extra_amount': total_extra_amount,
            'daily_data': daily_data,
            'daily_details': [r.to_dict() for r in records]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/staff/<int:staff_id>/toggle', methods=['POST'])
@login_required
def toggle_staff_status_api(staff_id):
    staff = User.query.get(staff_id)
    if staff:
        staff.is_active = not staff.is_active
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Staff not found'})

# ================= PROFIT REPORT ENDPOINT =================
@app.route('/api/reports/profit', methods=['GET'])
@login_required
@role_required(['admin', 'manager', 'staff'])
def get_profit_report():
    """Get profit report with expenses calculation"""
    try:
        user = User.query.get(session['user_id'])
        user_role = session.get('role', '').lower()
        
        # Get filter parameters
        branch_id = request.args.get('branch_id')
        service_id = request.args.get('service_id')
        staff_id = request.args.get('staff_id')
        
        # Get date range using helper
        start_dt, end_dt = get_date_range()
        
        # RESTRICTION: Staff can only see "Today"
        if user_role == 'staff':
            # Override date range to today only (naive local time for comparison)
            now = datetime.now()
            start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_dt = start_dt + timedelta(days=1)
            print(f"Restricting staff {user.useridname} to today only: {start_dt} to {end_dt}")
            
            # Staff can only see their own tasks
            staff_id = user.id
        if start_dt.tzinfo: start_dt = start_dt.replace(tzinfo=None)
        if end_dt.tzinfo: end_dt = end_dt.replace(tzinfo=None)
        
        # Build query
        query = Task.query.filter(
            Task.status == 'completed',
            Task.created_at >= start_dt,
            Task.created_at < end_dt
        )
        
        # Apply role/branch filtering
        if user.post.lower() == 'manager' and user.branch_id:
            query = query.filter(Task.branch_id == user.branch_id)
        elif branch_id and branch_id != 'all':
            try:
                query = query.filter(Task.branch_id == int(branch_id))
            except ValueError:
                pass
                
        if service_id and service_id != 'all':
            try:
                query = query.filter(Task.service_id == int(service_id))
            except ValueError:
                pass
                
        if staff_id and staff_id != 'all':
            try:
                query = query.filter(Task.assigned_to_id == int(staff_id))
            except ValueError:
                pass
                
        tasks = query.all()
        
        # Revenue = what company actually receives. Net Profit = Revenue - Govt Fees.
        # Correct Logic:
        # Regular Payment: Revenue = paid_amount, Fees = service_fee, Profit = revenue - fees
        # Self-Pay: Company only gets service_charge (customer pays govt directly). If due > 0,
        #   we only "take" (service_charge - due_amount) as revenue/profit.
        total_revenue = 0  # Total money company actually receives
        net_profit = 0    # What company keeps (revenue - fees)
        total_fees = 0      # Government fees to be paid
        
        for t in tasks:
            # Include offer/due tasks – revenue = what we actually received
            if t.is_self_pay:
                # Self-pay: we collect service_charge; any due is from our share, so we only "take" (charge - due)
                t_revenue = max(0, float(t.service_charge or 0) - float(t.due_amount or 0))
                t_govt_fee = 0  # Customer pays govt fees directly
                t_profit = t_revenue
            else:
                # Regular: revenue = paid_amount (actual collected); profit = revenue - govt fees
                t_revenue = float(t.paid_amount or 0)
                t_govt_fee = float(t.service_fee or 0)
                t_profit = t_revenue - t_govt_fee
            
            total_revenue += t_revenue
            net_profit += t_profit
            total_fees += t_govt_fee
        
        profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0
        
        # Build branch breakdown (same revenue/profit logic as above)
        branches = {}
        for t in tasks:
            b_name = t.branch_name or (t.branch.name if t.branch else 'Unknown Branch')
            if b_name not in branches:
                branches[b_name] = {'revenue': 0, 'fees': 0, 'tasks': 0, 'profit': 0}
            if t.is_self_pay:
                t_revenue = max(0, float(t.service_charge or 0) - float(t.due_amount or 0))
                t_govt_fee = 0
                t_profit = t_revenue
            else:
                t_revenue = float(t.paid_amount or 0)
                t_govt_fee = float(t.service_fee or 0)
                t_profit = t_revenue - t_govt_fee
            branches[b_name]['revenue'] += t_revenue
            branches[b_name]['fees'] += t_govt_fee
            branches[b_name]['profit'] += t_profit
            branches[b_name]['tasks'] += 1
            
        breakdown = []
        for name, stats in branches.items():
            profit = stats['profit']
            margin = (profit / stats['revenue'] * 100) if stats['revenue'] > 0 else 0
            breakdown.append({
                'branch': name,
                'revenue': round(stats['revenue'], 2),
                'fees': round(stats['fees'], 2),
                'profit': round(profit, 2),
                'margin': round(margin, 1),
                'tasks': stats['tasks']
            })
            
        # Build profit trend
        profit_trend = {'dates': [], 'profit': [], 'fees': []}
        curr = start_dt
        while curr < end_dt:
            d_str = curr.strftime('%b %d')
            # Filter tasks for this day
            d_tasks = [t for t in tasks if t.created_at.date() == curr.date()]
            
            d_rev = 0
            d_profit = 0
            d_cost = 0
            
            for t in d_tasks:
                if t.is_self_pay:
                    tr = max(0, float(t.service_charge or 0) - float(t.due_amount or 0))
                    tc = 0
                    tp = tr
                else:
                    tr = float(t.paid_amount or 0)
                    tc = float(t.service_fee or 0)
                    tp = tr - tc
                d_rev += tr
                d_profit += tp
                d_cost += tc
            
            profit_trend['dates'].append(d_str)
            profit_trend['profit'].append(round(d_profit, 2))
            profit_trend['fees'].append(round(d_cost, 2))
            curr += timedelta(days=1)

        # Build profit distribution (by branch)
        profit_distribution = {name: round(stats['profit'], 2) for name, stats in branches.items()}

        return jsonify({
            'success': True,
            'statistics': {
                'total_revenue': round(total_revenue, 2),
                'total_fees': round(total_fees, 2),
                'net_profit': round(net_profit, 2),
                'profit_margin': round(profit_margin, 1)
            },
            'branch_breakdown': breakdown,
            'profit_trend': profit_trend,
            'profit_distribution': profit_distribution
        })
    except Exception as e:
        print(f"Error in get_profit_report: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reports/due-report', methods=['GET'])
@login_required
def get_due_report():
    """Get due report for tasks with outstanding due amounts; optional status filter."""
    try:
        # Get filter parameters
        staff_id = request.args.get('staff_id', 'all')
        service_id = request.args.get('service_id', 'all')
        branch_id = request.args.get('branch_id', 'all')
        status_filter = request.args.get('status', 'completed')  # default: completed; 'all' = any status
        date_from = request.args.get('date_from') or request.args.get('start_date', '')
        date_to = request.args.get('date_to') or request.args.get('end_date', '')
        
        # Get date range using helper
        start_date, end_date = get_date_range()
        
        # Remove timezone info if present to avoid comparison issues
        if start_date.tzinfo:
            start_date = start_date.replace(tzinfo=None)
        if end_date.tzinfo:
            end_date = end_date.replace(tzinfo=None)
        
        # Base query: tasks with due amounts > 0
        query = Task.query.filter(Task.due_amount > 0)
        
        # Status filter: completed (default), or specific status, or all
        if status_filter and status_filter != 'all':
            query = query.filter(Task.status == status_filter)
        
        # Date filter: use completed_at for completed, updated_at for others
        if status_filter == 'completed':
            query = query.filter(
                Task.completed_at >= start_date,
                Task.completed_at <= end_date
            )
        else:
            query = query.filter(
                Task.updated_at >= start_date,
                Task.updated_at <= end_date
            )
        
        # Apply branch filter
        if branch_id and branch_id != 'all':
            try:
                query = query.filter(Task.branch_id == int(branch_id))
            except ValueError:
                pass
        
        # Apply staff filter
        if staff_id and staff_id != 'all':
            try:
                query = query.filter(Task.assigned_to_id == int(staff_id))
            except ValueError:
                pass
        
        # Apply service filter
        if service_id and service_id != 'all':
            try:
                query = query.filter(Task.service_id == int(service_id))
            except ValueError:
                pass
        
        # Get all matching tasks (order by completed_at for completed, else updated_at)
        if status_filter == 'completed':
            query = query.order_by(Task.completed_at.desc())
        else:
            query = query.order_by(Task.updated_at.desc())
        tasks = query.all()
        
        # Calculate statistics
        total_due_amount = sum(float(t.due_amount or 0) for t in tasks)
        total_tasks_with_due = len(tasks)
        
        def due_reason_type_from_offer_reason(offer_reason):
            if not offer_reason:
                return ''
            r = (offer_reason or '').strip()
            if r.startswith('Offer/Discount'):
                return 'Offer/Discount'
            if r.startswith('Payment Plan'):
                return 'Payment Plan'
            if r.startswith('Other'):
                return 'Other'
            return ''

        # Build task list
        task_list = []
        for task in tasks:
            # Prefer offer_reason (set when completing with due + reason type), else completion_notes
            due_reason = task.offer_reason or task.completion_notes or task.description or 'No reason specified'
            due_reason_type = due_reason_type_from_offer_reason(task.offer_reason)
            task_list.append({
                'order_no': task.order_no,
                'customer_name': task.customer_name,
                'customer_phone': task.customer_phone,
                'service_name': task.service_name,
                'assigned_to_name': task.assigned_to_name or 'Unassigned',
                'due_amount': float(task.due_amount or 0),
                'total_amount': float(task.total_amount or 0),
                'paid_amount': float(task.paid_amount or 0),
                'due_reason': due_reason,
                'due_reason_type': due_reason_type,
                'offer_amount': float(task.offer_amount or 0),
                'status': task.status or 'completed',
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'payment_mode': task.payment_mode or 'Not specified'
            })
        
        return jsonify({
            'success': True,
            'statistics': {
                'total_due_amount': round(total_due_amount, 2),
                'total_tasks_with_due': total_tasks_with_due,
                'average_due_amount': round(total_due_amount / total_tasks_with_due, 2) if total_tasks_with_due > 0 else 0
            },
            'tasks': task_list,
            'filters': {
                'staff_id': staff_id,
                'service_id': service_id,
                'branch_id': branch_id,
                'status': status_filter,
                'date_from': date_from,
                'date_to': date_to
            }
        })
        
    except Exception as e:
        print(f"Error in get_due_report: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== ATTENDANCE API ROUTES ====================

@app.route('/api/attendance/checkin', methods=['POST'])
@login_required
def attendance_checkin():
    """Staff check-in with branch selection"""
    try:
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.json
        branch_name = data.get('branch')
        branch_id = data.get('branch_id')
        
        if not branch_id:
            return jsonify({'error': 'Branch selection is required'}), 400
        
        # Find the branch
        branch = BranchNew.query.get(branch_id)
        if not branch:
            return jsonify({'error': 'Branch not found'}), 404
        
        # Check if already checked in today
        today = datetime.now(timezone.utc).date()
        existing_checkin = Attendance.query.filter(
            Attendance.user_id == user.id,
            db.func.date(Attendance.check_in) == today,
            Attendance.status == 'checked_in'
        ).first()
        
        if existing_checkin:
            return jsonify({'error': 'You have already checked in today'}), 400
        
        # Update user's branch_id in the User model
        user.branch_id = branch.id
        
        # Create attendance record
        attendance = Attendance(
            user_id=user.id,
            branch_id=branch.id,
            branch_name=branch.name,
            check_in=datetime.now(timezone.utc),
            status='checked_in'
        )
        
        db.session.add(attendance)
        db.session.commit()
        
        # Store branch information in session for immediate use
        session['branch_id'] = branch.id
        session['branch_name'] = branch.name
        session['branch_code'] = branch.code
        session['branch'] = branch.name  # For backward compatibility
        
        return jsonify({
            'success': True,
            'message': 'Checked in successfully',
            'branch': {
                'id': branch.id,
                'name': branch.name,
                'code': branch.code
            },
            'check_in_time': attendance.check_in.isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in attendance_checkin: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/attendance/checkout', methods=['POST'])
@login_required
def attendance_checkout():
    """Staff check-out"""
    try:
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Find today's check-in record
        today = datetime.now(timezone.utc).date()
        attendance = Attendance.query.filter(
            Attendance.user_id == user.id,
            db.func.date(Attendance.check_in) == today,
            Attendance.status == 'checked_in'
        ).first()
        
        if not attendance:
            return jsonify({'error': 'No check-in record found for today'}), 404
        
        data = request.json or {}
        online_cash = data.get('online_cash', 0.0)
        extra_amount = data.get('extra_amount', 0.0)
        pending_tasks = data.get('pending_tasks', []) # List of {task_id, reason}
        
        # Update check-out time
        checkout_time = datetime.now(timezone.utc)
        attendance.check_out = checkout_time
        attendance.status = 'checked_out'
        attendance.online_cash = online_cash
        attendance.extra_amount = extra_amount
        
        # Calculate total hours
        if attendance.check_in:
            time_diff = checkout_time - attendance.check_in
            attendance.total_hours = time_diff.total_seconds() / 3600
        
        # Save pending task reasons
        for item in pending_tasks:
            task_id = item.get('task_id')
            reason = item.get('reason')
            if task_id and reason:
                ptr = PendingTaskReason(
                    attendance_id=attendance.id,
                    task_id=task_id,
                    reason=reason
                )
                db.session.add(ptr)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Checked out successfully',
            'check_out_time': checkout_time.isoformat(),
            'total_hours': round(attendance.total_hours, 2) if attendance.total_hours else 0,
            'online_cash': attendance.online_cash,
            'extra_amount': attendance.extra_amount
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in attendance_checkout: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/staff/pending-tasks', methods=['GET'])
@login_required
def get_staff_pending_tasks():
    """Get all non-completed/non-cancelled tasks assigned to current user"""
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        # Filter for tasks assigned to this user that are not completed/cancelled
        # Note: We use the username for assignment check based on how this CRM seems to handle it
        pending_tasks = Task.query.filter(
            (Task.assigned_to == user.username) | (Task.assigned_to == str(user.id)),
            ~Task.status.in_(['Completed', 'Cancelled'])
        ).all()
        
        return jsonify({
            'success': True,
            'tasks': [task.to_dict() for task in pending_tasks]
        })
    except Exception as e:
        print(f"Error in get_staff_pending_tasks: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/attendance/today', methods=['GET'])
@login_required
def attendance_today():
    """Get today's attendance status for current user - returns flat format for frontend"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not in session'}), 401
            
        today = datetime.now(timezone.utc).date()
        
        # 1. Prefer an active check-in
        attendance = Attendance.query.filter(
            Attendance.user_id == user_id,
            db.func.date(Attendance.check_in) == today,
            Attendance.status == 'checked_in'
        ).first()
        
        # 2. If no active check-in, get most recent record of today
        if not attendance:
            attendance = Attendance.query.filter(
                Attendance.user_id == user_id,
                db.func.date(Attendance.check_in) == today
            ).order_by(Attendance.check_in.desc()).first()
            
        if not attendance:
            return jsonify(None)
            
        # Get branch information
        branch = BranchNew.query.get(attendance.branch_id) if attendance.branch_id else None
        
        # Prepare flat response structure expected by staffchecking.html
        response_data = {
            'id': attendance.id,
            'check_in': attendance.check_in.isoformat() if attendance.check_in else None,
            'check_out': attendance.check_out.isoformat() if attendance.check_out else None,
            'status': attendance.status,
            'total_hours': round(attendance.total_hours, 2) if attendance.total_hours else 0,
            'branch_id': attendance.branch_id,
            'branch_name': attendance.branch_name or (branch.name if branch else None),
            'branch_code': branch.code if branch else None
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in attendance_today: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/attendance/history', methods=['GET'])
@login_required
def get_attendance_history():
    """Get attendance history"""
    try:
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get filter parameters
        staff_id = request.args.get('staff_id')
        status = request.args.get('status')
        limit = int(request.args.get('limit', 30))
        
        # Build query
        query = Attendance.query
        
        # Role-based filtering
        user_role = session.get('role', '').lower()
        if user_role == 'staff':
            # Staff can only see their own records
            query = query.filter(Attendance.user_id == user.id)
        elif user_role == 'manager' and user.branch_id:
            # Managers see records from their branch
            query = query.filter(Attendance.branch_id == user.branch_id)
        elif user_role == 'admin':
            # Admin can filter by staff_id if provided
            if staff_id and staff_id != 'all':
                try:
                    query = query.filter(Attendance.user_id == int(staff_id))
                except ValueError:
                    pass
        
        # Status filter
        if status and status != 'all':
            query = query.filter(Attendance.status == status)
        
        # Get records
        records = query.order_by(Attendance.check_in.desc()).limit(limit).all()
        
        # Format response
        attendance_list = []
        for record in records:
            staff_user = User.query.get(record.user_id)
            branch = BranchNew.query.get(record.branch_id) if record.branch_id else None
            
            attendance_list.append({
                'id': record.id,
                'user_id': record.user_id,
                'user_name': staff_user.username if staff_user else 'Unknown',
                'branch': {
                    'id': branch.id,
                    'name': branch.name,
                    'code': branch.code
                } if branch else None,
                'check_in': record.check_in.isoformat() if record.check_in else None,
                'check_out': record.check_out.isoformat() if record.check_out else None,
                'status': record.status,
                'total_hours': round(record.total_hours, 2) if record.total_hours else 0
            })
        
        return jsonify({
            'success': True,
            'attendance': attendance_list,
            'total': len(attendance_list)
        })
        
    except Exception as e:
        print(f"Error in attendance_history: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    with app.app_context():
        initialize_database()
    print("Server starting on http://0.0.0.0:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
