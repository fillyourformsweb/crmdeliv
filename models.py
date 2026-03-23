from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='staff')  # admin, manager, staff, delivery
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=True)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # OTP for Password Reset
    otp_code = db.Column(db.String(6))
    otp_expiry = db.Column(db.DateTime)
    
    branch = db.relationship('Branch', back_populates='users')
    orders = db.relationship('Order', back_populates='created_by_user', foreign_keys='Order.created_by')
    assigned_deliveries = db.relationship('Order', back_populates='delivery_person', foreign_keys='Order.delivery_person_id')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Branch(db.Model):
    __tablename__ = 'branches'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    address = db.Column(db.String(300))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    users = db.relationship('User', back_populates='branch')
    orders = db.relationship('Order', back_populates='branch')


class Client(db.Model):
    __tablename__ = 'clients'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    company_name = db.Column(db.String(150))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(300))
    landmark = db.Column(db.String(150))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pincode = db.Column(db.String(10))
    alt_address = db.Column(db.String(300))
    alt_landmark = db.Column(db.String(150))
    alt_phone = db.Column(db.String(20))
    alt_email = db.Column(db.String(120))
    gst_number = db.Column(db.String(50))
    billing_pattern_id = db.Column(db.Integer, db.ForeignKey('billing_patterns.id'))
    bill_pattern = db.Column(db.String(100))
    billing_date = db.Column(db.Integer)  # Day of month (1-31)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    billing_pattern = db.relationship('BillingPattern', back_populates='clients')
    orders = db.relationship('Order', back_populates='client')
    receivers = db.relationship('Receiver', back_populates='client', cascade='all, delete-orphan')
    addresses = db.relationship('ClientAddress', back_populates='client', cascade='all, delete-orphan')


class Receiver(db.Model):
    __tablename__ = 'receivers'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    company_name = db.Column(db.String(150))
    phone = db.Column(db.String(20), nullable=False)
    alt_phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    alt_email = db.Column(db.String(120))
    address = db.Column(db.String(300))
    landmark = db.Column(db.String(150))
    alt_address = db.Column(db.String(300))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pincode = db.Column(db.String(10))
    gst_number = db.Column(db.String(50))
    bill_pattern = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    client = db.relationship('Client', back_populates='receivers')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'company_name': self.company_name,
            'phone': self.phone,
            'alt_phone': self.alt_phone,
            'email': self.email,
            'alt_email': self.alt_email,
            'address': self.address,
            'alt_address': self.alt_address,
            'city': self.city,
            'state': self.state,
            'pincode': self.pincode,
            'landmark': self.landmark,
            'gst_number': self.gst_number,
            'bill_pattern': self.bill_pattern
        }


class ClientAddress(db.Model):
    __tablename__ = 'client_addresses'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    address_label = db.Column(db.String(50), default='Primary')
    address = db.Column(db.String(300), nullable=False)
    landmark = db.Column(db.String(150))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pincode = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    client = db.relationship('Client', back_populates='addresses')

    def to_dict(self):
        return {
            'id': self.id,
            'address_label': self.address_label,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'pincode': self.pincode,
            'landmark': self.landmark
        }


class ReceiptSetting(db.Model):
    __tablename__ = 'receipt_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    base_number = db.Column(db.String(50), nullable=False, default='100371900086')
    range_end = db.Column(db.String(50), nullable=True)
    current_sequence = db.Column(db.Integer, default=0)
    prefix = db.Column(db.String(20))
    suffix = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))

class StaffReceiptAssignment(db.Model):
    __tablename__ = 'staff_receipt_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    prefix = db.Column(db.String(20))
    base_number = db.Column(db.String(50), nullable=False)
    range_end = db.Column(db.String(50), nullable=True) # New field for range
    current_sequence = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    user = db.relationship('User', foreign_keys=[user_id], backref='receipt_assignments')
    branch = db.relationship('Branch')
    admin = db.relationship('User', foreign_keys=[assigned_by])


class BillingPattern(db.Model):
    __tablename__ = 'billing_patterns'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    pattern_type = db.Column(db.String(20), nullable=False)  # 10, 15, 30
    base_rate = db.Column(db.Float, nullable=False)
    rate_per_kg = db.Column(db.Float, nullable=False)
    min_weight = db.Column(db.Float, default=0.5)
    max_weight = db.Column(db.Float)
    additional_charges = db.Column(db.Float, default=0)
    discount_percentage = db.Column(db.Float, default=0)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    clients = db.relationship('Client', back_populates='billing_pattern')


class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    receipt_number = db.Column(db.String(50), unique=True, nullable=False)
    receipt_type = db.Column(db.String(20), default='standard') # standard, manual
    assignment_id = db.Column(db.Integer, db.ForeignKey('staff_receipt_assignments.id'), nullable=True)
    order_type = db.Column(db.String(20), nullable=False)  # client, walkin
    receipt_mode = db.Column(db.String(30))  # standard, prime, parcel, state_express, road_express
    
    # Customer Details
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    customer_email = db.Column(db.String(120))
    customer_address = db.Column(db.String(300))
    customer_landmark = db.Column(db.String(150))
    customer_city = db.Column(db.String(100))
    customer_state = db.Column(db.String(100))
    customer_pincode = db.Column(db.String(10))
    
    # Receiver Details
    receiver_name = db.Column(db.String(100))
    receiver_phone = db.Column(db.String(20))
    receiver_address = db.Column(db.String(300))
    receiver_city = db.Column(db.String(100))
    receiver_state = db.Column(db.String(100))
    receiver_pincode = db.Column(db.String(10))
    receiver_landmark = db.Column(db.String(150))
    
    # Package Details
    package_description = db.Column(db.Text)
    weight = db.Column(db.Float)
    weight_category = db.Column(db.String(50))
    weight_in_kg = db.Column(db.Float)
    dimensions = db.Column(db.String(50))
    number_of_boxes = db.Column(db.Integer, default=1)
    
    # Pricing
    price_list_type = db.Column(db.String(50), default='default')  # default, normal_client, price_master
    base_amount = db.Column(db.Float, default=0)
    weight_charges = db.Column(db.Float, default=0)
    additional_charges = db.Column(db.Float, default=0)
    discount = db.Column(db.Float, default=0)
    tax_amount = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, default=0)
    insured_amount = db.Column(db.Float, default=0)  # Declared value for insurance
    insurance_charge = db.Column(db.Float, default=0)  # Calculated insurance charge
    calculated_amount = db.Column(db.Float, default=0)
    received_amount = db.Column(db.Float, default=0)
    amount_difference = db.Column(db.Float, default=0)
    difference_reason = db.Column(db.String(200))
    
    # Status
    status = db.Column(db.String(30), default='at_destination')  # at_destination, confirmed, in_transit, delivered, cancelled
    payment_status = db.Column(db.String(20), default='unpaid')  # unpaid, partial, paid
    payment_mode = db.Column(db.String(20))  # cash, card, upi, credit
    
    # International Booking Fields
    is_international = db.Column(db.Boolean, default=False)
    destination_country = db.Column(db.String(100))
    hs_code = db.Column(db.String(50))
    customs_description = db.Column(db.Text)
    product_value_usd = db.Column(db.Float)
    invoice_currency = db.Column(db.String(10), default='USD')
    international_notes = db.Column(db.Text)
    requires_signature_intl = db.Column(db.Boolean, default=False)
    
    # Extra Tracking Info
    order_number = db.Column(db.String(50))
    order_date = db.Column(db.String(20))
    consignment_number = db.Column(db.String(50))
    
    # Tracking
    tracking_link = db.Column(db.String(100), unique=True)
    customer_form_link = db.Column(db.String(100), unique=True)
    customer_form_completed = db.Column(db.Boolean, default=False)
    
    # Additional Info
    special_instructions = db.Column(db.Text)
    internal_notes = db.Column(db.Text)
    handling_tags = db.Column(db.Text)  # Comma-separated handling tags (FRAGILE, HANDLE WITH CARE, etc.)
    
    # Foreign Keys
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'))
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    delivery_person_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    billing_pattern_id = db.Column(db.Integer, db.ForeignKey('billing_patterns.id'))
    sender_address_id = db.Column(db.Integer, db.ForeignKey('client_addresses.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('receivers.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    delivered_at = db.Column(db.DateTime)
    
    # Reschedule/Pickup Management
    reschedule_reason = db.Column(db.String(200))
    reschedule_requested_date = db.Column(db.DateTime)
    reschedule_status = db.Column(db.String(50))  # pending, scheduled, cancelled
    pickup_attempts = db.Column(db.Integer, default=0)
    last_pickup_attempt = db.Column(db.DateTime)
    
    # Excel verification
    excel_verified = db.Column(db.Boolean, default=False)
    excel_weight = db.Column(db.Float)
    excel_amount = db.Column(db.Float)
    
    # Mobile app verification
    verified = db.Column(db.Boolean, default=True)  # Default True for web orders, False for mobile
    created_via = db.Column(db.String(20), default='web')  # 'web' or 'mobile'
    
    # Relationships
    client = db.relationship('Client', back_populates='orders')
    branch = db.relationship('Branch', back_populates='orders')
    created_by_user = db.relationship('User', back_populates='orders', foreign_keys=[created_by])
    delivery_person = db.relationship('User', back_populates='assigned_deliveries', foreign_keys=[delivery_person_id])
    tracking_updates = db.relationship('TrackingUpdate', back_populates='order', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', back_populates='order', cascade='all, delete-orphan')
    sender_address = db.relationship('ClientAddress')
    receiver_saved = db.relationship('Receiver')
    
    def generate_tracking_link(self):
        self.tracking_link = secrets.token_urlsafe(16)
        return self.tracking_link
    
    def generate_customer_form_link(self):
        self.customer_form_link = secrets.token_urlsafe(16)
        return self.customer_form_link


class TrackingUpdate(db.Model):
    __tablename__ = 'tracking_updates'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(200))
    description = db.Column(db.Text)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    order = db.relationship('Order', back_populates='tracking_updates')


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    message = db.Column(db.String(500), nullable=False)
    notification_type = db.Column(db.String(50))  # 'new_order', 'order_verified', 'status_update'
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='notifications')
    order = db.relationship('Order', back_populates='notifications')


class ExcelUpload(db.Model):
    __tablename__ = 'excel_uploads'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    records_processed = db.Column(db.Integer, default=0)
    records_matched = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ExcelData(db.Model):
    __tablename__ = 'excel_data'
    
    id = db.Column(db.Integer, primary_key=True)
    receipt_number = db.Column(db.String(50), nullable=False)
    weight = db.Column(db.Float)
    amount = db.Column(db.Float)
    additional_info = db.Column(db.Text)
    upload_id = db.Column(db.Integer, db.ForeignKey('excel_uploads.id'))
    matched = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class DefaultStatePrice(db.Model):
    __tablename__ = 'default_state_prices'
    
    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.String(100), nullable=False)
    shipping_mode = db.Column(db.String(50), default='standard', nullable=False)  # standard, prime, parcel, state_express, road_express, air
    price_100gm = db.Column(db.Float, default=0)
    price_250gm = db.Column(db.Float, default=0)
    price_500gm = db.Column(db.Float, default=0)
    price_1kg = db.Column(db.Float, default=0)
    price_2kg = db.Column(db.Float, default=0)
    price_3kg = db.Column(db.Float, default=0)
    price_extra_per_kg = db.Column(db.Float, default=20)  # Rate per kg for weight > 3kg
    # Air cargo pricing (> 3kg tiers)
    price_3_10kg = db.Column(db.Float, default=0)  # 3-10 kg tier
    price_10_25kg = db.Column(db.Float, default=0)  # 10-25 kg tier
    price_25_50kg = db.Column(db.Float, default=0)  # 25-50 kg tier
    price_50_100kg = db.Column(db.Float, default=0)  # 50-100 kg tier
    price_100plus_kg = db.Column(db.Float, default=0)  # 100+ kg tier
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('state', 'shipping_mode', name='uq_default_state_mode'),
    )


class ClientStatePrice(db.Model):
    __tablename__ = 'client_state_prices'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    shipping_mode = db.Column(db.String(50), default='standard', nullable=False)  # standard, prime, parcel, state_express, road_express, air
    price_100gm = db.Column(db.Float, default=0)
    price_250gm = db.Column(db.Float, default=0)
    price_500gm = db.Column(db.Float, default=0)
    price_1kg = db.Column(db.Float, default=0)
    price_2kg = db.Column(db.Float, default=0)
    price_3kg = db.Column(db.Float, default=0)
    price_extra_per_kg = db.Column(db.Float, default=20)  # Extra charge per kg for weight > 3kg
    # Air cargo pricing (> 3kg tiers)
    price_3_10kg = db.Column(db.Float, default=0)  # 3-10 kg tier
    price_10_25kg = db.Column(db.Float, default=0)  # 10-25 kg tier
    price_25_50kg = db.Column(db.Float, default=0)  # 25-50 kg tier
    price_50_100kg = db.Column(db.Float, default=0)  # 50-100 kg tier
    price_100plus_kg = db.Column(db.Float, default=0)  # 100+ kg tier
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('client_id', 'state', 'shipping_mode', name='uq_client_state_mode'),
    )


class NormalClientStatePrice(db.Model):
    __tablename__ = 'normal_client_state_prices'
    
    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.String(100), nullable=False)
    shipping_mode = db.Column(db.String(50), default='standard', nullable=False)  # standard, prime, parcel, state_express, road_express, air
    price_100gm = db.Column(db.Float, default=0)
    price_250gm = db.Column(db.Float, default=0)
    price_500gm = db.Column(db.Float, default=0)
    price_1kg = db.Column(db.Float, default=0)
    price_2kg = db.Column(db.Float, default=0)
    price_3kg = db.Column(db.Float, default=0)
    price_extra_per_kg = db.Column(db.Float, default=20)  # Rate per kg for weight > 3kg
    price_3_10kg = db.Column(db.Float, default=0)  # 3-10 kg tier
    price_10_25kg = db.Column(db.Float, default=0)  # 10-25 kg tier
    price_25_50kg = db.Column(db.Float, default=0)  # 25-50 kg tier
    price_50_100kg = db.Column(db.Float, default=0)  # 50-100 kg tier
    price_100plus_kg = db.Column(db.Float, default=0)  # 100+ kg tier
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('state', 'shipping_mode', name='uq_normal_state_mode'),
    )


class SystemSettings(db.Model):
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.String(200))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SalesVisit(db.Model):
    __tablename__ = 'sales_visits'

    id = db.Column(db.Integer, primary_key=True)
    # Contact Details
    contact_name = db.Column(db.String(100), nullable=False)
    contact_phone = db.Column(db.String(20))
    contact_email = db.Column(db.String(120))
    contact_designation = db.Column(db.String(100))
    # Company Details
    company_name = db.Column(db.String(150))
    company_address = db.Column(db.String(300))
    company_city = db.Column(db.String(100))
    company_state = db.Column(db.String(100))
    # Courier & Business Details
    covered_area = db.Column(db.String(200))          # Geographic area covered
    load_frequency = db.Column(db.String(100))         # Daily/Weekly/Monthly
    load_capacity = db.Column(db.String(100))          # Estimated shipment volume
    current_courier = db.Column(db.String(150))        # Which courier they use now
    price_cert = db.Column(db.String(200))             # Price certification details
    desired_price = db.Column(db.String(100))          # Client's desired price
    # Pitch & Status
    pitch_notes = db.Column(db.Text)
    status = db.Column(db.String(30), default='new')   # new, follow_up, converted, lost
    visit_date = db.Column(db.DateTime, default=datetime.utcnow)
    # Meta
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = db.relationship('User', foreign_keys=[created_by], backref='sales_visits')
    follow_ups = db.relationship('FollowUp', back_populates='visit', cascade='all, delete-orphan', order_by='FollowUp.created_at')
    meetings = db.relationship('Meeting', back_populates='visit', cascade='all, delete-orphan', order_by='Meeting.scheduled_at')


class FollowUp(db.Model):
    __tablename__ = 'follow_ups'

    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('sales_visits.id'), nullable=False)
    notes = db.Column(db.Text, nullable=False)
    follow_up_date = db.Column(db.DateTime)             # Next scheduled follow-up date
    status = db.Column(db.String(20), default='pending')  # pending, done, skipped
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    visit = db.relationship('SalesVisit', back_populates='follow_ups')
    creator = db.relationship('User', foreign_keys=[created_by])


class Meeting(db.Model):
    __tablename__ = 'meetings'

    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('sales_visits.id'), nullable=False)
    scheduled_at = db.Column(db.DateTime, nullable=False)
    rescheduled_at = db.Column(db.DateTime)             # New datetime if rescheduled
    location = db.Column(db.String(200))
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='scheduled')  # scheduled, completed, cancelled, rescheduled
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    visit = db.relationship('SalesVisit', back_populates='meetings')
    creator = db.relationship('User', foreign_keys=[created_by])


class Courier(db.Model):
    __tablename__ = 'couriers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    service_type = db.Column(db.String(100))  # e.g., "Express", "Standard", "Premium"
    contact_person = db.Column(db.String(100))
    contact_email = db.Column(db.String(120))
    contact_phone = db.Column(db.String(20))
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Offer(db.Model):
    __tablename__ = 'offers'

    id = db.Column(db.Integer, primary_key=True)
    min_amount = db.Column(db.Float, nullable=False)  # Minimum order amount
    max_amount = db.Column(db.Float, nullable=False)  # Maximum order amount
    offer_amount = db.Column(db.Float, nullable=False)  # Discount amount in rupees
    description = db.Column(db.String(200))  # e.g., "200-500 Rs offer 30 Rs"
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    creator = db.relationship('User', foreign_keys=[created_by])


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    username = db.Column(db.String(80), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=True)
    branch_name = db.Column(db.String(100))
    action = db.Column(db.String(100), nullable=False)  # CREATE, UPDATE, DELETE, PAYMENT, VERIFY, STATUS_CHANGE
    entity_type = db.Column(db.String(50), nullable=False)  # Order, Client, User, Branch, etc.
    entity_id = db.Column(db.Integer)
    entity_name = db.Column(db.String(200))  # e.g., receipt_number, client_name
    old_value = db.Column(db.Text)  # JSON string of old values
    new_value = db.Column(db.Text)  # JSON string of new values
    changes = db.Column(db.Text)  # Description of what changed
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=True)
    client_name = db.Column(db.String(100))
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    receipt_number = db.Column(db.String(50))
    due_amount = db.Column(db.Float)  # Track due amounts for alerts
    ip_address = db.Column(db.String(50))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    user = db.relationship('User', backref='audit_logs')
    branch = db.relationship('Branch', backref='audit_logs')
    client = db.relationship('Client', backref='audit_logs')
    order = db.relationship('Order', backref='audit_logs')


def init_db(app):
    import os
    # Ensure the instance folder exists so SQLite can create the DB file
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if db_uri.startswith('sqlite:///'):
        db_path = db_uri[len('sqlite:///'):]
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    db.init_app(app)
    with app.app_context():
        db.create_all()
        
        # Create default admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@crm.com',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
        
        # Create default receipt setting
        if not ReceiptSetting.query.first():
            receipt_setting = ReceiptSetting(
                base_number='100371900086',
                current_sequence=0
            )
            db.session.add(receipt_setting)
        
        # Create default billing patterns
        if not BillingPattern.query.first():
            patterns = [
                BillingPattern(name='Pattern 10', pattern_type='10', base_rate=50, rate_per_kg=10),
                BillingPattern(name='Pattern 15', pattern_type='15', base_rate=75, rate_per_kg=15),
                BillingPattern(name='Pattern 30', pattern_type='30', base_rate=100, rate_per_kg=30),
            ]
            db.session.add_all(patterns)
        
        db.session.commit()