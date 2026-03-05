import os
import secrets
import random
from datetime import datetime, timedelta
from functools import wraps
import pandas as pd
from io import BytesIO
import qrcode
import base64
import json
import fitz  # PyMuPDF
import google.generativeai as genai
from PIL import Image

from flask import (
    Flask, render_template, request, redirect, url_for, flash, 
    jsonify, session, send_file, make_response
)
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from werkzeug.utils import secure_filename

from config import Config
from models import (
    db, init_db, User, Branch, Client, Order, ReceiptSetting,
    TrackingUpdate, ExcelUpload, ExcelData, SystemSettings,
    DefaultStatePrice, ClientStatePrice, Notification, StaffReceiptAssignment, Receiver,
    BillingPattern
)

app = Flask(__name__)
app.config.from_object(Config)

# Configure Gemini
if app.config.get('GEMINI_API_KEY'):
    genai.configure(api_key=app.config['GEMINI_API_KEY'])


# JWT Configuration
app.config['JWT_SECRET_KEY'] = app.config['SECRET_KEY']  # Use same secret key
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=30)  # Long expiry for mobile

# Initialize extensions
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
jwt = JWTManager(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize database
init_db(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


@app.context_processor
def inject_now():
    return {'now': datetime.utcnow(), 'timedelta': timedelta}


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.template_filter('each_to_dict')
def each_to_dict(items):
    return [item.to_dict() for item in items]

@app.template_filter('rjust')
def rjust_filter(s, width, fillchar='0'):
    return str(s).rjust(width, fillchar)


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def staff_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'manager', 'staff']:
            flash('Staff access required.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'manager']:
            flash('Admin or Manager access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def validate_pincode(pincode):
    """Ensure pincode is exactly 6 digits."""
    if not pincode:
        return True  # If optional, allow empty
    return len(pincode) == 6 and pincode.isdigit()


def generate_receipt_number(user=None):
    from models import Order  # Local import to avoid circular dependency
    
    # Try to find a staff-wise assignment first
    if user and user.role != 'admin':
        assignment = StaffReceiptAssignment.query.filter_by(
            user_id=user.id, 
            branch_id=user.branch_id, 
            is_active=True
        ).first()

        if not assignment and user.branch_id:
             assignment = StaffReceiptAssignment.query.filter_by(
                branch_id=user.branch_id,
                user_id=None,
                is_active=True
            ).first()
        
        if assignment:
            # Check for actual max in DB once to self-heal sequence
            pattern = f"{assignment.prefix or ''}{assignment.base_number}%"
            last = Order.query.filter(Order.receipt_number.like(pattern)).order_by(Order.receipt_number.desc()).first()
            if last:
                try:
                    num = last.receipt_number
                    if assignment.prefix: num = num.replace(assignment.prefix, '', 1)
                    seq_str = num.replace(assignment.base_number, '', 1)
                    seq_digits = "".join([c for c in seq_str if c.isdigit()])
                    if seq_digits:
                        db_seq = int(seq_digits)
                        if db_seq > assignment.current_sequence:
                            assignment.current_sequence = db_seq
                except: pass

            # Loop to find an available number
            max_attempts = 100
            for _ in range(max_attempts):
                assignment.current_sequence += 1
                
                # Logic for range-based vs prefix-based
                if assignment.range_end:
                    try:
                        start_num = int(assignment.base_number)
                        current_num = start_num + assignment.current_sequence
                        # Check if we exceeded range
                        if current_num > int(assignment.range_end):
                             # TODO: Handle overflow? Maybe just let it fail or wrap around
                             pass
                        receipt_number = f"{assignment.prefix or ''}{current_num}"
                    except (ValueError, TypeError):
                        # Fallback if numbers aren't valid integers
                        receipt_number = f"{assignment.prefix or ''}{assignment.base_number}{assignment.current_sequence:06d}"
                else:
                    receipt_number = f"{assignment.prefix or ''}{assignment.base_number}{assignment.current_sequence:06d}"

                if not Order.query.filter_by(receipt_number=receipt_number).first():
                    db.session.commit()
                    return receipt_number, assignment.id
            
            # Fallback
            db.session.commit()
            return f"{assignment.prefix or ''}{assignment.base_number}{assignment.current_sequence:06d}", assignment.id

    # Fallback to global setting
    setting = ReceiptSetting.query.filter_by(is_active=True).first()
    if not setting:
        setting = ReceiptSetting(base_number='100371900086', current_sequence=0)
        db.session.add(setting)
    
    # Check for actual max in DB once to self-heal sequence
    prefix = setting.prefix or ''
    base = setting.base_number
    suffix = setting.suffix or ''
    pattern = f"{prefix}{base}%{suffix}"
    last = Order.query.filter(Order.receipt_number.like(pattern)).order_by(Order.receipt_number.desc()).first()
    if last:
        try:
            num = last.receipt_number
            if prefix: num = num.replace(prefix, '', 1)
            if suffix: num = num.rsplit(suffix, 1)[0]
            seq_str = num.replace(base, '', 1)
            seq_digits = "".join([c for c in seq_str if c.isdigit()])
            if seq_digits:
                db_seq = int(seq_digits)
                if db_seq > setting.current_sequence:
                    setting.current_sequence = db_seq
        except: pass

    # Loop for global uniqueness
    max_attempts = 100
    for _ in range(max_attempts):
        setting.current_sequence += 1
        
        if setting.range_end:
            try:
                start_num = int(setting.base_number)
                receipt_number = f"{prefix}{start_num + setting.current_sequence}{suffix}"
            except (ValueError, TypeError):
                receipt_number = f"{prefix}{base}{setting.current_sequence:06d}{suffix}"
        else:
            receipt_number = f"{prefix}{base}{setting.current_sequence:06d}{suffix}"
            
        if not Order.query.filter_by(receipt_number=receipt_number).first():
            break
            
    db.session.commit()
    return receipt_number, None

def get_next_receipt_number(user=None):
    """Predicts the next receipt number without incrementing the database permanently, 
    but checks for uniqueness against the Order table."""
    from models import Order
    
    if user and user.role != 'admin':
        assignment = StaffReceiptAssignment.query.filter_by(
            user_id=user.id, 
            branch_id=user.branch_id, 
            is_active=True
        ).first()

        if not assignment and user.branch_id:
             assignment = StaffReceiptAssignment.query.filter_by(
                branch_id=user.branch_id,
                user_id=None,
                is_active=True
            ).first()
        
        if assignment:
            # Self-heal prediction
            seq = assignment.current_sequence
            pattern = f"{assignment.prefix or ''}{assignment.base_number}%"
            last = Order.query.filter(Order.receipt_number.like(pattern)).order_by(Order.receipt_number.desc()).first()
            if last:
                try:
                    num = last.receipt_number
                    if assignment.prefix: num = num.replace(assignment.prefix, '', 1)
                    seq_str = num.replace(assignment.base_number, '', 1)
                    seq_digits = "".join([c for c in seq_str if c.isdigit()])
                    if seq_digits:
                        db_seq = int(seq_digits)
                        if db_seq > seq: seq = db_seq
                except: pass

            for _ in range(50):
                seq += 1
                if assignment.range_end:
                    try:
                        start_num = int(assignment.base_number)
                        number = f"{assignment.prefix or ''}{start_num + seq}"
                    except (ValueError, TypeError):
                        number = f"{assignment.prefix or ''}{assignment.base_number}{seq:06d}"
                else:
                    number = f"{assignment.prefix or ''}{assignment.base_number}{seq:06d}"
                
                if not Order.query.filter_by(receipt_number=number).first():
                    return number
            return f"{assignment.prefix or ''}{assignment.base_number}{(seq + 1):06d}"

    setting = ReceiptSetting.query.filter_by(is_active=True).first()
    if not setting:
        return "100371900086000001"
    
    seq = setting.current_sequence
    prefix = setting.prefix or ''
    base = setting.base_number
    suffix = setting.suffix or ''
    pattern = f"{prefix}{base}%{suffix}"
    last = Order.query.filter(Order.receipt_number.like(pattern)).order_by(Order.receipt_number.desc()).first()
    if last:
        try:
            num = last.receipt_number
            if prefix: num = num.replace(prefix, '', 1)
            if suffix: num = num.rsplit(suffix, 1)[0]
            seq_str = num.replace(base, '', 1)
            seq_digits = "".join([c for c in seq_str if c.isdigit()])
            if seq_digits:
                db_seq = int(seq_digits)
                if db_seq > seq: seq = db_seq
        except: pass

    for _ in range(50):
        seq += 1
        if setting.range_end:
            try:
                start_num = int(setting.base_number)
                number = f"{prefix}{start_num + seq}{suffix}"
            except (ValueError, TypeError):
                number = f"{prefix}{base}{seq:06d}{suffix}"
        else:
            number = f"{prefix}{base}{seq:06d}{suffix}"
            
        if not Order.query.filter_by(receipt_number=number).first():
            return number
            
    return f"{prefix}{base}{(seq + 1):06d}{suffix}"


def calculate_from_state_price(weight, price_obj):
    amount = 0
    # tiered pricing
    if weight <= 0.1: amount = price_obj.price_100gm
    elif weight <= 0.25: amount = price_obj.price_250gm
    elif weight <= 0.5: amount = price_obj.price_500gm
    elif weight <= 0.75: amount = price_obj.price_750gm
    elif weight <= 1.0: amount = price_obj.price_1kg
    elif weight <= 2.0: amount = price_obj.price_2kg
    elif weight <= 3.0: amount = price_obj.price_3kg
    else:
        # For weights > 3kg, use 3kg price + extra per kg if we can estimate, 
        # but for now let's just use 3kg as base and add 10/kg for simplicity
        base_3kg = price_obj.price_3kg or 150
        extra_weight = weight - 3.0
        amount = base_3kg + (extra_weight * 20) # Conservative estimate

    if amount == 0:
        return None
        
    return amount, 0, 0, 0, amount


def calculate_order_amount(weight, billing_pattern_id=None, state=None, client_id=None, insured_amount=0):
    state_clean = state.strip().lower() if state else None
    
    # Get insurance percentage from settings
    insurance_setting = SystemSettings.query.filter_by(key='insurance_percentage').first()
    insurance_percentage = float(insurance_setting.value) if insurance_setting and insurance_setting.value else 0
    insurance_charge = (insured_amount * insurance_percentage) / 100
    
    # 1. Check for Client State Price first
    if client_id and state_clean:
        client_price = ClientStatePrice.query.filter(
            ClientStatePrice.client_id == client_id,
            db.func.lower(ClientStatePrice.state) == state_clean
        ).first()
        if client_price:
            result = calculate_from_state_price(weight, client_price)
            if result:
                # result is (base, weight_charge, additional, discount, total)
                res_list = list(result)
                res_list[4] += insurance_charge # Add to total
                return (*tuple(res_list), 'client', insurance_charge)

    # 2. Check for Default State Price
    if state_clean:
        default_price = DefaultStatePrice.query.filter(
            db.func.lower(DefaultStatePrice.state) == state_clean
        ).first()
        if default_price:
            result = calculate_from_state_price(weight, default_price)
            if result:
                res_list = list(result)
                res_list[4] += insurance_charge # Add to total
                return (*tuple(res_list), 'state', insurance_charge)

    # 3. No Rate Found
    return 0.0, 0, 0, 0, insurance_charge, 'none', insurance_charge


# ============== AUTHENTICATION ROUTES ==============

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'customer':
            return redirect(url_for('customer_dashboard'))
        return redirect(url_for('dashboard'))
    return redirect(url_for('tracking'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'customer':
            return redirect(url_for('customer_dashboard'))
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account is deactivated. Contact admin.', 'error')
                return render_template('login.html')
            
            login_user(user, remember=True)
            flash('Login successful!', 'success')
            if user.role == 'customer':
                return redirect(url_for('customer_dashboard'))
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


# ============== DASHBOARD ==============

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'customer':
        return redirect(url_for('customer_dashboard'))
    # Get statistics
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status='pending').count()
    in_transit = Order.query.filter_by(status='in_transit').count()
    delivered = Order.query.filter_by(status='delivered').count()
    
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    
    # Staff count
    total_staff = User.query.filter_by(role='staff').count()
    delivery_personnel = User.query.filter_by(role='delivery').count()
    
    return render_template('dashboard.html',
                         total_orders=total_orders,
                         pending_orders=pending_orders,
                         in_transit=in_transit,
                         delivered=delivered,
                         recent_orders=recent_orders,
                         total_staff=total_staff,
                         delivery_personnel=delivery_personnel)


@app.route('/customer/dashboard')
@login_required
def customer_dashboard():
    if current_user.role != 'customer':
        flash('Access denied.')
        return redirect(url_for('dashboard'))
    
    # Get all orders associated with this customer's phone or email
    my_orders = Order.query.filter(
        (Order.customer_phone == current_user.phone) | 
        (Order.customer_email == current_user.email)
    ).order_by(Order.created_at.desc()).all()
    
    return render_template('customer_portal.html', orders=my_orders)

@app.route('/customers')
@login_required
@staff_required
def customers():
    # Get unique walk-in customers from orders
    # In a real app, we might have a dedicated Customer table
    # Here we aggregate from the Order table
    walkin_orders = Order.query.filter_by(order_type='walkin').all()
    
    customers_dict = {}
    for order in walkin_orders:
        key = (order.customer_name, order.customer_phone)
        if key not in customers_dict:
            customers_dict[key] = {
                'name': order.customer_name,
                'phone': order.customer_phone,
                'email': order.customer_email,
                'address': order.customer_address,
                'total_orders': 1,
                'last_order_date': order.created_at,
                'total_spent': order.total_amount or 0
            }
        else:
            customers_dict[key]['total_orders'] += 1
            customers_dict[key]['total_spent'] += (order.total_amount or 0)
            if order.created_at > customers_dict[key]['last_order_date']:
                customers_dict[key]['last_order_date'] = order.created_at
    
    customers_list = sorted(customers_dict.values(), key=lambda x: x['last_order_date'], reverse=True)
    
    return render_template('customers.html', customers=customers_list)


@app.route('/customer/profile')
@login_required
@staff_required
def customer_profile():
    name = request.args.get('name')
    phone = request.args.get('phone')
    
    if not name or not phone:
        flash('Customer name and phone are required to view profile.', 'danger')
        return redirect(url_for('customers'))
        
    orders = Order.query.filter_by(
        customer_name=name, 
        customer_phone=phone,
        order_type='walkin'
    ).order_by(Order.created_at.desc()).all()
    
    if not orders:
        flash('Customer not found.', 'warning')
        return redirect(url_for('customers'))
        
    summary = {
        'name': name,
        'phone': phone,
        'email': next((o.customer_email for o in orders if o.customer_email), 'N/A'),
        'address': next((o.customer_address for o in orders if o.customer_address), 'N/A'),
        'total_orders': len(orders),
        'total_spent': sum(o.total_amount or 0 for o in orders),
        'avg_order': sum(o.total_amount or 0 for o in orders) / len(orders) if orders else 0,
        'last_order_date': max(o.created_at for o in orders)
    }
    
    return render_template('customer_profile.html', customer=summary, orders=orders)


# ============== BRANCH MANAGEMENT ==============

@app.route('/branches')
@login_required
@admin_required
def branches():
    branches = Branch.query.all()
    return render_template('branches.html', branches=branches)


@app.route('/branch/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_branch():
    if request.method == 'POST':
        branch = Branch(
            name=request.form.get('name'),
            code=request.form.get('code'),
            address=request.form.get('address'),
            phone=request.form.get('phone'),
            email=request.form.get('email')
        )
        db.session.add(branch)
        db.session.commit()
        flash('Branch added successfully!', 'success')
        return redirect(url_for('branches'))
    
    return render_template('add_branch.html')


@app.route('/branch/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_branch(id):
    branch = Branch.query.get_or_404(id)
    
    if request.method == 'POST':
        branch.name = request.form.get('name')
        branch.code = request.form.get('code')
        branch.address = request.form.get('address')
        branch.phone = request.form.get('phone')
        branch.email = request.form.get('email')
        branch.is_active = request.form.get('is_active') == 'on'
        
        db.session.commit()
        flash('Branch updated successfully!', 'success')
        return redirect(url_for('branches'))
    
    return render_template('edit_branch.html', branch=branch)


@app.route('/branch/delete/<int:id>')
@login_required
@admin_required
def delete_branch(id):
    branch = Branch.query.get_or_404(id)
    db.session.delete(branch)
    db.session.commit()
    flash('Branch deleted successfully!', 'success')
    return redirect(url_for('branches'))


# ============== STAFF MANAGEMENT ==============

@app.route('/staff')
@login_required
@admin_required
def staff_management():
    staff = User.query.filter(User.role.in_(['staff', 'delivery'])).all()
    branches = Branch.query.filter_by(is_active=True).all()
    return render_template('staff_management.html', staff=staff, branches=branches)


@app.route('/staff/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_staff():
    branches = Branch.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return render_template('add_staff.html', branches=branches)
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'error')
            return render_template('add_staff.html', branches=branches)
        
        user = User(
            username=username,
            email=email,
            role=request.form.get('role'),
            branch_id=request.form.get('branch_id') or None,
            phone=request.form.get('phone'),
            address=request.form.get('address')
        )
        user.set_password(request.form.get('password'))
        
        db.session.add(user)
        db.session.commit()
        flash('Staff member added successfully!', 'success')
        return redirect(url_for('staff_management'))
    
    return render_template('add_staff.html', branches=branches)


@app.route('/staff/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_staff(id):
    user = User.query.get_or_404(id)
    branches = Branch.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.role = request.form.get('role')
        user.branch_id = request.form.get('branch_id') or None
        user.phone = request.form.get('phone')
        user.address = request.form.get('address')
        user.is_active = request.form.get('is_active') == 'on'
        
        if request.form.get('password'):
            user.set_password(request.form.get('password'))
        
        db.session.commit()
        flash('Staff member updated successfully!', 'success')
        return redirect(url_for('staff_management'))
    
    return render_template('edit_staff.html', user=user, branches=branches)


@app.route('/staff/delete/<int:id>')
@login_required
@admin_required
def delete_staff(id):
    user = User.query.get_or_404(id)
    if user.role == 'admin':
        flash('Cannot delete admin user.', 'error')
        return redirect(url_for('staff_management'))
    
    db.session.delete(user)
    db.session.commit()
    flash('Staff member deleted successfully!', 'success')
    return redirect(url_for('staff_management'))


# ============== DELIVERY PERSONNEL ==============

@app.route('/delivery-personnel')
@login_required
@admin_required
def delivery_personnel():
    personnel = User.query.filter_by(role='delivery').all()
    branches = Branch.query.filter_by(is_active=True).all()
    return render_template('delivery_personnel.html', personnel=personnel, branches=branches)


@app.route('/delivery-personnel/assign/<int:order_id>', methods=['POST'])
@login_required
@staff_required
def assign_delivery(order_id):
    order = Order.query.get_or_404(order_id)
    delivery_person_id = request.form.get('delivery_person_id')
    
    order.delivery_person_id = delivery_person_id
    order.status = 'assigned'
    
    # Add tracking update
    tracking = TrackingUpdate(
        order_id=order.id,
        status='Assigned to delivery personnel',
        updated_by=current_user.id
    )
    db.session.add(tracking)
    db.session.commit()
    
    flash('Delivery personnel assigned successfully!', 'success')
    return redirect(url_for('order_details', id=order_id))


# ============== CLIENT MANAGEMENT ==============

@app.route('/clients')
@login_required
@staff_required
def clients():
    clients = Client.query.all()
    return render_template('clients.html', clients=clients)


@app.route('/client/add', methods=['GET', 'POST'])
@login_required
@staff_required
def add_client():
    if request.method == 'POST':
        client = Client(
            name=request.form.get('name'),
            company_name=request.form.get('company_name'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            alt_phone=request.form.get('alt_phone'),
            alt_email=request.form.get('alt_email'),
            address=request.form.get('address'),
            alt_address=request.form.get('alt_address'),
            gst_number=request.form.get('gst_number'),
            bill_pattern=request.form.get('bill_pattern'),
            billing_date=request.form.get('billing_date', type=int)
        )
        db.session.add(client)
        db.session.commit()
        flash('Client added successfully!', 'success')
        return redirect(url_for('clients'))
    
    return render_template('add_client.html')


@app.route('/client/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@staff_required
def edit_client(id):
    client = Client.query.get_or_404(id)
    
    if request.method == 'POST':
        client.name = request.form.get('name')
        client.company_name = request.form.get('company_name')
        client.email = request.form.get('email')
        client.phone = request.form.get('phone')
        client.alt_phone = request.form.get('alt_phone')
        client.alt_email = request.form.get('alt_email')
        client.address = request.form.get('address')
        client.alt_address = request.form.get('alt_address')
        client.gst_number = request.form.get('gst_number')
        client.bill_pattern = request.form.get('bill_pattern')
        client.billing_date = request.form.get('billing_date', type=int)
        client.is_active = request.form.get('is_active') == 'on'
        
        db.session.commit()
        flash('Client updated successfully!', 'success')
        return redirect(url_for('clients'))
    
    return render_template('edit_client.html', client=client)


@app.route('/client/<int:id>/details')
@login_required
@staff_required
def client_details(id):
    client = Client.query.get_or_404(id)
    return render_template('client_details.html', client=client)


@app.route('/client/<int:client_id>/receiver/add', methods=['GET', 'POST'])
@login_required
@staff_required
def add_receiver(client_id):
    client = Client.query.get_or_404(client_id)
    if request.method == 'POST':
        pincode = request.form.get('pincode')
        if not validate_pincode(pincode):
            flash('Invalid Pincode. It must be exactly 6 digits.', 'error')
            return redirect(url_for('add_receiver', client_id=client_id))
            
        receiver = Receiver(
            client_id=client_id,
            name=request.form.get('name'),
            company_name=request.form.get('company_name'),
            phone=request.form.get('phone'),
            alt_phone=request.form.get('alt_phone'),
            email=request.form.get('email'),
            alt_email=request.form.get('alt_email'),
            address=request.form.get('address'),
            alt_address=request.form.get('alt_address'),
            city=request.form.get('city'),
            state=request.form.get('state'),
            pincode=pincode,
            gst_number=request.form.get('gst_number'),
            bill_pattern=request.form.get('bill_pattern')
        )
        db.session.add(receiver)
        db.session.commit()
        flash('Receiver added successfully!', 'success')
        return redirect(url_for('client_details', id=client_id))
    
    return render_template('add_receiver.html', client=client)


@app.route('/receiver/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@staff_required
def edit_receiver(id):
    receiver = Receiver.query.get_or_404(id)
    if request.method == 'POST':
        pincode = request.form.get('pincode')
        if not validate_pincode(pincode):
            flash('Invalid Pincode. It must be exactly 6 digits.', 'error')
            return redirect(url_for('edit_receiver', id=id))

        receiver.name = request.form.get('name')
        receiver.company_name = request.form.get('company_name')
        receiver.phone = request.form.get('phone')
        receiver.alt_phone = request.form.get('alt_phone')
        receiver.email = request.form.get('email')
        receiver.alt_email = request.form.get('alt_email')
        receiver.address = request.form.get('address')
        receiver.alt_address = request.form.get('alt_address')
        receiver.city = request.form.get('city')
        receiver.state = request.form.get('state')
        receiver.pincode = pincode
        receiver.gst_number = request.form.get('gst_number')
        receiver.bill_pattern = request.form.get('bill_pattern')
        
        db.session.commit()
        flash('Receiver updated successfully!', 'success')
        return redirect(url_for('client_details', id=receiver.client_id))
    
    return render_template('edit_receiver.html', receiver=receiver)


@app.route('/client/<int:client_id>/address/add', methods=['GET', 'POST'])
@login_required
@staff_required
def add_client_address(client_id):
    client = Client.query.get_or_404(client_id)
    if request.method == 'POST':
        pincode = request.form.get('pincode')
        if not validate_pincode(pincode):
            flash('Invalid Pincode. It must be exactly 6 digits.', 'error')
            return redirect(url_for('add_client_address', client_id=client_id))
            
        address = ClientAddress(
            client_id=client_id,
            address_label=request.form.get('address_label'),
            address=request.form.get('address'),
            city=request.form.get('city'),
            state=request.form.get('state'),
            pincode=pincode
        )
        db.session.add(address)
        db.session.commit()
        flash('Address added successfully!', 'success')
        return redirect(url_for('client_details', id=client_id))
    
    return render_template('add_client_address.html', client=client)


@app.route('/address/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@staff_required
def edit_client_address(id):
    address = ClientAddress.query.get_or_404(id)
    if request.method == 'POST':
        pincode = request.form.get('pincode')
        if not validate_pincode(pincode):
            flash('Invalid Pincode. It must be exactly 6 digits.', 'error')
            return redirect(url_for('edit_client_address', id=id))
            
        address.address_label = request.form.get('address_label')
        address.address = request.form.get('address')
        address.city = request.form.get('city')
        address.state = request.form.get('state')
        address.pincode = pincode
        
        db.session.commit()
        flash('Address updated successfully!', 'success')
        return redirect(url_for('client_details', id=address.client_id))
    
    return render_template('edit_client_address.html', address=address)


# ============== ORDER MANAGEMENT ==============

@app.route('/orders')
@login_required
@staff_required
def orders():
    status_filter = request.args.get('status', '')
    order_type_filter = request.args.get('order_type', '')
    search = request.args.get('search', '')
    
    query = Order.query
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    if order_type_filter:
        query = query.filter_by(order_type=order_type_filter)
    
    if search:
        query = query.filter(
            (Order.receipt_number.contains(search)) |
            (Order.customer_name.contains(search)) |
            (Order.customer_phone.contains(search))
        )
    
    orders = query.order_by(Order.created_at.desc()).all()
    delivery_personnel = User.query.filter_by(role='delivery', is_active=True).all()
    
    return render_template('orders.html', 
                         orders=orders, 
                         delivery_personnel=delivery_personnel,
                         status_filter=status_filter,
                         order_type_filter=order_type_filter,
                         search=search)


@app.route('/order/walkin', methods=['GET', 'POST'])
@login_required
@staff_required
def walkin_order():
    if request.method == 'POST':
        # ... POST logic
        receipt_type = request.form.get('receipt_type', 'standard')
        receipt_number = request.form.get('receipt_number')
        
        assignment_id = None
        if receipt_type == 'standard':
            predicted_number = get_next_receipt_number(current_user)
            if receipt_number == predicted_number:
                receipt_number, assignment_id = generate_receipt_number(current_user)
        
        if not receipt_number:
            flash('Tracking number is required!', 'danger')
            return redirect(url_for('walkin_order'))
        
        existing_order = Order.query.filter_by(receipt_number=receipt_number).first()
        if existing_order:
            flash(f'Tracking number {receipt_number} already exists!', 'danger')
            return redirect(url_for('walkin_order'))

        custom_tag = request.form.get('custom_handling_tag', '').strip()
        predefined_tags = request.form.getlist('handling_tags')
        all_tags = predefined_tags.copy()
        if custom_tag:
            all_tags.append(custom_tag)
        
        receiver_pincode = request.form.get('receiver_pincode')
        if not validate_pincode(receiver_pincode):
            flash('Invalid Pincode. It must be exactly 6 digits.', 'danger')
            return redirect(url_for('walkin_order'))
        
        order = Order(
            receipt_number=receipt_number,
            receipt_type=receipt_type,
            assignment_id=assignment_id,
            order_type='walkin',
            receipt_mode=request.form.get('receipt_mode'),
            customer_name=request.form.get('customer_name'),
            customer_phone=request.form.get('customer_phone'),
            customer_email=request.form.get('customer_email'),
            customer_address=request.form.get('customer_address'),
            receiver_name=request.form.get('receiver_name'),
            receiver_phone=request.form.get('receiver_phone'),
            receiver_address=request.form.get('receiver_address'),
            receiver_city=request.form.get('receiver_city'),
            receiver_state=request.form.get('receiver_state'),
            receiver_pincode=request.form.get('receiver_pincode'),
            package_description=request.form.get('package_description'),
            weight=float(request.form.get('weight') or 0),
            number_of_boxes=int(request.form.get('number_of_boxes') or 1),
            special_instructions=request.form.get('special_instructions'),
            handling_tags=','.join(all_tags),
            branch_id=current_user.branch_id,
            created_by=current_user.id,
            status='pending',
            payment_mode=request.form.get('payment_mode')
        )
        
        received_amount = float(request.form.get('received_amount') or 0)
        insured_amount = float(request.form.get('insured_amount') or 0)
        
        order.received_amount = received_amount
        order.total_amount = received_amount
        order.insured_amount = insured_amount
        
        if order.weight:
            base, weight_charge, additional, discount, total, _, ins_charge = calculate_order_amount(
                order.weight, state=order.receiver_state, insured_amount=order.insured_amount
            )
            order.base_amount = base
            order.weight_charges = weight_charge
            order.additional_charges = additional
            order.discount = discount
            order.insurance_charge = ins_charge
        else:
            order.base_amount = received_amount
            order.weight_charges = 0
            order.additional_charges = 0
            order.discount = 0
        
        if order.received_amount > 0:
            order.payment_status = 'paid'
        else:
            order.payment_status = 'unpaid'
        
        order.generate_tracking_link()
        db.session.add(order)
        db.session.commit()
        
        tracking = TrackingUpdate(
            order_id=order.id,
            status='Order Created',
            description='Walk-in order has been created',
            updated_by=current_user.id
        )
        db.session.add(tracking)
        db.session.commit()
        
        create_link = request.form.get('create_customer_link')
        if create_link:
            order.generate_customer_form_link()
            db.session.commit()
            flash(f'Order created! Link: {url_for("customer_form", token=order.customer_form_link, _external=True)}', 'success')
        else:
            flash(f'Order created successfully! Receipt: {receipt_number}', 'success')
        
        return redirect(url_for('walkin_bill', id=order.id))
    
    # Prefill from query params
    prefill = {
        'name': request.args.get('name', ''),
        'phone': request.args.get('phone', ''),
        'email': request.args.get('email', ''),
        'address': request.args.get('address', '')
    }
    
    return render_template('walkin_order.html', prefill=prefill)



@app.route('/order/walkin/<int:id>/bill')
@login_required
@manager_required
def walkin_bill(id):
    order = Order.query.get_or_404(id)
    if order.order_type != 'walkin':
        flash('This is not a walking customer order.', 'error')
        return redirect(url_for('order_details', id=id))
    is_gst = request.args.get('gst', 'no').lower() == 'yes'  # Get GST parameter
    return render_template('walkin_bill.html', order=order, is_gst=is_gst)


@app.route('/api/order/payment', methods=['POST'])
@app.route('/api/walkin/payment', methods=['POST']) # Maintain backward compatibility
@login_required
@staff_required
def record_order_payment():
    data = request.get_json()
    order_id = data.get('order_id')
    received_amount = float(data.get('received_amount', 0))
    payment_mode = data.get('payment_mode', 'cash')
    
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'success': False, 'message': 'Order not found'}), 404
    
    order.received_amount = received_amount
    order.payment_mode = payment_mode
    
    # Update payment status
    if received_amount >= order.total_amount:
        order.payment_status = 'paid'
    elif received_amount > 0:
        order.payment_status = 'partial'
    else:
        order.payment_status = 'unpaid'
    
    # Calculate difference if any
    if received_amount != order.total_amount:
        order.amount_difference = received_amount - order.total_amount
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Payment recorded successfully',
        'payment_status': order.payment_status
    })



@app.route('/order/client', methods=['GET', 'POST'])
@login_required
@staff_required
def client_order():
    clients = Client.query.filter_by(is_active=True).all()
    # Eager load receivers and addresses for JSON-like access in select data attributes if needed
    # but for simplicity we'll let the user select a client and then maybe use JS to fetch or just pre-pass.
    # Let's pre-pass them via data attributes on the options.
    patterns = BillingPattern.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        receipt_type = request.form.get('receipt_type', 'standard')
        receipt_number = request.form.get('receipt_number')
        
        assignment_id = None
        if receipt_type == 'standard':
            predicted_number = get_next_receipt_number(current_user)
            if receipt_number == predicted_number:
                receipt_number, assignment_id = generate_receipt_number(current_user)
            else:
                pass

        if not receipt_number:
            flash('Receipt number is required!', 'danger')
            return redirect(url_for('client_order'))
        
        # Check for duplicate receipt number
        existing_order = Order.query.filter_by(receipt_number=receipt_number).first()
        if existing_order:
            flash(f'Receipt number {receipt_number} already exists! Please use a different number or use standard mode to auto-generate.', 'danger')
            return redirect(url_for('client_order'))

        client_id = request.form.get('client_id')
        client = Client.query.get(client_id)
        
        # Get custom handling tag if provided
        custom_tag = request.form.get('custom_handling_tag', '').strip()
        predefined_tags = request.form.getlist('handling_tags')
        
        # Combine predefined and custom tags
        all_tags = predefined_tags.copy()
        if custom_tag:
            all_tags.append(custom_tag)
        
        # Validate Pincode
        receiver_pincode = request.form.get('receiver_pincode')
        if not validate_pincode(receiver_pincode):
            flash('Invalid Pincode. It must be exactly 6 digits.', 'danger')
            return redirect(url_for('client_order'))
        
        order = Order(
            receipt_number=receipt_number,
            receipt_type=receipt_type,
            assignment_id=assignment_id,
            order_type='client',
            receipt_mode=request.form.get('receipt_mode'),
            client_id=client_id,
            sender_address_id=request.form.get('sender_address_id') or None,
            receiver_id=request.form.get('receiver_id') or None,
            customer_name=client.name if client else request.form.get('customer_name'),
            customer_phone=client.phone if client else request.form.get('customer_phone'),
            customer_email=client.email if client else request.form.get('customer_email'),
            customer_address=client.address if client else request.form.get('customer_address'),
            receiver_name=request.form.get('receiver_name'),
            receiver_phone=request.form.get('receiver_phone'),
            receiver_address=request.form.get('receiver_address'),
            receiver_city=request.form.get('receiver_city'),
            receiver_state=request.form.get('receiver_state'),
            receiver_pincode=request.form.get('receiver_pincode'),
            package_description=request.form.get('package_description'),
            weight=float(request.form.get('weight') or 0),
            number_of_boxes=int(request.form.get('number_of_boxes') or 1),
            special_instructions=request.form.get('special_instructions'),
            handling_tags=','.join(all_tags),  # Save all tags (predefined + custom)
            branch_id=current_user.branch_id,
            created_by=current_user.id,
            status='pending'
        )
        
        # Add insured amount
        insured_amount = float(request.form.get('insured_amount') or 0)
        order.insured_amount = insured_amount
        
        # Determine total amount (client orders usually have fixed pricing elsewhere or manual)
        # For now, we use state pricing if available
        base, weight_charge, additional, discount, total, _, ins_charge = calculate_order_amount(
            order.weight, None, state=order.receiver_state, client_id=order.client_id, insured_amount=order.insured_amount
        )
        order.base_amount = base
        order.weight_charges = weight_charge
        order.additional_charges = additional
        order.discount = discount
        order.insurance_charge = ins_charge
        order.total_amount = total
        
        order.generate_tracking_link()
        
        db.session.add(order)
        db.session.commit()
        
        # Add initial tracking
        tracking = TrackingUpdate(
            order_id=order.id,
            status='Order Created',
            description='Client order has been created',
            updated_by=current_user.id
        )
        db.session.add(tracking)
        db.session.commit()
        
        create_link = request.form.get('create_customer_link')
        if create_link:
            order.generate_customer_form_link()
            db.session.commit()
            flash(f'Order created! Customer form link: {url_for("customer_form", token=order.customer_form_link, _external=True)}', 'success')
        else:
            flash(f'Order created successfully! Tracking Number: {receipt_number}', 'success')
        
        return redirect(url_for('order_details', id=order.id))
    
    return render_template('client_order.html', clients=clients)


@app.route('/order/<int:id>')
@login_required
@staff_required
def order_details(id):
    order = Order.query.get_or_404(id)
    # Redirect to the new view_order template if preferred, or keep order_details
    tracking_updates = TrackingUpdate.query.filter_by(order_id=id).order_by(TrackingUpdate.created_at.desc()).all()
    delivery_personnel = User.query.filter_by(role='delivery', is_active=True).all()
    
    # Generate QR code for tracking
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    tracking_url = url_for('tracking', receipt=order.receipt_number, _external=True)
    qr.add_data(tracking_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    qr_img.save(buffer, format='PNG')
    qr_code = base64.b64encode(buffer.getvalue()).decode()
    
    return render_template('view_order.html', 
                         order=order, 
                         tracking_updates=tracking_updates,
                         delivery_personnel=delivery_personnel,
                         qr_code=qr_code)


@app.route('/order/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@staff_required
def edit_order(id):
    order = Order.query.get_or_404(id)
    clients = Client.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        new_receipt_number = request.form.get('receipt_number')
        
        # Check if receipt number is being changed and if it already exists
        if new_receipt_number != order.receipt_number:
            existing_order = Order.query.filter_by(receipt_number=new_receipt_number).first()
            if existing_order:
                flash(f'Tracking number {new_receipt_number} already exists in another order! Please use a different number.', 'danger')
                return redirect(url_for('edit_order', id=id))
        
        # Validate Pincode
        receiver_pincode = request.form.get('receiver_pincode')
        if not validate_pincode(receiver_pincode):
            flash('Invalid Pincode. It must be exactly 6 digits.', 'danger')
            return redirect(url_for('edit_order', id=id))

        order.receipt_number = new_receipt_number
        order.receipt_mode = request.form.get('receipt_mode')
        order.customer_name = request.form.get('customer_name')
        order.customer_phone = request.form.get('customer_phone')
        order.customer_email = request.form.get('customer_email')
        order.customer_address = request.form.get('customer_address')
        order.receiver_name = request.form.get('receiver_name')
        order.receiver_phone = request.form.get('receiver_phone')
        order.receiver_address = request.form.get('receiver_address')
        order.receiver_city = request.form.get('receiver_city')
        order.receiver_state = request.form.get('receiver_state')
        order.receiver_pincode = request.form.get('receiver_pincode')
        order.package_description = request.form.get('package_description')
        order.weight = float(request.form.get('weight') or 0)
        order.number_of_boxes = int(request.form.get('number_of_boxes') or 1)
        order.special_instructions = request.form.get('special_instructions')
        order.status = request.form.get('status')
        order.payment_status = request.form.get('payment_status')
        order.payment_mode = request.form.get('payment_mode')
        order.internal_notes = request.form.get('internal_notes')
        
        # Recalculate amounts
        if order.weight:
            base, weight_charge, additional, discount, total, _ = calculate_order_amount(
                order.weight, None, state=order.receiver_state, client_id=order.client_id
            )
            # Only update if we actually got a calculated total (from state pricing)
            if total > 0:
                order.base_amount = base
                order.weight_charges = weight_charge
                order.additional_charges = additional
                order.discount = discount
                order.total_amount = total
        
        db.session.commit()
        flash('Order updated successfully!', 'success')
        return redirect(url_for('order_details', id=order.id))
    
    return render_template('edit_order.html', order=order, clients=clients)


@app.route('/order/<int:id>/update-status', methods=['GET', 'POST'])
@login_required
@staff_required
def update_order_status(id):
    order = Order.query.get_or_404(id)
    
    # Define valid transitions
    valid_transitions = {}
    
    if order.status == 'pending':
        valid_transitions = {
            'confirmed': 'Confirmed',
            'in_transit': 'In Transit (On the way)'
        }
    elif order.status == 'confirmed':
         valid_transitions = {
            'in_transit': 'In Transit (On the way)'
        }
    elif order.status == 'in_transit':
         valid_transitions = {
            'at_destination': 'At Destination (Arrived at City)'
        }
    elif order.status == 'at_destination':
         valid_transitions = {
            'out_for_delivery': 'Out for Delivery',
            'delivered': 'Delivered (Successfully Handed Over)',
            'rto': 'RTO (Returning to Origin)'
        }
    elif order.status == 'out_for_delivery':
         valid_transitions = {
            'delivered': 'Delivered (Successfully Handed Over)',
            'rto': 'RTO (Returning to Origin)'
        }
    
    if request.method == 'GET':
        return render_template('update_status.html', order=order, valid_transitions=valid_transitions)
        
    new_status = request.form.get('status')
    
    # Optional: Server-side validation of transition
    # if new_status not in valid_transitions and current_user.role != 'admin':
    #     flash('Invalid status transition.', 'error')
    #     return redirect(url_for('update_order_status', id=id))

    location = request.form.get('location')
    description = request.form.get('description')
    
    order.status = new_status
    if new_status == 'delivered':
        order.delivered_at = datetime.utcnow()
    
    tracking = TrackingUpdate(
        order_id=order.id,
        status=new_status.replace('_', ' ').title(),
        location=location,
        description=description,
        updated_by=current_user.id
    )
    db.session.add(tracking)
    db.session.commit()
    
    flash('Order status updated successfully!', 'success')
    return redirect(url_for('order_details', id=order.id))


@app.route('/order/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_order(id):
    order = Order.query.get_or_404(id)
    db.session.delete(order)
    db.session.commit()
    flash('Order deleted successfully.', 'success')
    return redirect(url_for('orders'))


@app.route('/order/<int:id>/reopen', methods=['POST'])
@login_required
@admin_required
def reopen_order(id):
    order = Order.query.get_or_404(id)
    order.status = 'in_transit' # Reset to in_transit so it can be moved again
    order.delivered_at = None
    
    tracking = TrackingUpdate(
        order_id=order.id,
        status='Re-opened',
        description='Order re-opened by Admin. Status reset to In Transit.',
        updated_by=current_user.id
    )
    db.session.add(tracking)
    db.session.commit()
    
    flash('Order re-opened successfully.', 'success')
    return redirect(url_for('order_details', id=order.id))


@app.route('/order/<int:id>/generate-link', methods=['POST'])
@login_required
@staff_required
def generate_customer_link(id):
    order = Order.query.get_or_404(id)
    
    if not order.customer_form_link:
        order.generate_customer_form_link()
        db.session.commit()
    
    link = url_for('customer_form', token=order.customer_form_link, _external=True)
    
    return jsonify({
        'success': True,
        'link': link
    })





# ============== CUSTOMER FORM (PUBLIC) ==============

@app.route('/form/<token>', methods=['GET', 'POST'])
def customer_form(token):
    order = Order.query.filter_by(customer_form_link=token).first_or_404()
    
    if request.method == 'POST':
        order.receiver_name = request.form.get('receiver_name') or order.receiver_name
        order.receiver_phone = request.form.get('receiver_phone') or order.receiver_phone
        order.receiver_address = request.form.get('receiver_address') or order.receiver_address
        order.receiver_city = request.form.get('receiver_city') or order.receiver_city
        order.receiver_state = request.form.get('receiver_state') or order.receiver_state
        
        pincode = request.form.get('receiver_pincode')
        if pincode and not validate_pincode(pincode):
            flash('Invalid Pincode. It must be exactly 6 digits.', 'error')
            return redirect(url_for('customer_form', token=token))
            
        order.receiver_pincode = pincode or order.receiver_pincode
        order.package_description = request.form.get('package_description') or order.package_description
        order.special_instructions = request.form.get('special_instructions') or order.special_instructions
        order.customer_form_completed = True
        
        db.session.commit()
        flash('Thank you! Your details have been submitted successfully.', 'success')
        return redirect(url_for('tracking', receipt=order.receipt_number))
    
    return render_template('customer_form.html', order=order)


# ============== TRACKING (PUBLIC) ==============

@app.route('/tracking')
def tracking():
    receipt = request.args.get('receipt', '')
    order = None
    tracking_updates = []
    
    if receipt:
        order = Order.query.filter_by(receipt_number=receipt).first()
        if order:
            tracking_updates = TrackingUpdate.query.filter_by(order_id=order.id).order_by(TrackingUpdate.created_at.desc()).all()
    
    return render_template('tracking.html', order=order, tracking_updates=tracking_updates, receipt=receipt)


@app.route('/track/<link>')
def track_by_link(link):
    order = Order.query.filter_by(tracking_link=link).first_or_404()
    tracking_updates = TrackingUpdate.query.filter_by(order_id=order.id).order_by(TrackingUpdate.created_at.desc()).all()
    return render_template('tracking.html', order=order, tracking_updates=tracking_updates, receipt=order.receipt_number)


# ============== RECEIPT SETTINGS ==============

@app.route('/receipt-settings', methods=['GET', 'POST'])
@login_required
@admin_required
def receipt_settings():
    setting = ReceiptSetting.query.filter_by(is_active=True).first()
    
    if request.method == 'POST':
        if not setting:
            setting = ReceiptSetting()
        
        setting.base_number = request.form.get('base_number')
        setting.range_end = request.form.get('range_end')
        setting.prefix = request.form.get('prefix')
        setting.suffix = request.form.get('suffix')
        setting.updated_by = current_user.id
        
        if request.form.get('reset_sequence') == 'on':
            setting.current_sequence = 0
        
        db.session.add(setting)
        db.session.commit()
        flash('Tracking settings updated successfully!', 'success')
        return redirect(url_for('receipt_settings'))
    
    return render_template('receipt_settings.html', setting=setting)


# ============== INSURANCE SETTINGS ==============

@app.route('/insurance-settings', methods=['GET', 'POST'])
@login_required
@admin_required
def insurance_settings():
    setting = SystemSettings.query.filter_by(key='insurance_percentage').first()
    
    if request.method == 'POST':
        percentage = request.form.get('insurance_percentage', '0')
        if not setting:
            setting = SystemSettings(key='insurance_percentage', value=percentage, description='Percentage for insurance calculation')
            db.session.add(setting)
        else:
            setting.value = percentage
        
        db.session.commit()
        flash('Insurance settings updated successfully!', 'success')
        return redirect(url_for('insurance_settings'))
    
    return render_template('insurance_settings.html', setting=setting)


# ============== BILLING PATTERNS ==============

# Billing Pattern routes removed



# ============== EXCEL UPLOAD ==============

@app.route('/excel-upload', methods=['GET', 'POST'])
@login_required
@staff_required
def excel_upload():
    uploads = ExcelUpload.query.order_by(ExcelUpload.created_at.desc()).limit(20).all()
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected.', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                df = pd.read_excel(filepath)
                
                upload = ExcelUpload(
                    filename=filename,
                    uploaded_by=current_user.id,
                    records_processed=len(df)
                )
                db.session.add(upload)
                db.session.commit()
                
                # Robust column mapping
                def get_val(row, aliases):
                    for alias in aliases:
                        if alias in row:
                            val = row[alias]
                            if pd.isna(val): return None
                            return val
                    return None

                matched_count = 0
                for index, row in df.iterrows():
                    # Aliases for Receipt Number (Prioritize 'Awb No')
                    receipt_number = get_val(row, ['Awb No', 'receipt_number', 'Receipt Number', 'RECEIPT_NUMBER', 'AWB', 'Consignment No'])
                    if receipt_number:
                        receipt_number = str(receipt_number).strip()
                    
                    # Aliases for Weight (Prioritize 'Weight')
                    weight = get_val(row, ['Weight', 'Weight (kg)', 'weight', 'WEIGHT', 'Actual Weight'])
                    
                    # Aliases for Amount (Prioritize 'GR Amount' as cost)
                    amount = get_val(row, ['GR Amount', 'Amount', 'amount', 'AMOUNT', 'Total Amount', 'Net Amount'])
                    
                    # Handle ValueIf and Destination as Additional Info
                    savings = get_val(row, ['ValueIf', 'valueif', 'Savings'])
                    dest = get_val(row, ['Destination', 'destination', 'City', 'State'])
                    
                    info_parts = []
                    if dest: info_parts.append(f"Dest/State: {dest}")
                    if savings: info_parts.append(f"Savings: {savings}")
                    info = " | ".join(info_parts) if info_parts else None

                    if receipt_number:
                        excel_data = ExcelData(
                            receipt_number=receipt_number,
                            weight=float(weight) if weight is not None else None,
                            amount=float(amount) if amount is not None else None,
                            additional_info=info,
                            upload_id=upload.id
                        )
                        db.session.add(excel_data)
                        
                        # Match with existing orders
                        order = Order.query.filter_by(receipt_number=receipt_number).first()
                        if order:
                            order.excel_weight = float(weight) if weight is not None else None
                            order.excel_amount = float(amount) if amount is not None else None
                            order.excel_verified = True
                            excel_data.matched = True
                            matched_count += 1
                
                upload.records_matched = matched_count
                db.session.commit()
                
                flash(f'File uploaded successfully! Processed: {len(df)}, Matched: {matched_count}', 'success')
                
            except Exception as e:
                flash(f'Error processing file: {str(e)}', 'error')
        else:
            flash('Invalid file type. Please upload Excel files only.', 'error')
        
        return redirect(url_for('excel_upload'))
    
    return render_template('excel_upload.html', uploads=uploads)


@app.route('/excel-data/<int:upload_id>')
@login_required
@staff_required
def view_excel_data(upload_id):
    upload = ExcelUpload.query.get_or_404(upload_id)
    data = ExcelData.query.filter_by(upload_id=upload_id).all()
    return render_template('excel_data.html', upload=upload, data=data)


@app.route('/verify-excel', methods=['POST'])
@login_required
@staff_required
def verify_excel():
    order_id = request.form.get('order_id')
    order = Order.query.get_or_404(order_id)
    
    excel_data = ExcelData.query.filter_by(receipt_number=order.receipt_number, matched=False).first()
    
    if excel_data:
        order.excel_weight = excel_data.weight
        order.excel_amount = excel_data.amount
        order.excel_verified = True
        excel_data.matched = True
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Order verified with Excel data'})
    
    return jsonify({'success': False, 'message': 'No matching Excel data found'})


# ============== MOBILE API ENDPOINTS ==============

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """Mobile login endpoint - returns JWT token"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        # Find user by username or email
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is deactivated'}), 403
        
        # Create JWT token
        access_token = create_access_token(identity=user.id)
        
        return jsonify({
            'access_token': access_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'phone': user.phone,
                'branch_id': user.branch_id
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/request-otp', methods=['POST'])
def api_request_otp():
    """Request OTP for password reset"""
    try:
        data = request.get_json()
        identifier = data.get('email') or data.get('phone')
        
        if not identifier:
            return jsonify({'error': 'Email or phone required'}), 400
        
        # Find user
        user = User.query.filter(
            (User.email == identifier) | (User.phone == identifier)
        ).first()
        
        if not user:
            # Don't reveal if user exists
            return jsonify({'message': 'If account exists, OTP has been sent'}), 200
        
        # Generate 6-digit OTP
        otp_code = str(random.randint(100000, 999999))
        user.otp_code = otp_code
        user.otp_expiry = datetime.utcnow() + timedelta(minutes=15)
        db.session.commit()
        
        # TODO: Send OTP via email/SMS
        # For now, just log it (in production, integrate with email/SMS service)
        print(f"OTP for {user.username}: {otp_code}")
        
        return jsonify({
            'message': 'OTP sent successfully',
            'debug_otp': otp_code  # Remove this in production!
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/verify-otp', methods=['POST'])
def api_verify_otp():
    """Verify OTP and return temporary token"""
    try:
        data = request.get_json()
        identifier = data.get('email') or data.get('phone')
        otp_code = data.get('otp_code')
        
        if not identifier or not otp_code:
            return jsonify({'error': 'Email/phone and OTP required'}), 400
        
        user = User.query.filter(
            (User.email == identifier) | (User.phone == identifier)
        ).first()
        
        if not user or user.otp_code != otp_code:
            return jsonify({'error': 'Invalid OTP'}), 401
        
        if not user.otp_expiry or user.otp_expiry < datetime.utcnow():
            return jsonify({'error': 'OTP expired'}), 401
        
        # Create temporary token for password reset (short expiry)
        temp_token = create_access_token(identity=user.id, expires_delta=timedelta(minutes=10))
        
        return jsonify({
            'message': 'OTP verified',
            'reset_token': temp_token
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/reset-password', methods=['POST'])
@jwt_required()
def api_reset_password():
    """Reset password with verified OTP token"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        new_password = data.get('new_password')
        
        if not new_password or len(new_password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        user.set_password(new_password)
        user.otp_code = None
        user.otp_expiry = None
        db.session.commit()
        
        return jsonify({'message': 'Password reset successful'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/orders', methods=['GET', 'POST'])
@jwt_required()
def api_orders():
    """GET: List orders, POST: Create new order"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if request.method == 'GET':
        # List orders based on user role
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            status_filter = request.args.get('status')
            
            if user.role in ['admin', 'staff', 'delivery']:
                query = Order.query
            else:
                # Customer role - filter by phone/email
                query = Order.query.filter(
                    (Order.customer_phone == user.phone) | 
                    (Order.customer_email == user.email)
                )
            
            if status_filter:
                query = query.filter_by(status=status_filter)
            
            orders = query.order_by(Order.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            return jsonify({
                'orders': [{
                    'id': o.id,
                    'receipt_number': o.receipt_number,
                    'customer_name': o.customer_name,
                    'receiver_name': o.receiver_name,
                    'receiver_city': o.receiver_city,
                    'receiver_state': o.receiver_state,
                    'status': o.status,
                    'payment_status': o.payment_status,
                    'total_amount': o.total_amount,
                    'verified': o.verified,
                    'created_at': o.created_at.isoformat(),
                    'created_via': o.created_via
                } for o in orders.items],
                'total': orders.total,
                'pages': orders.pages,
                'current_page': orders.page
            }), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'POST':
        # Create new order from mobile
        try:
            data = request.get_json()
            
            # Validate required fields
            required = ['customer_name', 'customer_phone', 'receiver_name', 
                       'receiver_address', 'receiver_city', 'receiver_state', 
                       'receiver_pincode', 'package_description', 'weight']
            
            for field in required:
                if field not in data or not data[field]:
                    return jsonify({'error': f'{field} is required'}), 400
            
            # Generate receipt number
            receipt_number = generate_receipt_number()
            
            # Create order
            order = Order(
                receipt_number=receipt_number,
                order_type='walkin',  # Mobile orders are walk-in type
                receipt_mode=data.get('receipt_mode', 'standard'),
                customer_name=data['customer_name'],
                customer_phone=data['customer_phone'],
                customer_email=data.get('customer_email', user.email),
                customer_address=data.get('customer_address', ''),
                receiver_name=data['receiver_name'],
                receiver_phone=data.get('receiver_phone', ''),
                receiver_address=data['receiver_address'],
                receiver_city=data['receiver_city'],
                receiver_state=data['receiver_state'],
                receiver_pincode=data['receiver_pincode'],
                package_description=data['package_description'],
                weight=float(data['weight']),
                number_of_boxes=int(data.get('number_of_boxes', 1)),
                special_instructions=data.get('special_instructions', ''),
                created_by=user_id,
                status='pending',
                verified=False,  # Needs verification
                created_via='mobile'
            )
            
            # Calculate amounts
            if order.weight:
                base, weight_charge, additional, discount, total, _ = calculate_order_amount(
                    order.weight, state=order.receiver_state
                )
                order.base_amount = base
                order.weight_charges = weight_charge
                order.additional_charges = additional
                order.discount = discount
                order.total_amount = total
            
            order.generate_tracking_link()
            db.session.add(order)
            db.session.commit()
            
            # Add tracking update
            tracking = TrackingUpdate(
                order_id=order.id,
                status='Order Created',
                description='Order created via mobile app',
                updated_by=user_id
            )
            db.session.add(tracking)
            
            # Create notifications for all staff and admin
            staff_users = User.query.filter(
                User.role.in_(['admin', 'staff']),
                User.is_active == True
            ).all()
            
            for staff in staff_users:
                notification = Notification(
                    user_id=staff.id,
                    order_id=order.id,
                    message=f"New order #{order.receipt_number} created by {order.customer_name}",
                    notification_type='new_order'
                )
                db.session.add(notification)
            
            db.session.commit()
            
            return jsonify({
                'message': 'Order created successfully',
                'order': {
                    'id': order.id,
                    'receipt_number': order.receipt_number,
                    'status': order.status,
                    'total_amount': order.total_amount,
                    'verified': order.verified
                }
            }), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500


@app.route('/api/orders/<int:order_id>', methods=['GET'])
@jwt_required()
def api_order_details(order_id):
    """Get detailed order information"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Check access rights
        if user.role == 'customer':
            if order.customer_phone != user.phone and order.customer_email != user.email:
                return jsonify({'error': 'Access denied'}), 403
        
        tracking_updates = TrackingUpdate.query.filter_by(order_id=order_id).order_by(
            TrackingUpdate.created_at.desc()
        ).all()
        
        return jsonify({
            'order': {
                'id': order.id,
                'receipt_number': order.receipt_number,
                'order_type': order.order_type,
                'status': order.status,
                'payment_status': order.payment_status,
                'customer_name': order.customer_name,
                'customer_phone': order.customer_phone,
                'customer_email': order.customer_email,
                'receiver_name': order.receiver_name,
                'receiver_phone': order.receiver_phone,
                'receiver_address': order.receiver_address,
                'receiver_city': order.receiver_city,
                'receiver_state': order.receiver_state,
                'receiver_pincode': order.receiver_pincode,
                'package_description': order.package_description,
                'weight': order.weight,
                'number_of_boxes': order.number_of_boxes,
                'total_amount': order.total_amount,
                'verified': order.verified,
                'created_via': order.created_via,
                'created_at': order.created_at.isoformat(),
                'tracking_updates': [{
                    'status': t.status,
                    'description': t.description,
                    'location': t.location,
                    'created_at': t.created_at.isoformat()
                } for t in tracking_updates]
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/orders/pending-verification', methods=['GET'])
@jwt_required()
def api_pending_verification():
    """Get orders pending verification (staff/admin only)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if user.role not in ['admin', 'staff']:
            return jsonify({'error': 'Access denied'}), 403
        
        orders = Order.query.filter_by(verified=False).order_by(Order.created_at.desc()).all()
        
        return jsonify({
            'orders': [{
                'id': o.id,
                'receipt_number': o.receipt_number,
                'customer_name': o.customer_name,
                'customer_phone': o.customer_phone,
                'receiver_city': o.receiver_city,
                'receiver_state': o.receiver_state,
                'total_amount': o.total_amount,
                'created_at': o.created_at.isoformat(),
                'created_via': o.created_via
            } for o in orders]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/orders/<int:order_id>/verify', methods=['POST'])
@jwt_required()
def api_verify_order(order_id):
    """Verify an order (staff/admin only)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if user.role not in ['admin', 'staff']:
            return jsonify({'error': 'Access denied'}), 403
        
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        order.verified = True
        
        # Add tracking update
        tracking = TrackingUpdate(
            order_id=order.id,
            status='Order Verified',
            description=f'Order verified by {user.username}',
            updated_by=user_id
        )
        db.session.add(tracking)
        
        # Notify customer
        if order.created_by:
            customer = User.query.get(order.created_by)
            if customer:
                notification = Notification(
                    user_id=customer.id,
                    order_id=order.id,
                    message=f"Your order #{order.receipt_number} has been verified",
                    notification_type='order_verified'
                )
                db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({'message': 'Order verified successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/billing/dues', methods=['GET'])
@jwt_required()
def api_billing_dues():
    """Get outstanding bills for customer"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Get unpaid orders for this customer
        orders = Order.query.filter(
            (Order.customer_phone == user.phone) | (Order.customer_email == user.email),
            Order.payment_status.in_(['unpaid', 'partial'])
        ).all()
        
        total_due = sum(o.total_amount or 0 for o in orders)
        
        return jsonify({
            'total_due': total_due,
            'orders': [{
                'id': o.id,
                'receipt_number': o.receipt_number,
                'total_amount': o.total_amount,
                'payment_status': o.payment_status,
                'status': o.status,
                'created_at': o.created_at.isoformat()
            } for o in orders]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/billing/request-clearance', methods=['POST'])
@jwt_required()
def api_request_clearance():
    """Request billing clearance from admin"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        data = request.get_json()
        order_id = data.get('order_id')
        notes = data.get('notes', '')
        
        if not order_id:
            return jsonify({'error': 'Order ID required'}), 400
        
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Add notes to order
        order.internal_notes = f"{order.internal_notes or ''}\n[Clearance Request] {notes}"
        
        # Notify admins
        admins = User.query.filter_by(role='admin', is_active=True).all()
        for admin in admins:
            notification = Notification(
                user_id=admin.id,
                order_id=order.id,
                message=f"Billing clearance requested for order #{order.receipt_number}",
                notification_type='billing_request'
            )
            db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({'message': 'Clearance request sent to admin'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/notifications', methods=['GET'])
@jwt_required()
def api_notifications():
    """Get notifications for authenticated user"""
    try:
        user_id = get_jwt_identity()
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        query = Notification.query.filter_by(user_id=user_id)
        
        if unread_only:
            query = query.filter_by(is_read=False)
        
        notifications = query.order_by(Notification.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        unread_count = Notification.query.filter_by(user_id=user_id, is_read=False).count()
        
        return jsonify({
            'notifications': [{
                'id': n.id,
                'message': n.message,
                'notification_type': n.notification_type,
                'order_id': n.order_id,
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat()
            } for n in notifications.items],
            'unread_count': unread_count,
            'total': notifications.total,
            'pages': notifications.pages,
            'current_page': notifications.page
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/notifications/<int:notification_id>/mark-read', methods=['POST'])
@jwt_required()
def api_mark_notification_read(notification_id):
    """Mark notification as read"""
    try:
        user_id = get_jwt_identity()
        
        notification = Notification.query.get(notification_id)
        if not notification:
            return jsonify({'error': 'Notification not found'}), 404
        
        if notification.user_id != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        notification.is_read = True
        db.session.commit()
        
        return jsonify({'message': 'Notification marked as read'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============== PRINT LABELS ==============

@app.route('/order/<int:id>/print-label')
@login_required
@staff_required
def print_label(id):
    order = Order.query.get_or_404(id)
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    tracking_url = url_for('tracking', receipt=order.receipt_number, _external=True)
    qr.add_data(tracking_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    qr_img.save(buffer, format='PNG')
    qr_code = base64.b64encode(buffer.getvalue()).decode()
    
    return render_template('print_label.html', order=order, qr_code=qr_code)


@app.route('/order/<int:id>/print-all-labels')
@login_required
@staff_required
def print_all_labels(id):
    order = Order.query.get_or_404(id)
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    tracking_url = url_for('tracking', receipt=order.receipt_number, _external=True)
    qr.add_data(tracking_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    qr_img.save(buffer, format='PNG')
    qr_code = base64.b64encode(buffer.getvalue()).decode()
    
    labels = []
    for i in range(order.number_of_boxes):
        labels.append({
            'box_number': i + 1,
            'total_boxes': order.number_of_boxes
        })
    
    return render_template('print_all_labels.html', order=order, qr_code=qr_code, labels=labels)


# ============== API ENDPOINTS ==============

@app.route('/api/orders/search')
@login_required
def api_search_orders():
    query = request.args.get('q', '')
    orders = Order.query.filter(
        (Order.receipt_number.contains(query)) |
        (Order.customer_name.contains(query)) |
        (Order.customer_phone.contains(query))
    ).limit(10).all()
    
    return jsonify([{
        'id': o.id,
        'receipt_number': o.receipt_number,
        'customer_name': o.customer_name,
        'status': o.status
    } for o in orders])


@app.route('/api/client/<int:id>')
@login_required
def api_get_client(id):
    client = Client.query.get_or_404(id)
    return jsonify({
        'id': client.id,
        'name': client.name,
        'company_name': client.company_name,
        'phone': client.phone,
        'email': client.email,
        'address': client.address,
        'billing_pattern_id': client.billing_pattern_id
    })


@app.route('/api/calculate-amount', methods=['POST'])
@login_required
def api_calculate_amount():
    weight = float(request.json.get('weight', 0))
    state = request.json.get('state')
    client_id = request.json.get('client_id')
    insured_amount = float(request.json.get('insured_amount', 0))
    
    if weight or insured_amount:
        base, weight_charge, additional, discount, total, rate_type, ins_charge = calculate_order_amount(
            weight, None, state=state, client_id=client_id, insured_amount=insured_amount
        )
        return jsonify({
            'base_amount': base,
            'weight_charges': weight_charge,
            'additional_charges': additional,
            'discount': discount,
            'insurance_charge': ins_charge,
            'total_amount': total,
            'rate_type': rate_type
        })
    
    return jsonify({'error': 'Invalid input'}), 400


# ============== REPORTS ==============

@app.route('/reports')
@login_required
@admin_required
def reports():
    # Get date range
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = Order.query
    
    if start_date:
        query = query.filter(Order.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(Order.created_at <= datetime.strptime(end_date, '%Y-%m-%d'))
    
    orders = query.all()
    
    # Calculate statistics
    total_orders = len(orders)
    total_revenue = sum(o.total_amount or 0 for o in orders)
    total_weight = sum(o.weight or 0 for o in orders)
    
    status_breakdown = {}
    for order in orders:
        status_breakdown[order.status] = status_breakdown.get(order.status, 0) + 1
    
    return render_template('reports.html',
                         orders=orders,
                         total_orders=total_orders,
                         total_revenue=total_revenue,
                         total_weight=total_weight,
                         status_breakdown=status_breakdown,
                         start_date=start_date,
                         end_date=end_date)


@app.route('/reports/export')
@login_required
@admin_required
def export_report():
    orders = Order.query.all()
    
    data = []
    for o in orders:
        data.append({
            'Receipt Number': o.receipt_number,
            'Order Type': o.order_type,
            'Customer Name': o.customer_name,
            'Customer Phone': o.customer_phone,
            'Receiver Name': o.receiver_name,
            'Receiver Address': o.receiver_address,
            'Weight': o.weight,
            'Total Amount': o.total_amount,
            'Status': o.status,
            'Created At': o.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    df = pd.DataFrame(data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'orders_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )


# ============== PRICING ROUTES ==============

@app.route('/default-prices')
@login_required
@admin_required
def default_prices():
    prices = DefaultStatePrice.query.all()
    return render_template('default_prices.html', prices=prices)


@app.route('/default-prices/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_default_price():
    if request.method == 'POST':
        state = request.form.get('state')
        if DefaultStatePrice.query.filter_by(state=state).first():
            flash('Price for this state already exists.', 'error')
            return redirect(url_for('add_default_price'))
            
        price = DefaultStatePrice(
            state=state,
            price_100gm=float(request.form.get('price_100gm', 0)),
            price_250gm=float(request.form.get('price_250gm', 0)),
            price_500gm=float(request.form.get('price_500gm', 0)),
            price_750gm=float(request.form.get('price_750gm', 0)),
            price_1kg=float(request.form.get('price_1kg', 0)),
            price_2kg=float(request.form.get('price_2kg', 0)),
            price_3kg=float(request.form.get('price_3kg', 0))
        )
        db.session.add(price)
        db.session.commit()
        flash(f'Prices for {state} added successfully!', 'success')
        return redirect(url_for('default_prices'))
        
    return render_template('add_default_price.html')


@app.route('/default-prices/edit/<int:price_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_default_price(price_id):
    price = DefaultStatePrice.query.get_or_404(price_id)
    
    if request.method == 'POST':
        price.state = request.form.get('state')
        price.price_100gm = float(request.form.get('price_100gm', 0))
        price.price_250gm = float(request.form.get('price_250gm', 0))
        price.price_500gm = float(request.form.get('price_500gm', 0))
        price.price_750gm = float(request.form.get('price_750gm', 0))
        price.price_1kg = float(request.form.get('price_1kg', 0))
        price.price_2kg = float(request.form.get('price_2kg', 0))
        price.price_3kg = float(request.form.get('price_3kg', 0))
        
        db.session.commit()
        flash(f'Prices for {price.state} updated successfully!', 'success')
        return redirect(url_for('default_prices'))
        
    return render_template('edit_default_price.html', price=price)


@app.route('/default-prices/delete/<int:price_id>', methods=['POST'])
@login_required
@admin_required
def delete_default_price(price_id):
    price = DefaultStatePrice.query.get_or_404(price_id)
    state_name = price.state
    db.session.delete(price)
    db.session.commit()
    flash(f'Pricing for {state_name} deleted.', 'success')
    return redirect(url_for('default_prices'))


@app.route('/client-prices/<int:client_id>')
@login_required
@staff_required
def view_client_prices(client_id):
    client = Client.query.get_or_404(client_id)
    client_state_prices = ClientStatePrice.query.filter_by(client_id=client_id).all()
    all_states = DefaultStatePrice.query.all()
    
    # Enrich all_states with custom prices if they exist
    enriched_states = []
    for s in all_states:
        custom = ClientStatePrice.query.filter_by(client_id=client_id, state=s.state).first()
        enriched_states.append({
            'state': s.state,
            'price_100gm': s.price_100gm,
            'price_250gm': s.price_250gm,
            'price_500gm': s.price_500gm,
            'price_750gm': s.price_750gm,
            'price_1kg': s.price_1kg,
            'price_2kg': s.price_2kg,
            'price_3kg': s.price_3kg,
            'has_custom_price': 1 if custom else 0,
            'custom_price_100gm': custom.price_100gm if custom else 0,
            'custom_price_250gm': custom.price_250gm if custom else 0,
            'custom_price_500gm': custom.price_500gm if custom else 0,
            'custom_price_750gm': custom.price_750gm if custom else 0,
            'custom_price_1kg': custom.price_1kg if custom else 0,
            'custom_price_2kg': custom.price_2kg if custom else 0,
            'custom_price_3kg': custom.price_3kg if custom else 0
        })
        
    return render_template('client_state_prices.html', 
                         client=client, 
                         client_state_prices=client_state_prices,
                         all_states=enriched_states)


@app.route('/client-prices/<int:client_id>/set', methods=['GET', 'POST'])
@login_required
@staff_required
def set_client_prices(client_id):
    client = Client.query.get_or_404(client_id)
    selected_state = request.args.get('state')
    
    if request.method == 'POST':
        state = request.form.get('state')
        if not state:
            flash('State is required.', 'error')
            return redirect(url_for('set_client_prices', client_id=client_id))
            
        custom = ClientStatePrice.query.filter_by(client_id=client_id, state=state).first()
        if not custom:
            custom = ClientStatePrice(client_id=client_id, state=state)
            db.session.add(custom)
            
        custom.price_100gm = float(request.form.get('price_100gm', 0))
        custom.price_250gm = float(request.form.get('price_250gm', 0))
        custom.price_500gm = float(request.form.get('price_500gm', 0))
        custom.price_750gm = float(request.form.get('price_750gm', 0))
        custom.price_1kg = float(request.form.get('price_1kg', 0))
        custom.price_2kg = float(request.form.get('price_2kg', 0))
        custom.price_3kg = float(request.form.get('price_3kg', 0))
        
        db.session.commit()
        flash(f'Custom prices for {state} updated successfully!', 'success')
        return redirect(url_for('view_client_prices', client_id=client_id))
        
    all_states = [s.state for s in DefaultStatePrice.query.all()]
    
    # Pre-fill data if state is selected
    existing_price = None
    if selected_state:
        existing_price = ClientStatePrice.query.filter_by(client_id=client_id, state=selected_state).first()
        
    return render_template('set_client_prices.html', 
                         client=client, 
                         states=all_states, 
                         selected_state=selected_state,
                         existing_price=existing_price)


@app.route('/client-prices/<int:client_id>/delete/<int:price_id>', methods=['POST'])
@login_required
@staff_required
def delete_client_price(client_id, price_id):
    price = ClientStatePrice.query.get_or_404(price_id)
    if price.client_id != client_id:
        flash('Unauthorized action.', 'error')
        return redirect(url_for('view_client_prices', client_id=client_id))
        
    state_name = price.state
    db.session.delete(price)
    db.session.commit()
    flash(f'Custom pricing for {state_name} removed.', 'success')
    return redirect(url_for('view_client_prices', client_id=client_id))


# ============== ADVANCED REPORTS ==============

@app.route('/detailed-reports')
@login_required
@admin_required
def detailed_reports():
    return render_template('detailed_reports.html')


@app.route('/due-amount-report')
@login_required
@admin_required
def due_amount_report():
    return render_template('due_amount_report.html')


@app.route('/public-prices')
def public_prices():
    prices = DefaultStatePrice.query.all()
    weight_categories = [
        ('100gm', 'price_100gm'),
        ('250gm', 'price_250gm'),
        ('500gm', 'price_500gm'),
        ('750gm', 'price_750gm'),
        ('1kg', 'price_1kg'),
        ('2kg', 'price_2kg'),
        ('3kg', 'price_3kg')
    ]
    return render_template('public_prices.html', prices=prices, weight_categories=weight_categories)


@app.route('/bill/<int:order_id>')
@login_required
@manager_required
def view_bill(order_id):
    order = Order.query.get_or_404(order_id)
    # Map order to bill-like object for the template
    bill = {
        'id': order.id,
        'bill_number': order.receipt_number,
        'bill_date': order.created_at.strftime('%Y-%m-%d'),
        'name': order.customer_name,
        'address': order.customer_address or 'N/A',
        'city': order.receiver_city or 'N/A',
        'state': order.receiver_state or 'N/A',
        'pincode': order.receiver_pincode or 'N/A',
        'phone': order.customer_phone,
        'email': order.customer_email or 'N/A',
        'gst_number': order.client.gst_number if order.client else 'N/A',
        'client_id': order.client_id or 'Walk-in',
        'status': order.payment_status.title() if order.payment_status else 'Pending',
        'weight_category': order.weight_category or f"{order.weight}kg",
        'quantity': order.number_of_boxes,
        'price_per_unit': order.total_amount / order.number_of_boxes if order.number_of_boxes > 0 else order.total_amount,
        'total_amount': order.total_amount,
        'notes': order.special_instructions,
        'created_at': order.created_at.isoformat()
    }
    return render_template('view_bill.html', bill=bill)


@app.route('/upload-confirmation', methods=['GET', 'POST'])
@login_required
@staff_required
def upload_confirmation():
    if request.method == 'POST':
        if 'excel_file' not in request.files:
            flash('No file selected.', 'error')
            return redirect(request.url)
        
        file = request.files['excel_file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                df = pd.read_excel(filepath)
                # Logic to process confirmation data
                # Matching AWB No with consignment_number or receipt_number
                flash(f'Successfully processed {len(df)} records from {filename}', 'success')
                return redirect(url_for('orders'))
            except Exception as e:
                flash(f'Error processing file: {str(e)}', 'error')
        else:
            flash('Invalid file type.', 'error')
            
    return render_template('upload_confirmation.html')


@app.route('/api/due_amounts')
@login_required
def api_due_amounts():
    # Filter parameters
    customer_type = request.args.get('type', 'all')
    status = request.args.get('status', 'all')
    from_date = request.args.get('from')
    to_date = request.args.get('to')
    
    # Base query for orders not fully paid
    query = Order.query.filter(Order.payment_status != 'Paid')
    
    # Apply filters
    if customer_type != 'all':
        query = query.filter(Order.order_type == customer_type)
    
    if status != 'all':
        query = query.filter(Order.payment_status.ilike(f"%{status}%"))
        
    if from_date:
        query = query.filter(Order.created_at >= datetime.strptime(from_date, '%Y-%m-%d'))
    if to_date:
        query = query.filter(Order.created_at <= datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1))
        
    orders = query.order_by(Order.created_at.desc()).all()
    
    total_due = sum((o.total_amount or 0) - (o.received_amount or 0) for o in orders)
    walking_orders = [o for o in orders if o.order_type == 'walkin']
    client_orders = [o for o in orders if o.order_type == 'client']
    
    walking_due = sum((o.total_amount or 0) - (o.received_amount or 0) for o in walking_orders)
    client_due = sum((o.total_amount or 0) - (o.received_amount or 0) for o in client_orders)
    
    # Overdue: items older than 3 days and not paid
    overdue_limit = datetime.utcnow() - timedelta(days=3)
    overdue_orders = [o for o in orders if o.created_at < overdue_limit]
    overdue_due = sum((o.total_amount or 0) - (o.received_amount or 0) for o in overdue_orders)
    
    return jsonify({
        'summary': {
            'total_due': total_due,
            'total_orders': len(orders),
            'walking_due': walking_due,
            'walking_orders': len(walking_orders),
            'client_due': client_due,
            'client_orders': len(client_orders),
            'overdue_due': overdue_due,
            'overdue_orders': len(overdue_orders)
        },
        'due_amounts': [{
            'id': o.id,
            'order_date': o.created_at.strftime('%Y-%m-%d'),
            'customer_name': o.customer_name,
            'phone': o.customer_phone,
            'customer_type': o.order_type.title(),
            'order_number': o.receipt_number,
            'calculated_amount': o.total_amount or 0,
            'due_amount': (o.total_amount or 0) - (o.received_amount or 0),
            'payment_status': o.payment_status.title() if o.payment_status else 'Pending'
        } for o in orders],
        'type_summary': [
            {'customer_type': 'walking', 'total_due': walking_due, 'order_count': len(walking_orders)},
            {'customer_type': 'client', 'total_due': client_due, 'order_count': len(client_orders)}
        ],
        'top_due': [{
            'id': o.id,
            'customer_name': o.customer_name,
            'order_number': o.receipt_number,
            'due_amount': (o.total_amount or 0) - (o.received_amount or 0),
            'due_days': (datetime.utcnow() - o.created_at).days
        } for o in sorted(orders, key=lambda x: (x.total_amount or 0) - (x.received_amount or 0), reverse=True)[:5]]
    })


@app.route('/api/due_amounts/export')
@login_required
@admin_required
def export_due_amounts():
    customer_type = request.args.get('type', 'all')
    status = request.args.get('status', 'all')
    from_date = request.args.get('from')
    to_date = request.args.get('to')
    
    query = Order.query.filter(Order.payment_status != 'Paid')
    
    if customer_type != 'all':
        query = query.filter(Order.order_type == customer_type)
    if status != 'all':
        query = query.filter(Order.payment_status.ilike(f"%{status}%"))
    if from_date:
        query = query.filter(Order.created_at >= datetime.strptime(from_date, '%Y-%m-%d'))
    if to_date:
        query = query.filter(Order.created_at <= datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1))
        
    orders = query.order_by(Order.created_at.desc()).all()
    
    data = []
    for o in orders:
        data.append({
            'Date': o.created_at.strftime('%Y-%m-%d'),
            'Customer Name': o.customer_name,
            'Phone': o.customer_phone,
            'Type': o.order_type.title(),
            'Order Number': o.receipt_number,
            'Total Amount': o.total_amount or 0,
            'Due Amount': (o.total_amount or 0) - (o.received_amount or 0),
            'Payment Status': o.payment_status.title() if o.payment_status else 'Pending'
        })
    
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Due Amounts')
    output.seek(0)
    
    filename = f"due_amounts_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )



@app.route('/api/states')
@login_required
def api_states():
    states = db.session.query(DefaultStatePrice.state).distinct().all()
    return jsonify([s[0] for s in states])


@app.route('/api/reports/overview')
@login_required
@admin_required
def api_report_overview():
    # Mock data for demonstration, in real app calculate from DB
    orders = Order.query.all()
    total_revenue = sum(o.total_amount or 0 for o in orders)
    avg_order = total_revenue / len(orders) if orders else 0
    
    # Revenue trend (last 7 days)
    labels = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
    values = [sum(o.total_amount or 0 for o in orders if o.created_at.date() == (datetime.now() - timedelta(days=i)).date()) for i in range(6, -1, -1)]
    
    # Top states
    states_data = db.session.query(Order.receiver_state, db.func.sum(Order.total_amount)).group_by(Order.receiver_state).limit(5).all()
    
    return jsonify({
        'total_orders': len(orders),
        'total_revenue': total_revenue,
        'avg_order_value': avg_order,
        'conversion_rate': 85.5,
        'revenue_trend': {'labels': labels, 'values': values},
        'top_states': {
            'labels': [s[0] or 'Unknown' for s in states_data],
            'values': [float(s[1] or 0) for s in states_data]
        },
        'recent_transactions': [{
            'date': o.created_at.strftime('%Y-%m-%d'),
            'order_number': o.receipt_number,
            'customer_name': o.customer_name,
            'customer_type': o.order_type,
            'amount': o.total_amount or 0,
            'payment_status': o.payment_status.title() if o.payment_status else 'Pending',
            'status': o.status.title()
        } for o in orders[:10]]
    })


@app.route('/api/reports/sales')
@login_required
@admin_required
def api_report_sales():
    # Logic for sales report
    labels = [(datetime.now() - timedelta(days=i)).strftime('%a') for i in range(6, -1, -1)]
    values = [secrets.randbelow(10000) for _ in range(7)]
    
    return jsonify({
        'sales_by_day': {'labels': labels, 'values': values},
        'sales_by_weight': {
            'labels': ['0-500g', '500g-1kg', '1kg-2kg', '2kg-5kg', '5kg+'],
            'values': [30, 45, 20, 10, 5]
        },
        'detailed_sales': []
    })


@app.route('/api/reports/clients')
@login_required
@admin_required
def api_report_clients():
    clients = Client.query.all()
    return jsonify({
        'client_acquisition': {
            'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            'values': [5, 8, 12, 7, 15, 10]
        },
        'client_value_distribution': [40, 45, 15],
        'client_performance': [{
            'name': c.name,
            'client_id': f'CL-{c.id:04d}',
            'since': c.created_at.strftime('%Y-%m-%d'),
            'total_orders': len(c.orders),
            'total_spent': sum(o.total_amount or 0 for o in c.orders),
            'avg_order': sum(o.total_amount or 0 for o in c.orders) / len(c.orders) if c.orders else 0,
            'last_order': c.orders[-1].created_at.strftime('%Y-%m-%d') if c.orders else 'N/A',
            'status': 'Active' if c.is_active else 'Inactive'
        } for c in clients]
    })


@app.route('/api/reports/performance')
@login_required
@admin_required
def api_report_performance():
    return jsonify({
        'order_growth': 12.5,
        'revenue_growth': 15.2,
        'client_retention': 92.0,
        'avg_processing_time': 4.5,
        'efficiency_metrics': [85, 90, 78, 92, 88]
    })

@app.route('/api/mark_paid/<int:order_id>', methods=['POST'])
@login_required
def mark_paid(order_id):
    order = Order.query.get_or_404(order_id)
    order.payment_status = 'Paid'
    order.received_amount = order.total_amount
    order.amount_difference = 0
    db.session.commit()
    return jsonify({'success': True})
@app.route('/fix-db')
@login_required
@admin_required
def fix_db():
    from sqlalchemy import text
    try:
        # Check and add columns to Order table
        columns = [
            ('weight_category', 'VARCHAR(50)'),
            ('weight_in_kg', 'FLOAT'),
            ('dimensions', 'VARCHAR(50)'),
            ('tax_amount', 'FLOAT DEFAULT 0'),
            ('calculated_amount', 'FLOAT DEFAULT 0'),
            ('received_amount', 'FLOAT DEFAULT 0'),
            ('amount_difference', 'FLOAT DEFAULT 0'),
            ('difference_reason', 'VARCHAR(200)'),
            ('order_number', 'VARCHAR(50)'),
            ('order_date', 'VARCHAR(20)'),
            ('consignment_number', 'VARCHAR(50)')
        ]
        
        for col_name, col_type in columns:
            try:
                db.session.execute(text(f"ALTER TABLE orders ADD COLUMN {col_name} {col_type}"))
                db.session.commit()
            except Exception:
                db.session.rollback()
        
        db.create_all()
        flash('Database schema synchronized successfully!', 'success')
    except Exception as e:
        flash(f'Error syncing database: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))


@app.route('/admin/receipts', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_receipts():
    if request.method == 'POST':
        user_id = request.form.get('user_id')  # Optional now
        branch_id = request.form.get('branch_id')
        prefix = request.form.get('prefix')
        base_number = request.form.get('base_number', '100000')
        range_end = request.form.get('range_end')
        
        # Check if assignment exists for this branch (and no user)
        existing = StaffReceiptAssignment.query.filter_by(
            branch_id=branch_id, 
            user_id=None
        ).first()
        
        if existing:
            flash('An assignment for this branch already exists.', 'error')
            return redirect(url_for('admin_receipts'))

        assignment = StaffReceiptAssignment(
            user_id=user_id if user_id else None,
            branch_id=branch_id,
            prefix=prefix,
            base_number=base_number,
            range_end=range_end,
            assigned_by=current_user.id
        )
        db.session.add(assignment)
        db.session.commit()
        flash('Tracking assignment created successfully!', 'success')
        return redirect(url_for('admin_receipts'))
    
    assignments = StaffReceiptAssignment.query.all()
    users = User.query.filter(User.role.in_(['staff', 'manager'])).all()
    branches = Branch.query.all()
    return render_template('admin_receipt_assignments.html', 
                         assignments=assignments, 
                         users=users, 
                         branches=branches)
@app.route('/admin/receipts/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_receipt_assignment(id):
    assignment = StaffReceiptAssignment.query.get_or_404(id)
    if request.method == 'POST':
        assignment.prefix = request.form.get('prefix')
        assignment.base_number = request.form.get('base_number')
        assignment.range_end = request.form.get('range_end')
        assignment.current_sequence = int(request.form.get('current_sequence', 0))
        assignment.is_active = request.form.get('is_active') == 'on'
        
        db.session.commit()
        flash('Tracking assignment updated successfully!', 'success')
        return redirect(url_for('admin_receipts'))
    
    users = User.query.filter(User.role.in_(['staff', 'manager'])).all()
    branches = Branch.query.all()
    return render_template('admin_receipt_assignments.html', 
                         edit_item=assignment, 
                         assignments=StaffReceiptAssignment.query.all(), 
                         users=users, 
                         branches=branches)

@app.route('/admin/receipts/toggle/<int:id>')
@login_required
@admin_required
def toggle_receipt_assignment(id):
    assignment = StaffReceiptAssignment.query.get_or_404(id)
    assignment.is_active = not assignment.is_active
    db.session.commit()
    flash('Assignment status updated!', 'success')
    return redirect(url_for('admin_receipts'))

@app.route('/api/receipt/next')
@login_required
def api_next_receipt():
    number = get_next_receipt_number(current_user)
    return jsonify({'receipt_number': number})

@app.route('/receipts/check')
@login_required
def staff_receipt_check():
    if current_user.role == 'admin':
        assignments = StaffReceiptAssignment.query.filter_by(is_active=True).all()
    elif current_user.role == 'manager':
        assignments = StaffReceiptAssignment.query.filter_by(branch_id=current_user.branch_id, is_active=True).all()
    else:
        # Show both personal assignments and branch assignments
        assignments = StaffReceiptAssignment.query.filter(
            StaffReceiptAssignment.branch_id == current_user.branch_id,
            StaffReceiptAssignment.is_active == True,
            (StaffReceiptAssignment.user_id == current_user.id) | (StaffReceiptAssignment.user_id == None)
        ).all()
    
    next_number = get_next_receipt_number(current_user)
    return render_template('staff_receipt_check.html', assignments=assignments, next_number=next_number)


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


#@app.errorhandler(500)
#def internal_error(error):
     #db.session.rollback()
     #return render_template('errors/500.html'), 500


import os

# ============== CLIENT DUE REPORT ==============

@app.route('/client-due-report')
@login_required
@staff_required
def client_due_report():
    """Main client-wise due report page"""
    return render_template('client_due_report.html')


@app.route('/api/client-due-summary')
@login_required
@staff_required
def api_client_due_summary():
    """API to get all clients with their due amounts"""
    try:
        # Get filter parameters
        start_date_str = request.args.get('start_date', '')
        end_date_str = request.args.get('end_date', '')
        
        # Query all clients with orders
        clients = Client.query.filter_by(is_active=True).all()
        
        client_data = []
        total_due_all = 0
        
        for client in clients:
            # Build query for client orders
            query = Order.query.filter_by(client_id=client.id, order_type='client')
            
            # Apply date filters if provided
            if start_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                query = query.filter(Order.created_at >= start_date)
            if end_date_str:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                # Add one day to include the end date fully
                end_date = end_date + timedelta(days=1)
                query = query.filter(Order.created_at < end_date)
            
            orders = query.all()
            
            if not orders:
                continue
            
            # Calculate totals for this client
            total_amount = sum(o.total_amount or 0 for o in orders)
            received_amount = sum(o.received_amount or 0 for o in orders)
            due_amount = total_amount - received_amount
            
            if due_amount > 0:  # Only include clients with outstanding dues
                client_data.append({
                    'id': client.id,
                    'name': client.name,
                    'company_name': client.company_name,
                    'phone': client.phone,
                    'email': client.email,
                    'total_orders': len(orders),
                    'total_amount': total_amount,
                    'received_amount': received_amount,
                    'due_amount': due_amount,
                    'last_order_date': max(o.created_at for o in orders).strftime('%Y-%m-%d') if orders else None
                })
                total_due_all += due_amount
        
        # Sort by due amount (highest first)
        client_data.sort(key=lambda x: x['due_amount'], reverse=True)
        
        return jsonify({
            'success': True,
            'clients': client_data,
            'summary': {
                'total_clients': len(client_data),
                'total_due': total_due_all
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/client/<int:client_id>/orders-due')
@login_required
@staff_required
def client_orders_due(client_id):
    """Individual client orders page with due amounts"""
    client = Client.query.get_or_404(client_id)
    return render_template('client_orders_due.html', client=client)


@app.route('/api/client/<int:client_id>/orders')
@login_required
@staff_required
def api_client_orders(client_id):
    """API to get orders for a specific client with filters"""
    try:
        # Get filter parameters
        start_date_str = request.args.get('start_date', '')
        end_date_str = request.args.get('end_date', '')
        payment_status = request.args.get('payment_status', '')
        
        # Build query
        query = Order.query.filter_by(client_id=client_id, order_type='client')
        
        # Apply date filters
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            query = query.filter(Order.created_at >= start_date)
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            end_date = end_date + timedelta(days=1)
            query = query.filter(Order.created_at < end_date)
        
        # Apply payment status filter
        if payment_status and payment_status != 'all':
            query = query.filter_by(payment_status=payment_status)
        
        orders = query.order_by(Order.created_at.desc()).all()
        
        # Calculate totals
        total_amount = sum(o.total_amount or 0 for o in orders)
        received_amount = sum(o.received_amount or 0 for o in orders)
        due_amount = total_amount - received_amount
        
        # Prepare order data
        order_data = []
        for order in orders:
            order_due = (order.total_amount or 0) - (order.received_amount or 0)
            order_data.append({
                'id': order.id,
                'receipt_number': order.receipt_number,
                'created_at': order.created_at.strftime('%Y-%m-%d'),
                'receiver_name': order.receiver_name,
                'receiver_city': order.receiver_city,
                'receiver_state': order.receiver_state,
                'weight': order.weight or 0,
                'total_amount': order.total_amount or 0,
                'received_amount': order.received_amount or 0,
                'due_amount': order_due,
                'payment_status': order.payment_status,
                'status': order.status
            })
        
        return jsonify({
            'success': True,
            'orders': order_data,
            'summary': {
                'total_orders': len(orders),
                'total_amount': total_amount,
                'received_amount': received_amount,
                'due_amount': due_amount
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/client/<int:client_id>/print-consolidated-bill')
@login_required
@manager_required
def print_consolidated_bill(client_id):
    """Print consolidated bill for client orders in a date range"""
    client = Client.query.get_or_404(client_id)
    
    # Get date range parameters
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    is_gst = request.args.get('gst', 'no').lower() == 'yes'  # Get GST parameter
    
    # Build query
    query = Order.query.filter_by(client_id=client_id, order_type='client')
    
    # Apply date filters
    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        query = query.filter(Order.created_at >= start_date)
    else:
        start_date = None
    
    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        end_date_display = end_date
        end_date = end_date + timedelta(days=1)
        query = query.filter(Order.created_at < end_date)
    else:
        end_date_display = None
    
    orders = query.order_by(Order.created_at.asc()).all()
    
    # Calculate grand totals
    grand_total_amount = sum(o.total_amount or 0 for o in orders)
    grand_received_amount = sum(o.received_amount or 0 for o in orders)
    grand_due_amount = grand_total_amount - grand_received_amount
    grand_total_weight = sum(o.weight or 0 for o in orders)
    
    # Calculate GST values if GST bill
    if is_gst:
        # Taxable value (amount without GST - reverse calculate)
        taxable_value = grand_total_amount / 1.18  # Assuming total includes 18% GST
        cgst_amount = taxable_value * 0.09  # 9% CGST
        sgst_amount = taxable_value * 0.09  # 9% SGST
    else:
        taxable_value = 0
        cgst_amount = 0
        sgst_amount = 0
    
    # Check billing date
    today_day = datetime.now().day
    if client.billing_date and client.billing_date != today_day:
        flash(f'Note: Today (Day {today_day}) is not the scheduled billing date (Day {client.billing_date}) for {client.name}.', 'warning')
    
    return render_template('client_consolidated_bill.html',
                         client=client,
                         orders=orders,
                         start_date=start_date,
                         end_date=end_date_display,
                         grand_total_amount=grand_total_amount,
                         grand_received_amount=grand_received_amount,
                         grand_due_amount=grand_due_amount,
                         grand_total_weight=grand_total_weight,
                         is_gst=is_gst,
                         taxable_value=taxable_value,
                         cgst_amount=cgst_amount,
                         sgst_amount=sgst_amount)


# ============== ADMIN EXPORT ==============

@app.route('/admin/export/db')
@login_required
@admin_required
def export_db():
    """Download the raw SQLite database file."""
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if not db_uri.startswith('sqlite:///'):
        flash('Only SQLite databases can be exported this way.', 'error')
        return redirect(url_for('dashboard'))
    db_path = db_uri[len('sqlite:///'):]
    if not os.path.isfile(db_path):
        flash('Database file not found.', 'error')
        return redirect(url_for('dashboard'))
    filename = f"crm_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    return send_file(db_path, as_attachment=True, download_name=filename,
                     mimetype='application/octet-stream')


@app.route('/admin/export/xlsx')
@login_required
@admin_required
def export_xlsx():
    """Export all orders to an Excel (.xlsx) file."""
    orders = Order.query.order_by(Order.created_at.desc()).all()

    rows = []
    for o in orders:
        rows.append({
            'Receipt No': o.receipt_number,
            'Order Type': o.order_type,
            'Status': o.status,
            'Payment Status': o.payment_status,
            'Payment Mode': o.payment_mode,
            'Customer Name': o.customer_name,
            'Customer Phone': o.customer_phone,
            'Customer Email': o.customer_email,
            'Customer Address': o.customer_address,
            'Receiver Name': o.receiver_name,
            'Receiver Phone': o.receiver_phone,
            'Receiver Address': o.receiver_address,
            'Receiver City': o.receiver_city,
            'Receiver State': o.receiver_state,
            'Receiver Pincode': o.receiver_pincode,
            'Package Description': o.package_description,
            'Weight (kg)': o.weight_in_kg,
            'Number of Boxes': o.number_of_boxes,
            'Base Amount': o.base_amount,
            'Total Amount': o.total_amount,
            'Received Amount': o.received_amount,
            'Amount Difference': o.amount_difference,
            'Special Instructions': o.special_instructions,
            'Handling Tags': o.handling_tags,
            'Branch': o.branch.name if o.branch else '',
            'Created By': o.created_by_user.username if o.created_by_user else '',
            'Created At': o.created_at.strftime('%Y-%m-%d %H:%M') if o.created_at else '',
            'Delivered At': o.delivered_at.strftime('%Y-%m-%d %H:%M') if o.delivered_at else '',
        })

    df = pd.DataFrame(rows)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Orders')
    output.seek(0)

    filename = f"crm_orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(output, as_attachment=True, download_name=filename,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@app.route('/api/scan-document', methods=['POST'])
@login_required
@staff_required
def scan_document():
    if 'document' not in request.files:
        return jsonify({'error': 'No document uploaded'}), 400
    
    file = request.files['document']
    if file.filename == '':
        return jsonify({'error': 'No document selected'}), 400
    
    if not (file and (file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf')))):
        return jsonify({'error': 'Unsupported file format. Please upload an image or PDF.'}), 400

    try:
        # Load Gemini model
        model = genai.GenerativeModel('gemini-flash-latest')
        
        # Prepare content for Gemini
        img_content = []
        
        if file.filename.lower().endswith('.pdf'):
            # Convert PDF to Image (first page)
            pdf_data = file.read()
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            page = doc.load_page(0)
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            img_byte_arr = BytesIO()
            img.save(img_byte_arr, format='JPEG')
            img_content.append({"mime_type": "image/jpeg", "data": img_byte_arr.getvalue()})
        else:
            # Handle standard image
            img_data = file.read()
            img_content.append({"mime_type": file.mimetype, "data": img_data})

        # Prompt for extraction
        prompt = """
        Extract the following information from this shipping document or label. 
        Look for 'From' (Sender) and 'To' (Receiver) sections.
        Return ONLY a JSON object with these keys:
        - from_name
        - from_phone
        - from_address
        - to_name
        - to_phone
        - to_address
        - to_city
        - to_state
        - to_pincode

        If a field is not found, leave it as an empty string.
        """

        response = model.generate_content([prompt, img_content[0]])
        
        # Parse JSON results
        result_text = response.text.strip()
        # Clean potential markdown code blocks
        if result_text.startswith('```json'):
            result_text = result_text[7:-3].strip()
        elif result_text.startswith('```'):
            result_text = result_text[3:-3].strip()
            
        data = json.loads(result_text)
        return jsonify(data)

    except Exception as e:
        print(f"AI Scan Error: {str(e)}")
        return jsonify({'error': f"Failed to process document: {str(e)}"}), 500


# ============== RUN APP ==============

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)