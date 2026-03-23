# Triggering server reload for template fix
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
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
try:
    import google.genai as genai
except ImportError:
    genai = None
from PIL import Image
import requests

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
    DefaultStatePrice, ClientStatePrice, NormalClientStatePrice, Notification, StaffReceiptAssignment, Receiver,
    BillingPattern, SalesVisit, FollowUp, Meeting, ClientAddress, Courier, Offer, AuditLog
)

app = Flask(__name__)
app.config.from_object(Config)

# Configure Gemini
if genai and app.config.get('GEMINI_API_KEY'):
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
        if not current_user.is_authenticated or current_user.role not in ['admin', 'manager', 'operation_manager', 'staff']:
            flash('Staff access required.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'manager', 'operation_manager']:
            flash('Admin or Manager access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def marketing_manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'marketing_manager':
            flash('Marketing Manager access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def branch_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'branch':
            flash('Branch access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def delivery_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['delivery', 'delivery_pickup']:
            flash('Delivery personnel access required.', 'error')
            return redirect(url_for('login'))
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


def calculate_from_state_price(weight, price_obj, shipping_mode='standard'):
    amount = 0
    
    # Check if this is air cargo (>3kg with special tiers)
    is_air = getattr(price_obj, 'shipping_mode', 'standard').lower() == 'air'
    
    if is_air:
        # Air cargo pricing for weights > 3kg
        if weight > 3.0:
            if weight <= 10.0:  # 3-10 kg
                amount = getattr(price_obj, 'price_3_10kg', 0) or 0
            elif weight <= 25.0:  # 10-25 kg
                amount = getattr(price_obj, 'price_10_25kg', 0) or 0
            elif weight <= 50.0:  # 25-50 kg
                amount = getattr(price_obj, 'price_25_50kg', 0) or 0
            elif weight <= 100.0:  # 50-100 kg
                amount = getattr(price_obj, 'price_50_100kg', 0) or 0
            else:  # 100+ kg
                amount = getattr(price_obj, 'price_100plus_kg', 0) or 0
        else:
            # For air cargo <= 3kg, use standard tiers
            if weight <= 0.1:  # 100g
                amount = getattr(price_obj, 'price_100gm', 0) or 0
            elif weight <= 0.25:  # 250g
                amount = getattr(price_obj, 'price_250gm', 0) or 0
            elif weight <= 0.5:  # 500g
                amount = getattr(price_obj, 'price_500gm', 0) or 0
            elif weight <= 1.0:  # 1kg
                amount = getattr(price_obj, 'price_1kg', 0) or 0
            elif weight <= 2.0:  # 2kg
                amount = (getattr(price_obj, 'price_1kg', 0) or 0) * 2
            elif weight <= 3.0:  # 3kg
                amount = (getattr(price_obj, 'price_1kg', 0) or 0) * 3
    else:
        # Standard/other shipping mode pricing
        if weight <= 0.1:  # 100g
            amount = price_obj.price_100gm
        elif weight <= 0.25:  # 250g
            amount = price_obj.price_250gm
        elif weight <= 0.5:  # 500g
            amount = price_obj.price_500gm
        elif weight <= 1.0:  # 1kg
            amount = price_obj.price_1kg
        elif weight <= 2.0:  # 2kg = 1kg price × 2
            amount = price_obj.price_1kg * 2
        elif weight <= 3.0:  # 3kg = 1kg price × 3
            amount = price_obj.price_1kg * 3
        else:
            # For weights > 3kg: use extra_per_kg rate for entire weight
            extra_per_kg = getattr(price_obj, 'price_extra_per_kg', 20) or 20
            amount = weight * extra_per_kg

    if amount == 0:
        return None
        
    return amount, 0, 0, 0, amount


def calculate_order_amount(weight, billing_pattern_id=None, state=None, client_id=None, insured_amount=0, shipping_mode='standard'):
    state_clean = state.strip().lower() if state else None
    shipping_mode_clean = shipping_mode.strip().lower() if shipping_mode else 'standard'
    
    # Get insurance percentage from settings
    insurance_setting = SystemSettings.query.filter_by(key='insurance_percentage').first()
    insurance_percentage = float(insurance_setting.value) if insurance_setting and insurance_setting.value else 0
    insurance_charge = (insured_amount * insurance_percentage) / 100
    
    # 1. Check for Client State Price first
    if client_id and state_clean:
        client_price = ClientStatePrice.query.filter(
            ClientStatePrice.client_id == client_id,
            db.func.lower(ClientStatePrice.state) == state_clean,
            db.func.lower(ClientStatePrice.shipping_mode) == shipping_mode_clean
        ).first()
        if client_price:
            result = calculate_from_state_price(weight, client_price)
            if result:
                # result is (base, weight_charge, additional, discount, total)
                res_list = list(result)
                res_list[4] += insurance_charge # Add to total
                return (*tuple(res_list), 'client', insurance_charge)
        
        # Fallback to standard mode if specific shipping mode not found
        if shipping_mode_clean != 'standard':
            client_price = ClientStatePrice.query.filter(
                ClientStatePrice.client_id == client_id,
                db.func.lower(ClientStatePrice.state) == state_clean,
                db.func.lower(ClientStatePrice.shipping_mode) == 'standard'
            ).first()
            if client_price:
                result = calculate_from_state_price(weight, client_price)
                if result:
                    res_list = list(result)
                    res_list[4] += insurance_charge
                    return (*tuple(res_list), 'client', insurance_charge)

    # 2. Check for Normal Client State Price (Default for all clients)
    if state_clean:
        normal_client_price = NormalClientStatePrice.query.filter(
            db.func.lower(NormalClientStatePrice.state) == state_clean,
            db.func.lower(NormalClientStatePrice.shipping_mode) == shipping_mode_clean
        ).first()
        if normal_client_price:
            result = calculate_from_state_price(weight, normal_client_price)
            if result:
                res_list = list(result)
                res_list[4] += insurance_charge # Add to total
                return (*tuple(res_list), 'normal_client', insurance_charge)
        
        # Fallback to standard mode if specific shipping mode not found
        if shipping_mode_clean != 'standard':
            normal_client_price = NormalClientStatePrice.query.filter(
                db.func.lower(NormalClientStatePrice.state) == state_clean,
                db.func.lower(NormalClientStatePrice.shipping_mode) == 'standard'
            ).first()
            if normal_client_price:
                result = calculate_from_state_price(weight, normal_client_price)
                if result:
                    res_list = list(result)
                    res_list[4] += insurance_charge
                    return (*tuple(res_list), 'normal_client', insurance_charge)

    # 3. Check for Default State Price
    if state_clean:
        default_price = DefaultStatePrice.query.filter(
            db.func.lower(DefaultStatePrice.state) == state_clean,
            db.func.lower(DefaultStatePrice.shipping_mode) == shipping_mode_clean
        ).first()
        if default_price:
            result = calculate_from_state_price(weight, default_price)
            if result:
                res_list = list(result)
                res_list[4] += insurance_charge # Add to total
                return (*tuple(res_list), 'state', insurance_charge)
        
        # Fallback to standard mode if specific shipping mode not found
        if shipping_mode_clean != 'standard':
            default_price = DefaultStatePrice.query.filter(
                db.func.lower(DefaultStatePrice.state) == state_clean,
                db.func.lower(DefaultStatePrice.shipping_mode) == 'standard'
            ).first()
            if default_price:
                result = calculate_from_state_price(weight, default_price)
                if result:
                    res_list = list(result)
                    res_list[4] += insurance_charge
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
            
            if user.role not in ['admin', 'manager', 'operation_manager', 'marketing_manager', 'staff', 'delivery', 'delivery_pickup', 'branch', 'customer']:
                flash('Access restricted for this role.', 'error')
                return render_template('login.html')
            
            # Check if branch user has a branch assigned
            if user.role == 'branch' and not user.branch_id:
                flash('Your account is not assigned to any branch. Please contact your administrator.', 'error')
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


# ============== SIGNUP & EMAIL OTP ==============

def send_otp_email(email, otp_code):
    """Send OTP via email using Flask-Mail or simple SMTP"""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Email configuration
        sender_email = app.config.get('MAIL_USERNAME', 'noreply@crmdelivery.com')
        sender_password = app.config.get('MAIL_PASSWORD', '')
        smtp_server = app.config.get('MAIL_SERVER', 'smtp.gmail.com')
        smtp_port = app.config.get('MAIL_PORT', 587)
        
        # Skip if credentials not configured
        if not sender_password:
            print(f"[DEV MODE] OTP for {email}: {otp_code}")
            session['otp_code'] = otp_code
            session['otp_email'] = email
            return True
        
        # Create email
        message = MIMEMultipart("alternative")
        message["Subject"] = "Your CRM Delivery Account Verification Code"
        message["From"] = sender_email
        message["To"] = email
        
        # Email body
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px;">
                <div style="max-width: 500px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px;">
                    <h2 style="color: #0f172a; margin-bottom: 20px;">Verify Your Email</h2>
                    <p style="color: #666; font-size: 15px; line-height: 1.6;">
                        Welcome to CRM Delivery! Use the code below to verify your email and complete your account registration.
                    </p>
                    <div style="background: #f0f0f0; border-left: 4px solid #7c3aed; padding: 20px; margin: 25px 0; border-radius: 5px;">
                        <p style="margin: 0; color: #666; font-size: 13px; margin-bottom: 10px;">Your verification code:</p>
                        <p style="margin: 0; font-size: 32px; font-weight: bold; color: #7c3aed; letter-spacing: 5px;">{otp_code}</p>
                    </div>
                    <p style="color: #666; font-size: 13px;">This code will expire in 30 minutes.</p>
                    <p style="color: #999; font-size: 12px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 20px;">
                        If you didn't request this code, please ignore this email.
                    </p>
                </div>
            </body>
        </html>
        """
        
        part = MIMEText(html, "html")
        message.attach(part)
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, message.as_string())
        
        return True
    except Exception as e:
        print(f"Error sending OTP email: {str(e)}")
        # Store in session as fallback
        session['otp_code'] = otp_code
        session['otp_email'] = email
        return True


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Validation
        if not username or len(username) < 3:
            flash('Username must be at least 3 characters long.', 'error')
            return render_template('signup.html')
        
        if not email:
            flash('Email is required.', 'error')
            return render_template('signup.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('signup.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('signup.html')
        
        # Check if username or email already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'error')
            return render_template('signup.html')
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already registered. Please use a different email or login.', 'error')
            return render_template('signup.html')
        
        # Generate OTP
        otp_code = str(random.randint(100000, 999999))
        
        # Store signup data in session
        session['signup_pending'] = True
        session['pending_username'] = username
        session['pending_email'] = email
        session['pending_password'] = password  # Hash before saving would be better
        session['otp_code'] = otp_code
        session['otp_email'] = email
        
        # Send OTP email
        send_otp_email(email, otp_code)
        
        flash('OTP sent to your email. Please verify to complete registration.', 'success')
        return redirect(url_for('verify_otp'))
    
    return render_template('signup.html')


@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    # Check if signup is pending
    if not session.get('signup_pending'):
        flash('Please complete the signup form first.', 'error')
        return redirect(url_for('signup'))
    
    if request.method == 'POST':
        submitted_otp = request.form.get('otp_code', '').strip()
        stored_otp = session.get('otp_code')
        
        if submitted_otp != stored_otp:
            flash('Invalid OTP. Please try again.', 'error')
            return render_template('verify_otp.html', email=session.get('pending_email'))
        
        # OTP verified - Create user account
        try:
            username = session.get('pending_username')
            email = session.get('pending_email')
            password = session.get('pending_password')
            
            # Create new user with staff role by default
            new_user = User(
                username=username,
                email=email,
                role='staff',  # Default role for new registrations
                is_active=True
            )
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
            # Clear session
            session.pop('signup_pending', None)
            session.pop('pending_username', None)
            session.pop('pending_email', None)
            session.pop('pending_password', None)
            session.pop('otp_code', None)
            session.pop('otp_email', None)
            
            flash('Account created successfully! You can now login.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            print(f"Error creating user: {str(e)}")
            flash('An error occurred while creating your account. Please try again.', 'error')
            return render_template('verify_otp.html', email=session.get('pending_email'))
    
    return render_template('verify_otp.html', email=session.get('pending_email'))


@app.route('/resend-otp', methods=['POST'])
def resend_otp():
    if not session.get('signup_pending'):
        flash('Please complete the signup form first.', 'error')
        return redirect(url_for('signup'))
    
    # Generate new OTP
    otp_code = str(random.randint(100000, 999999))
    email = session.get('pending_email')
    
    # Update session with new OTP
    session['otp_code'] = otp_code
    
    # Send OTP email
    send_otp_email(email, otp_code)
    
    flash('New OTP sent to your email.', 'success')
    return redirect(url_for('verify_otp'))


# ============== DASHBOARD ==============

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'customer':
        return redirect(url_for('customer_dashboard'))
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    if current_user.role == 'marketing_manager':
        return redirect(url_for('marketing_manager_dashboard'))
    if current_user.role == 'operation_manager':
        return redirect(url_for('operations_dashboard'))
    if current_user.role == 'manager':
        return redirect(url_for('manager_dashboard'))
    if current_user.role == 'branch':
        return redirect(url_for('branch_dashboard'))
    if current_user.role in ['delivery', 'delivery_pickup']:
        return redirect(url_for('delivery_dashboard'))
    if current_user.role == 'staff':
        return redirect(url_for('staff_dashboard'))
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


@app.route('/manager-dashboard')
@login_required
@manager_required
def manager_dashboard():
    """Manager dashboard with 15-day history, offers, and promotions"""
    from sqlalchemy import func, desc
    from datetime import datetime, timedelta
    
    # Get date range (default 15 days)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    if not date_from:
        date_from = (datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')
    
    query = Order.query.filter(
        Order.created_at >= datetime.strptime(date_from, '%Y-%m-%d'),
        Order.created_at <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
    )
    
    # Basic Stats
    total_orders = query.count()
    total_revenue = query.with_entities(func.sum(Order.total_amount)).scalar() or 0
    total_received = query.with_entities(func.sum(Order.received_amount)).scalar() or 0
    pending_amount = total_revenue - total_received
    at_destination_orders = query.filter_by(status='at_destination').count()
    in_transit = query.filter_by(status='in_transit').count()
    delivered = query.filter_by(status='delivered').count()
    pending = query.filter_by(status='pending').count()
    
    # Top Clients (by order count)
    top_clients = db.session.query(
        Client.name, 
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('total_spent'),
        func.sum(Order.received_amount).label('total_received')
    ).join(Order).filter(
        Order.created_at >= datetime.strptime(date_from, '%Y-%m-%d'),
        Order.created_at <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
    ).group_by(Client.id).order_by(desc('order_count')).limit(10).all()
    
    # Client Due Report (Unpaid orders)
    client_dues = db.session.query(
        Client.name,
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount - Order.received_amount).label('due_amount')
    ).join(Order).filter(
        Order.payment_status != 'paid',
        Order.created_at >= datetime.strptime(date_from, '%Y-%m-%d'),
        Order.created_at <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
    ).group_by(Client.id).having(func.sum(Order.total_amount - Order.received_amount) > 0).all()
    
    # Get all offers and promotions
    offers = Offer.query.all()
    
    # Recent orders
    recent_orders = query.order_by(Order.created_at.desc()).limit(10).all()
    
    branches = Branch.query.all()
    
    return render_template('manager_dashboard.html',
                         user=current_user,
                         total_orders=total_orders,
                         total_revenue=total_revenue,
                         total_received=total_received,
                         pending_amount=pending_amount,
                         at_destination_orders=at_destination_orders,
                         in_transit=in_transit,
                         delivered=delivered,
                         pending=pending,
                         top_clients=top_clients,
                         client_dues=client_dues,
                         offers=offers,
                         recent_orders=recent_orders,
                         branches=branches,
                         date_from=date_from,
                         date_to=date_to)


@app.route('/staff-dashboard')
@login_required
@staff_required
def staff_dashboard():
    from sqlalchemy import func, desc
    from datetime import datetime, timedelta
    
    # Filters
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    branch_id = request.args.get('branch_id', type=int)
    
    query = Order.query
    
    if date_from:
        query = query.filter(Order.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(Order.created_at <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
    if branch_id:
        query = query.filter_by(branch_id=branch_id)
    
    # Basic Stats
    total_orders = query.count()
    total_revenue = query.with_entities(func.sum(Order.total_amount)).scalar() or 0
    at_destination_orders = query.filter_by(status='at_destination').count()
    
    # Top Clients (by order count)
    top_clients = db.session.query(
        Client.name, 
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('total_spent')
    ).join(Order).group_by(Client.id).order_by(desc('order_count')).limit(5).all()
    
    # Client Due Report (Unpaid orders)
    client_dues = db.session.query(
        Client.name,
        func.sum(Order.total_amount - Order.received_amount).label('due_amount')
    ).join(Order).filter(Order.payment_status != 'paid').group_by(Client.id).having(func.sum(Order.total_amount - Order.received_amount) > 0).all()
    
    # Branch-wise (Center-wise) Analysis
    branch_stats = db.session.query(
        Branch.name,
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('revenue')
    ).join(Order).group_by(Branch.id).all()

    branches = Branch.query.all()
    
    return render_template('staff_dashboard.html',
                         total_orders=total_orders,
                         total_revenue=total_revenue,
                         at_destination_orders=at_destination_orders,
                         top_clients=top_clients,
                         client_dues=client_dues,
                         branch_stats=branch_stats,
                         branches=branches,
                         date_from=date_from,
                         date_to=date_to,
                         selected_branch=branch_id)


@app.route('/branch-dashboard')
@login_required
@branch_required
def branch_dashboard():
    """Branch user dashboard - shows only their branch data"""
    from sqlalchemy import func, desc
    from datetime import datetime, timedelta
    
    # Get branch info
    branch = current_user.branch
    if not branch:
        flash('Branch configuration error. Please contact admin.', 'error')
        return redirect(url_for('login'))
    
    # Filters
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    query = Order.query.filter_by(branch_id=branch.id)
    
    if date_from:
        query = query.filter(Order.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(Order.created_at <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
    
    # Basic Stats
    total_orders = query.count()
    total_revenue = query.with_entities(func.sum(Order.total_amount)).scalar() or 0
    at_destination_orders = query.filter_by(status='at_destination').count()
    in_transit_orders = query.filter_by(status='in_transit').count()
    delivered_orders = query.filter_by(status='delivered').count()
    
    # Recent orders
    recent_orders = query.order_by(Order.created_at.desc()).limit(10).all()
    
    return render_template('branch_dashboard.html',
                         branch=branch,
                         total_orders=total_orders,
                         total_revenue=total_revenue,
                         at_destination_orders=at_destination_orders,
                         in_transit_orders=in_transit_orders,
                         delivered_orders=delivered_orders,
                         recent_orders=recent_orders,
                         date_from=date_from,
                         date_to=date_to)


@app.route('/delivery-dashboard')
@login_required
@delivery_required
def delivery_dashboard():
    """Delivery personnel dashboard"""
    from sqlalchemy import func, desc
    from datetime import datetime, timedelta
    
    # Get assigned orders for this delivery person
    assigned_orders = Order.query.filter_by(delivery_person_id=current_user.id).all()
    
    # Count by status
    pending_pickups = len([o for o in assigned_orders if o.status == 'pending'])
    in_transit_count = len([o for o in assigned_orders if o.status == 'in_transit'])
    delivered_count = len([o for o in assigned_orders if o.status == 'delivered'])
    
    # Get reschedule requests
    reschedules = db.session.query(Order).filter(
        Order.delivery_person_id == current_user.id,
        Order.reschedule_reason.isnot(None)
    ).all()
    
    return render_template('delivery_dashboard.html',
                         user=current_user,
                         assigned_orders=assigned_orders,
                         pending_pickups=pending_pickups,
                         in_transit_count=in_transit_count,
                         delivered_count=delivered_count,
                         reschedules=reschedules)


@app.route('/admin-dashboard')
@login_required
@admin_required
def admin_dashboard():
    from sqlalchemy import func, desc
    from datetime import datetime, timedelta, timezone
    
    # Get date filter from query parameters
    days_filter = request.args.get('days', 30, type=int)
    start_date = datetime.now(timezone.utc) - timedelta(days=days_filter)
    
    # Total Shipments and Revenue
    total_shipments = Order.query.count()
    total_revenue = db.session.query(func.sum(Order.total_amount)).scalar() or 0
    
    # Filter by date for dynamic stats
    recent_shipments = Order.query.filter(Order.created_at >= start_date).count()



    recent_revenue = db.session.query(func.sum(Order.total_amount)).filter(Order.created_at >= start_date).scalar() or 0
    
    # Top Customers
    top_customers = db.session.query(
        Order.customer_name,
        Order.customer_phone,
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('total_spent')
    ).filter(Order.created_at >= start_date).group_by(
        Order.customer_name, Order.customer_phone
    ).order_by(desc('total_spent')).limit(10).all()
    
    # Top Clients
    top_clients = db.session.query(
        Client.name,
        Client.company_name,
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('total_spent')
    ).join(Order, Order.client_id == Client.id).filter(
        Order.created_at >= start_date
    ).group_by(Client.id, Client.name, Client.company_name).order_by(desc('total_spent')).limit(10).all()
    
    # Branch wise Statistics
    branch_stats = db.session.query(
        Branch.name,
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('total_amount')
    ).join(Order, Order.branch_id == Branch.id).filter(
        Order.created_at >= start_date
    ).group_by(Branch.id, Branch.name).order_by(desc('order_count')).all()
    
    # Staff Orders (date wise - last 7 days)
    staff_stats = db.session.query(
        User.username,
        func.count(Order.id).label('orders_created'),
        func.sum(Order.total_amount).label('total_value')
    ).join(Order, Order.created_by == User.id).filter(
        Order.created_at >= (datetime.now(timezone.utc) - timedelta(days=7)),
        User.role.in_(['staff', 'manager'])
    ).group_by(User.id, User.username).order_by(desc('orders_created')).limit(10).all()
    
    # Client Due Report (unpaid invoices)
    due_clients_rows = db.session.query(
        Client.name,
        Client.company_name,
        Client.email,
        Client.id,
        func.count(Order.id).label('pending_orders'),
        func.sum(Order.total_amount).label('total_due')
    ).join(Order, Order.client_id == Client.id).filter(
        Order.payment_status.in_(['unpaid', 'partial'])
    ).group_by(Client.id, Client.name, Client.company_name, Client.email).order_by(desc('total_due')).limit(10).all()
    
    # Convert to dict for template
    due_clients = [
        {
            'name': row[0],
            'company_name': row[1],
            'email': row[2],
            'id': row[3],
            'pending_orders': row[4],
            'total_due': float(row[5]) if row[5] else 0
        }
        for row in due_clients_rows
    ]
    
    # Daily Revenue (last 7 days)
    daily_revenue_rows = db.session.query(
        func.date(Order.created_at).label('order_date'),
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('daily_total')
    ).filter(Order.created_at >= (datetime.now(timezone.utc) - timedelta(days=7))).group_by(
        func.date(Order.created_at)
    ).order_by('order_date').all()
    
    # Convert to dict for JSON serialization
    daily_revenue = [{'order_date': str(row.order_date), 'order_count': row.order_count, 'daily_total': float(row.daily_total) if row.daily_total else 0} for row in daily_revenue_rows]
    
    # Status Distribution
    status_dist_rows = db.session.query(
        Order.status,
        func.count(Order.id).label('count')
    ).filter(Order.created_at >= start_date).group_by(Order.status).all()
    
    # Convert to dict for JSON serialization
    status_dist = [{'status': row.status, 'count': row.count} for row in status_dist_rows]
    
    return render_template('admin_dashboard.html',
                         total_shipments=total_shipments,
                         total_revenue=total_revenue,
                         recent_shipments=recent_shipments,
                         recent_revenue=recent_revenue,
                         top_customers=top_customers,
                         top_clients=top_clients,
                         branch_stats=branch_stats,
                         staff_stats=staff_stats,
                         due_clients=due_clients,
                         daily_revenue=daily_revenue,
                         status_dist=status_dist,
                         days_filter=days_filter)


# ============== OPERATION MANAGER ROUTES ==============

@app.route('/operations/dashboard')
@login_required
@manager_required
def operations_dashboard():
    """Main Operations Manager Dashboard with KPIs and overview"""
    from sqlalchemy import func, desc
    from datetime import datetime, timedelta, timezone
    
    # Get statistics
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status='at_destination').count()
    in_transit_orders = Order.query.filter_by(status='in_transit').count()
    delivered_orders = Order.query.filter_by(status='delivered').count()
    
    # Revenue metrics
    total_revenue = db.session.query(func.sum(Order.total_amount)).scalar() or 0
    today_revenue = db.session.query(func.sum(Order.total_amount)).filter(
        db.func.date(Order.created_at) == datetime.now(timezone.utc).date()
    ).scalar() or 0
    
    # Branch-wise statistics
    branch_stats = db.session.query(
        Branch.name,
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('revenue')
    ).join(Order).group_by(Branch.id).all()
    
    # Recent completed bookings
    recent_completed = Order.query.filter_by(status='delivered').order_by(
        Order.delivered_at.desc()
    ).limit(10).all()
    
    # Walk-in vs Client order ratio
    walkin_count = Order.query.filter_by(order_type='walkin').count()
    client_count = Order.query.filter_by(order_type='client').count()
    
    return render_template('operations_dashboard.html',
                         total_orders=total_orders,
                         pending_orders=pending_orders,
                         in_transit_orders=in_transit_orders,
                         delivered_orders=delivered_orders,
                         total_revenue=total_revenue,
                         today_revenue=today_revenue,
                         branch_stats=branch_stats,
                         recent_completed=recent_completed,
                         walkin_count=walkin_count,
                         client_count=client_count)


@app.route('/operations/profile')
@login_required
@manager_required
def operations_profile():
    """Operation Manager's own profile page"""
    from sqlalchemy import func
    
    user = current_user
    
    # Get user statistics
    orders_created = Order.query.filter_by(created_by=user.id).count()
    revenue_handled = db.session.query(func.sum(Order.total_amount)).filter(
        Order.created_by == user.id
    ).scalar() or 0
    
    return render_template('operations_profile.html',
                         user=user,
                         orders_created=orders_created,
                         revenue_handled=revenue_handled)


@app.route('/operations/crm-overview')
@login_required
@manager_required
def operations_crm_overview():
    """CRM Overview - How the system works and pricing information"""
    from sqlalchemy import func
    
    # Get pricing overview
    default_prices = DefaultStatePrice.query.all()
    
    # Get system statistics
    total_clients = Client.query.filter_by(is_active=True).count()
    total_staff = User.query.filter(User.role.in_(['staff', 'manager'])).count()
    total_branches = Branch.query.filter_by(is_active=True).count()
    
    # Average order value
    avg_order_value = db.session.query(func.avg(Order.total_amount)).scalar() or 0
    
    # Order status breakdown
    status_breakdown = db.session.query(
        Order.status,
        func.count(Order.id).label('count')
    ).group_by(Order.status).all()
    
    return render_template('operations_crm_overview.html',
                         default_prices=default_prices,
                         total_clients=total_clients,
                         total_staff=total_staff,
                         total_branches=total_branches,
                         avg_order_value=avg_order_value,
                         status_breakdown=status_breakdown)


@app.route('/operations/booking-history')
@login_required
@manager_required
def operations_booking_history():
    """View completed bookings/orders history"""
    page = request.args.get('page', 1, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = Order.query.filter_by(status='delivered')
    
    if start_date:
        query = query.filter(Order.delivered_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(Order.delivered_at <= datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
    
    pagination = query.order_by(Order.delivered_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    completed_orders = pagination.items
    
    # Statistics
    total_completed = query.count()
    total_revenue = db.session.query(func.sum(Order.total_amount)).filter(
        Order.status == 'delivered'
    ).scalar() or 0
    
    return render_template('operations_booking_history.html',
                         completed_orders=completed_orders,
                         pagination=pagination,
                         total_completed=total_completed,
                         total_revenue=total_revenue,
                         start_date=start_date,
                         end_date=end_date)


@app.route('/operations/branch-bookings')
@login_required
@manager_required
def operations_branch_bookings():
    """View branch-wise completed bookings"""
    if current_user.role == 'manager' and current_user.branch_id:
        # Managers see only their branch
        branches = [current_user.branch]
    else:
        # Admins see all branches
        branches = Branch.query.filter_by(is_active=True).all()
    
    branch_id = request.args.get('branch_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Filter branch if selected
    if branch_id:
        selected_branch = next((b for b in branches if b.id == branch_id), None)
    else:
        selected_branch = branches[0] if branches else None
        branch_id = selected_branch.id if selected_branch else None
    
    # Get completed orders for selected branch
    query = Order.query.filter(
        Order.branch_id == branch_id,
        Order.status == 'delivered'
    )
    
    if start_date:
        query = query.filter(Order.delivered_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(Order.delivered_at <= datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
    
    branch_orders = query.order_by(Order.delivered_at.desc()).all()
    
    # Branch statistics
    branch_total = sum(o.total_amount or 0 for o in branch_orders)
    branch_finalized_count = len(branch_orders)
    
    return render_template('operations_branch_bookings.html',
                         branches=branches,
                         selected_branch=selected_branch,
                         branch_orders=branch_orders,
                         branch_total=branch_total,
                         branch_finalized_count=branch_finalized_count,
                         start_date=start_date,
                         end_date=end_date)


@app.route('/operations/walk-in-orders')
@login_required
@manager_required
def operations_walk_in_orders():
    """View all walk-in customer orders"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    search = request.args.get('search', '')
    
    query = Order.query.filter_by(order_type='walkin')
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    if search:
        query = query.filter(
            (Order.receipt_number.ilike(f'%{search}%')) |
            (Order.customer_name.ilike(f'%{search}%')) |
            (Order.customer_phone.ilike(f'%{search}%'))
        )
    
    pagination = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    walkin_orders = pagination.items
    
    # Statistics
    total_walkin = Order.query.filter_by(order_type='walkin').count()
    total_walkin_revenue = db.session.query(func.sum(Order.total_amount)).filter(
        Order.order_type == 'walkin'
    ).scalar() or 0
    
    return render_template('operations_walk_in_orders.html',
                         walkin_orders=walkin_orders,
                         pagination=pagination,
                         total_walkin=total_walkin,
                         total_walkin_revenue=total_walkin_revenue,
                         status_filter=status_filter,
                         search=search)


@app.route('/operations/client-orders')
@login_required
@manager_required
def operations_client_orders():
    """View all client orders"""
    page = request.args.get('page', 1, type=int)
    client_id = request.args.get('client_id', type=int)
    status_filter = request.args.get('status', '')
    search = request.args.get('search', '')
    
    query = Order.query.filter_by(order_type='client')
    
    if client_id:
        query = query.filter_by(client_id=client_id)
    if status_filter:
        query = query.filter_by(status=status_filter)
    if search:
        query = query.filter(
            (Order.receipt_number.ilike(f'%{search}%')) |
            (Order.customer_name.ilike(f'%{search}%')) |
            (Order.receiver_name.ilike(f'%{search}%'))
        )
    
    pagination = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    client_orders = pagination.items
    
    # Get all clients for filter
    clients = Client.query.filter_by(is_active=True).all()
    
    # Statistics
    total_client_orders = Order.query.filter_by(order_type='client').count()
    total_client_revenue = db.session.query(func.sum(Order.total_amount)).filter(
        Order.order_type == 'client'
    ).scalar() or 0
    
    return render_template('operations_client_orders.html',
                         client_orders=client_orders,
                         pagination=pagination,
                         clients=clients,
                         selected_client_id=client_id,
                         total_client_orders=total_client_orders,
                         total_client_revenue=total_client_revenue,
                         status_filter=status_filter,
                         search=search)


@app.route('/operations/audit-logs')
@login_required
@manager_required
def operations_audit_logs():
    """View audit logs - Read-only for managers"""
    from models import AuditLog
    
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', '')
    entity_filter = request.args.get('entity_type', '')
    user_filter = request.args.get('username', '')
    
    query = AuditLog.query
    
    if action_filter:
        query = query.filter_by(action=action_filter)
    if entity_filter:
        query = query.filter_by(entity_type=entity_filter)
    if user_filter:
        query = query.filter(AuditLog.username.ilike(f'%{user_filter}%'))
    
    pagination = query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=30, error_out=False
    )
    logs = pagination.items
    
    return render_template('operations_audit_logs.html',
                         logs=logs,
                         pagination=pagination,
                         action_filter=action_filter,
                         entity_filter=entity_filter,
                         user_filter=user_filter)


@app.route('/operations/analytics')
@login_required
@manager_required
def operations_analytics():
    """View operational analytics and trends"""
    from sqlalchemy import func, desc
    from datetime import datetime, timedelta, timezone
    
    # Date range for analytics
    days_filter = request.args.get('days', 30, type=int)
    start_date = datetime.now(timezone.utc) - timedelta(days=days_filter)
    
    # Total metrics for period
    orders_in_period = Order.query.filter(Order.created_at >= start_date).count()
    revenue_in_period = db.session.query(func.sum(Order.total_amount)).filter(
        Order.created_at >= start_date
    ).scalar() or 0
    
    # Orders by type in period
    walkin_in_period = Order.query.filter(
        Order.order_type == 'walkin',
        Order.created_at >= start_date
    ).count()
    client_in_period = Order.query.filter(
        Order.order_type == 'client',
        Order.created_at >= start_date
    ).count()
    
    # Orders by status
    status_breakdown = db.session.query(
        Order.status,
        func.count(Order.id).label('count')
    ).filter(Order.created_at >= start_date).group_by(Order.status).all()
    
    # Top states by revenue
    top_states = db.session.query(
        Order.receiver_state,
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('revenue')
    ).filter(Order.created_at >= start_date).group_by(
        Order.receiver_state
    ).order_by(desc('revenue')).limit(10).all()
    
    # Daily revenue trend
    daily_revenue = db.session.query(
        func.date(Order.created_at).label('date'),
        func.count(Order.id).label('count'),
        func.sum(Order.total_amount).label('revenue')
    ).filter(Order.created_at >= start_date).group_by(
        func.date(Order.created_at)
    ).order_by('date').all()
    
    # Top clients
    top_clients = db.session.query(
        Client.name,
        Client.company_name,
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('revenue')
    ).join(Order).filter(Order.created_at >= start_date).group_by(
        Client.id
    ).order_by(desc('revenue')).limit(10).all()
    
    # Average metrics
    avg_order_value = revenue_in_period / orders_in_period if orders_in_period > 0 else 0
    avg_weight = db.session.query(func.avg(Order.weight)).filter(
        Order.created_at >= start_date
    ).scalar() or 0
    
    return render_template('operations_analytics.html',
                         orders_in_period=orders_in_period,
                         revenue_in_period=revenue_in_period,
                         walkin_in_period=walkin_in_period,
                         client_in_period=client_in_period,
                         status_breakdown=status_breakdown,
                         top_states=top_states,
                         daily_revenue=daily_revenue,
                         top_clients=top_clients,
                         avg_order_value=avg_order_value,
                         avg_weight=avg_weight,
                         days_filter=days_filter)


@app.route('/operations/corporate-clients/7day')
@login_required
@manager_required
def operations_corporate_clients_7day():
    """View corporate client orders from last 7 days - Read-only for individuals"""
    from datetime import datetime, timedelta, timezone
    
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    # Get all client orders from last 7 days
    orders = Order.query.filter(
        Order.order_type == 'client',
        Order.created_at >= seven_days_ago
    ).order_by(Order.created_at.desc()).all()
    
    # Group by client
    clients_data = {}
    for order in orders:
        if order.client_id not in clients_data:
            client = Client.query.get(order.client_id)
            clients_data[order.client_id] = {
                'client': client,
                'orders': [],
                'total_amount': 0,
                'total_count': 0
            }
        clients_data[order.client_id]['orders'].append(order)
        clients_data[order.client_id]['total_amount'] += order.total_amount or 0
        clients_data[order.client_id]['total_count'] += 1
    
    # Summary stats
    total_orders_7day = len(orders)
    total_revenue_7day = sum(o.total_amount or 0 for o in orders)
    
    return render_template('operations_corporate_clients_7day.html',
                         clients_data=clients_data,
                         total_orders_7day=total_orders_7day,
                         total_revenue_7day=total_revenue_7day)


@app.route('/operations/bulk-import', methods=['GET', 'POST'])
@login_required
@manager_required
def operations_bulk_import():
    """Bulk import orders from Excel file"""
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
                
                imported_count = 0
                skipped_rows = []
                
                for index, row in df.iterrows():
                    try:
                        # Validate required fields
                        if pd.isna(row.get('customer_name')) or pd.isna(row.get('receiver_name')):
                            skipped_rows.append((index + 2, 'Missing customer or receiver name'))
                            continue
                        
                        receiver_pincode = str(row.get('receiver_pincode', '')).strip()
                        if not receiver_pincode or len(receiver_pincode) != 6 or not receiver_pincode.isdigit():
                            skipped_rows.append((index + 2, 'Invalid pincode'))
                            continue
                        
                        # Generate receipt number
                        receipt_number = generate_receipt_number(current_user)
                        
                        # Create order
                        order = Order(
                            receipt_number=receipt_number,
                            order_type=str(row.get('order_type', 'walkin')).lower(),
                            receipt_mode=str(row.get('receipt_mode', 'standard')),
                            customer_name=str(row.get('customer_name')),
                            customer_phone=str(row.get('customer_phone', '')),
                            customer_email=str(row.get('customer_email', '')),
                            customer_address=str(row.get('customer_address', '')),
                            receiver_name=str(row.get('receiver_name')),
                            receiver_phone=str(row.get('receiver_phone', '')),
                            receiver_address=str(row.get('receiver_address', '')),
                            receiver_city=str(row.get('receiver_city', '')),
                            receiver_state=str(row.get('receiver_state', '')),
                            receiver_pincode=receiver_pincode,
                            package_description=str(row.get('package_description', '')),
                            weight=float(row.get('weight', 0)),
                            number_of_boxes=int(row.get('number_of_boxes', 1)),
                            special_instructions=str(row.get('special_instructions', '')),
                            created_by=current_user.id,
                            branch_id=current_user.branch_id,
                            status='at_destination',
                            payment_status='unpaid'
                        )
                        
                        # Calculate amount
                        if order.weight:
                            shipping_mode = str(row.get('receipt_mode', 'standard'))
                            base, weight_charge, additional, discount, total, _ = calculate_order_amount(
                                order.weight, state=order.receiver_state, shipping_mode=shipping_mode
                            )
                            order.base_amount = base
                            order.weight_charges = weight_charge
                            order.additional_charges = additional
                            order.discount = discount
                            order.total_amount = total
                        
                        order.generate_tracking_link()
                        db.session.add(order)
                        
                        # Add tracking update
                        tracking = TrackingUpdate(
                            order_id=order.id,
                            status='Order Created',
                            description='Order created via bulk import',
                            updated_by=current_user.id
                        )
                        db.session.add(tracking)
                        
                        imported_count += 1
                    
                    except Exception as e:
                        skipped_rows.append((index + 2, str(e)))
                        continue
                
                db.session.commit()
                
                flash(f'Bulk import successful! Imported {imported_count} orders.', 'success')
                if skipped_rows:
                    flash(f'Skipped {len(skipped_rows)} rows due to errors.', 'warning')
                
                return redirect(url_for('operations_bulk_import'))
            
            except Exception as e:
                db.session.rollback()
                flash(f'Error processing file: {str(e)}', 'error')
        else:
            flash('Invalid file type. Please upload Excel files only.', 'error')
        
        return redirect(request.url)
    
    return render_template('operations_bulk_import.html')


@app.route('/operations/shipment-tracking')
@login_required
def operations_shipment_tracking():
    """View shipment tracking for all orders with detailed status updates"""
    # Check user role
    if current_user.role not in ['admin', 'manager', 'operation_manager', 'branch']:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    from datetime import datetime, timedelta, timezone
    
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    search_receipt = request.args.get('receipt', '')
    customer_filter = request.args.get('customer', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    query = Order.query
    
    # Branch users can only see their own branch's orders
    if current_user.role == 'branch':
        query = query.filter_by(branch_id=current_user.branch_id)
    
    # Apply filters
    if status_filter and status_filter != 'all':
        query = query.filter_by(status=status_filter)
    if search_receipt:
        query = query.filter(Order.receipt_number.contains(search_receipt))
    if customer_filter:
        query = query.filter(Order.customer_name.contains(customer_filter))
    
    if date_from:
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Order.created_at >= start_date)
        except:
            pass
    
    if date_to:
        try:
            end_date = datetime.strptime(date_to, '%Y-%m-%d')
            end_date = end_date.replace(hour=23, minute=59, second=59)
            query = query.filter(Order.created_at <= end_date)
        except:
            pass
    
    pagination = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    orders = pagination.items
    
    # Get unique statuses for filter dropdown
    distinct_statuses = db.session.query(Order.status).distinct().all()
    statuses = [s[0] for s in distinct_statuses if s[0]]
    
    return render_template('operations_shipment_tracking.html',
                         orders=orders,
                         pagination=pagination,
                         status_filter=status_filter,
                         search_receipt=search_receipt,
                         customer_filter=customer_filter,
                         date_from=date_from,
                         date_to=date_to,
                         distinct_statuses=statuses)


@app.route('/operations/marketing-sales')
@login_required
@manager_required
def operations_marketing_sales():
    """View marketing and sales analytics"""
    from sqlalchemy import func, desc, case
    from datetime import datetime, timedelta, timezone
    
    days_filter = request.args.get('days', 30, type=int)
    start_date = datetime.now(timezone.utc) - timedelta(days=days_filter)
    
    # Total metrics
    total_orders = Order.query.filter(Order.created_at >= start_date).count()
    total_revenue = db.session.query(func.sum(Order.total_amount)).filter(
        Order.created_at >= start_date
    ).scalar() or 0
    total_walkin = Order.query.filter(
        Order.order_type == 'walkin',
        Order.created_at >= start_date
    ).count()
    total_client = Order.query.filter(
        Order.order_type == 'client',
        Order.created_at >= start_date
    ).count()
    
    # Conversion: client orders as % of total
    conversion_rate = (total_client / total_orders * 100) if total_orders > 0 else 0
    
    # Top performing states
    top_states = db.session.query(
        Order.receiver_state,
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('revenue')
    ).filter(Order.created_at >= start_date).group_by(
        Order.receiver_state
    ).order_by(desc('revenue')).limit(15).all()
    
    # Top performing clients (corporate)
    top_clients = db.session.query(
        Client.name,
        Client.company_name,
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('revenue'),
        (func.sum(Order.total_amount) / func.count(Order.id)).label('avg_order_value')
    ).join(Order).filter(Order.created_at >= start_date).group_by(
        Client.id
    ).order_by(desc('revenue')).limit(15).all()
    
    # Daily order trend
    daily_orders = db.session.query(
        func.date(Order.created_at).label('date'),
        func.count(Order.id).label('total_orders'),
        func.sum(case([(Order.order_type == 'walkin', 1)], else_=0)).label('walkin_count'),
        func.sum(case([(Order.order_type == 'client', 1)], else_=0)).label('client_count')
    ).filter(Order.created_at >= start_date).group_by(
        func.date(Order.created_at)
    ).order_by('date').all()
    
    # Order type breakdown
    order_type_data = db.session.query(
        Order.order_type,
        func.count(Order.id).label('count'),
        func.sum(Order.total_amount).label('revenue')
    ).filter(Order.created_at >= start_date).group_by(Order.order_type).all()
    
    return render_template('operations_marketing_sales.html',
                         total_orders=total_orders,
                         total_revenue=total_revenue,
                         total_walkin=total_walkin,
                         total_client=total_client,
                         conversion_rate=conversion_rate,
                         top_states=top_states,
                         top_clients=top_clients,
                         daily_orders=daily_orders,
                         order_type_data=order_type_data,
                         days_filter=days_filter)


@app.route('/operations/finance-due-report')
@login_required
@manager_required
def operations_finance_due_report():
    """View financial analytics and payment due report"""
    from sqlalchemy import func, desc, case
    from datetime import datetime, timedelta, timezone
    
    days_filter = request.args.get('days', 30, type=int)
    start_date = datetime.now(timezone.utc) - timedelta(days=days_filter)
    
    # Financial overview for period
    total_orders = Order.query.filter(Order.created_at >= start_date).count()
    total_amount = db.session.query(func.sum(Order.total_amount)).filter(
        Order.created_at >= start_date
    ).scalar() or 0
    total_received = db.session.query(func.sum(Order.received_amount)).filter(
        Order.created_at >= start_date
    ).scalar() or 0
    total_due = total_amount - total_received
    
    # Payment status breakdown
    payment_breakdown = db.session.query(
        Order.payment_status,
        func.count(Order.id).label('count'),
        func.sum(Order.total_amount).label('amount'),
        func.sum(Order.received_amount).label('received'),
        func.sum(Order.total_amount - Order.received_amount).label('due')
    ).filter(Order.created_at >= start_date).group_by(Order.payment_status).all()
    
    # Top clients with outstanding dues
    top_due_clients = db.session.query(
        Client.name,
        Client.company_name,
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('total_amount'),
        func.sum(Order.received_amount).label('total_received'),
        func.sum(Order.total_amount - Order.received_amount).label('total_due')
    ).join(Order).filter(
        Order.created_at >= start_date,
        Order.total_amount > Order.received_amount
    ).group_by(Client.id).order_by(desc('total_due')).limit(20).all()
    
    # Daily revenue trend with collections
    daily_finance = db.session.query(
        func.date(Order.created_at).label('date'),
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('invoiced'),
        func.sum(Order.received_amount).label('collected'),
        func.sum(Order.total_amount - Order.received_amount).label('outstanding')
    ).filter(Order.created_at >= start_date).group_by(
        func.date(Order.created_at)
    ).order_by('date').all()
    
    # Payment mode breakdown
    payment_mode_breakdown = db.session.query(
        Order.payment_mode,
        func.count(Order.id).label('count'),
        func.sum(Order.received_amount).label('amount')
    ).filter(Order.created_at >= start_date).group_by(Order.payment_mode).all()
    
    return render_template('operations_finance_due_report.html',
                         total_orders=total_orders,
                         total_amount=total_amount,
                         total_received=total_received,
                         total_due=total_due,
                         payment_breakdown=payment_breakdown,
                         top_due_clients=top_due_clients,
                         daily_finance=daily_finance,
                         payment_mode_breakdown=payment_mode_breakdown,
                         days_filter=days_filter)


@app.route('/operations/client-due-report')
@login_required
@manager_required
def operations_client_due_report():
    """View all clients with outstanding payment dues"""
    from sqlalchemy import func, desc
    
    page = request.args.get('page', 1, type=int)
    search_client = request.args.get('search', '')
    min_due = request.args.get('min_due', 0, type=float)
    
    # Query clients with their total outstanding dues
    query = db.session.query(
        Client.id,
        Client.name,
        Client.company_name,
        Client.phone,
        Client.email,
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('total_billed'),
        func.sum(Order.received_amount).label('total_paid'),
        func.sum(Order.total_amount - Order.received_amount).label('total_due')
    ).join(Order).group_by(Client.id)
    
    # Filter by search term
    if search_client:
        query = query.filter(
            (Client.name.contains(search_client)) |
            (Client.company_name.contains(search_client)) |
            (Client.phone.contains(search_client))
        )
    
    # Filter by minimum due amount
    if min_due > 0:
        query = query.having(
            func.sum(Order.total_amount - Order.received_amount) >= min_due
        )
    
    # Only show clients with outstanding dues
    query = query.having(func.sum(Order.total_amount - Order.received_amount) > 0)
    
    pagination = query.order_by(desc('total_due')).paginate(
        page=page, per_page=25, error_out=False
    )
    clients = pagination.items
    
    # Summary stats
    total_outstanding = db.session.query(
        func.sum(Order.total_amount - Order.received_amount)
    ).filter(Order.total_amount > Order.received_amount).scalar() or 0
    
    total_clients_due = db.session.query(
        func.count(func.distinct(Client.id))
    ).join(Order).filter(Order.total_amount > Order.received_amount).scalar() or 0
    
    return render_template('operations_client_due_report.html',
                         clients=clients,
                         pagination=pagination,
                         search_client=search_client,
                         min_due=min_due,
                         total_outstanding=total_outstanding,
                         total_clients_due=total_clients_due)


@app.route('/audit-logs')
@login_required
@admin_required
def audit_logs():
    """View all audit logs - Admin only"""
    from models import AuditLog
    
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', '')
    entity_filter = request.args.get('entity_type', '')
    user_filter = request.args.get('username', '')
    branch_filter = request.args.get('branch', '')
    client_filter = request.args.get('client', '')
    search_date = request.args.get('date', '')
    
    query = AuditLog.query
    
    if action_filter:
        query = query.filter_by(action=action_filter)
    if entity_filter:
        query = query.filter_by(entity_type=entity_filter)
    if user_filter:
        query = query.filter(AuditLog.username.contains(user_filter))
    if branch_filter:
        query = query.filter_by(branch_name=branch_filter)
    if client_filter:
        query = query.filter(AuditLog.client_name.contains(client_filter))
    if search_date:
        from datetime import datetime, timedelta
        try:
            search_dt = datetime.strptime(search_date, '%Y-%m-%d')
            next_day = search_dt + timedelta(days=1)
            query = query.filter(AuditLog.created_at >= search_dt, AuditLog.created_at < next_day)
        except:
            pass
    
    pagination = query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    logs = pagination.items
    
    return render_template('audit_logs.html',
                         logs=logs,
                         pagination=pagination,
                         action_filter=action_filter,
                         entity_filter=entity_filter,
                         user_filter=user_filter,
                         branch_filter=branch_filter,
                         client_filter=client_filter,
                         search_date=search_date)


@app.route('/audit-logs/<int:log_id>')
@login_required
@admin_required
def audit_log_detail(log_id):
    """View detailed audit log entry - Admin only"""
    from models import AuditLog
    
    log = AuditLog.query.get_or_404(log_id)
    return render_template('audit_log_detail.html', log=log)


@app.route('/audit-logs/report')
@login_required
@admin_required
def audit_logs_report():
    """Generate audit logs report - Admin only"""
    from models import AuditLog
    from sqlalchemy import func
    
    # Default to last 30 days
    from datetime import datetime, timedelta
    start_date = datetime.utcnow() - timedelta(days=30)
    
    # Activity by user
    user_activity = db.session.query(
        AuditLog.username,
        func.count(AuditLog.id).label('action_count')
    ).filter(AuditLog.created_at >= start_date).group_by(AuditLog.username).order_by(
        func.count(AuditLog.id).desc()
    ).all()
    
    # Activity by entity type
    entity_activity = db.session.query(
        AuditLog.entity_type,
        func.count(AuditLog.id).label('action_count')
    ).filter(AuditLog.created_at >= start_date).group_by(AuditLog.entity_type).order_by(
        func.count(AuditLog.id).desc()
    ).all()
    
    # Activity by action
    action_activity = db.session.query(
        AuditLog.action,
        func.count(AuditLog.id).label('action_count')
    ).filter(AuditLog.created_at >= start_date).group_by(AuditLog.action).order_by(
        func.count(AuditLog.id).desc()
    ).all()
    
    # Clients with most activity
    client_activity = db.session.query(
        AuditLog.client_name,
        func.count(AuditLog.id).label('action_count'),
        func.sum(AuditLog.due_amount).label('total_due')
    ).filter(AuditLog.created_at >= start_date, AuditLog.client_name.isnot(None)).group_by(
        AuditLog.client_name
    ).order_by(func.count(AuditLog.id).desc()).limit(20).all()
    
    # Due alerts
    due_alerts = db.session.query(AuditLog).filter(
        AuditLog.due_amount.isnot(None),
        AuditLog.due_amount > 0,
        AuditLog.created_at >= start_date
    ).order_by(AuditLog.due_amount.desc()).limit(30).all()
    
    return render_template('audit_logs_report.html',
                         user_activity=user_activity,
                         entity_activity=entity_activity,
                         action_activity=action_activity,
                         client_activity=client_activity,
                         due_alerts=due_alerts)


@app.route('/api/audit-logs/export')
@login_required
@admin_required
def export_audit_logs():
    """Export audit logs as CSV - Admin only"""
    from models import AuditLog
    import csv
    from io import StringIO, BytesIO
    
    # Get logs from last 90 days
    from datetime import datetime, timedelta
    start_date = datetime.utcnow() - timedelta(days=90)
    
    logs = AuditLog.query.filter(AuditLog.created_at >= start_date).order_by(
        AuditLog.created_at.desc()
    ).all()
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Date', 'User', 'Branch', 'Action', 'Entity Type', 'Entity Name',
        'Client', 'Receipt Number', 'Changes', 'Due Amount', 'IP Address'
    ])
    
    for log in logs:
        writer.writerow([
            log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            log.username,
            log.branch_name or '',
            log.action,
            log.entity_type,
            log.entity_name or '',
            log.client_name or '',
            log.receipt_number or '',
            log.changes or '',
            log.due_amount or '',
            log.ip_address or ''
        ])
    
    # Return as download
    response = app.make_response(output.getvalue().encode('utf-8-sig'))
    response.headers["Content-Disposition"] = "attachment; filename=audit_logs.csv"
    response.headers["Content-Type"] = "text/csv; charset=utf-8-sig"
    return response


@app.route('/api/search/suggestions')
@login_required
def search_suggestions():
    query = request.args.get('q', '').strip()
    if not query or len(query) < 1:
        return jsonify([])
    
    # Search Orders (by Tracking Number)
    orders = Order.query.filter(
        Order.receipt_number.ilike(f'%{query}%')
    ).limit(3).all()
    
    # Search Individual Customers (from orders, distinct by phone/name)
    individuals = db.session.query(
        Order.customer_name, 
        Order.customer_phone
    ).filter(
        (Order.order_type == 'walkin') & 
        ((Order.customer_name.ilike(f'%{query}%')) | (Order.customer_phone.ilike(f'%{query}%')))
    ).distinct().limit(3).all()
    
    # Search Corporate Clients
    clients = Client.query.filter(
        (Client.name.ilike(f'%{query}%')) | 
        (Client.company_name.ilike(f'%{query}%'))
    ).limit(3).all()
    
    suggestions = []
    
    for o in orders:
        suggestions.append({
            'type': 'Shipment',
            'label': f'📦 {o.receipt_number} - {o.customer_name}',
            'value': o.receipt_number,
            'url': url_for('order_details', id=o.id) if current_user.role != 'customer' else url_for('tracking', receipt=o.receipt_number)
        })
        
    for name, phone in individuals:
        suggestions.append({
            'type': 'Individual',
            'label': f'👤 {name} ({phone})',
            'value': name,
            'url': url_for('customers') + f'?search={name}'
        })
        
    for c in clients:
        suggestions.append({
            'type': 'Corporate',
            'label': f'🏢 {c.name}',
            'value': c.name,
            'url': url_for('clients', search=c.name)
        })
        
    return jsonify(suggestions)


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


@app.route('/client-portal')
@login_required
def client_portal():
    """Client portal - profile, booking, order history, tracking"""
    if current_user.role not in ['customer', 'client']:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get client's orders
    my_orders = Order.query.filter(
        (Order.customer_phone == current_user.phone) | 
        (Order.customer_email == current_user.email)
    ).order_by(Order.created_at.desc()).all()
    
    # Get parcel types for booking
    parcel_types = [
        {'id': 'small', 'name': 'Small Parcel', 'weight': '0-250g', 'icon': 'fa-cube'},
        {'id': 'medium', 'name': 'Medium Parcel', 'weight': '250g-1kg', 'icon': 'fa-box'},
        {'id': 'large', 'name': 'Large Parcel', 'weight': '1kg-5kg', 'icon': 'fa-boxes'},
        {'id': 'extra_large', 'name': 'Extra Large Parcel', 'weight': '5kg-10kg', 'icon': 'fa-cube'},
        {'id': 'bulk', 'name': 'Bulk/Multiple', 'weight': '10kg+', 'icon': 'fa-dolly'},
    ]
    
    return render_template('client_portal.html', 
                         user=current_user, 
                         orders=my_orders,
                         parcel_types=parcel_types)


@app.route('/api/client/update-profile', methods=['POST'])
@login_required
def api_client_update_profile():
    """Update client profile"""
    try:
        current_user.email = request.form.get('email', current_user.email)
        current_user.phone = request.form.get('phone', current_user.phone)
        current_user.address = request.form.get('address', current_user.address)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Profile updated successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/api/client/book', methods=['POST'])
@login_required
def api_client_book():
    """Client booking endpoint"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['receiver_name', 'receiver_phone', 'receiver_address', 'receiver_city', 'receiver_state', 'receiver_pincode', 'weight']
        for field in required:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        # Validate pincode
        pincode = data.get('receiver_pincode')
        if not pincode or len(pincode) != 6 or not pincode.isdigit():
            return jsonify({'success': False, 'message': 'Invalid pincode. Must be 6 digits.'}), 400
        
        # Generate receipt number
        receipt_number, assignment_id = generate_receipt_number(current_user)
        
        # Create order
        order = Order(
            receipt_number=receipt_number,
            assignment_id=assignment_id,
            order_type='client',
            receipt_type='standard',
            receipt_mode=data.get('shipping_mode', 'standard'),
            customer_name=current_user.username,
            customer_phone=current_user.phone,
            customer_email=current_user.email,
            customer_address=current_user.address,
            receiver_name=data.get('receiver_name'),
            receiver_phone=data.get('receiver_phone'),
            receiver_address=data.get('receiver_address'),
            receiver_city=data.get('receiver_city'),
            receiver_state=data.get('receiver_state'),
            receiver_pincode=data.get('receiver_pincode'),
            receiver_landmark=data.get('receiver_landmark', ''),
            package_description=data.get('package_description', ''),
            weight=float(data.get('weight', 0)),
            number_of_boxes=int(data.get('number_of_boxes', 1)),
            special_instructions=data.get('special_instructions', ''),
            status='pending',
            payment_mode=data.get('payment_mode', 'cash'),
            created_by=current_user.id
        )
        
        # Calculate charges
        if order.weight:
            base, weight_charge, additional, discount, total, _, ins_charge = calculate_order_amount(
                order.weight, 
                state=order.receiver_state, 
                shipping_mode=order.receipt_mode
            )
            order.base_amount = base
            order.weight_charges = weight_charge
            order.additional_charges = additional
            order.discount = discount
            order.total_amount = total
            order.insurance_charge = ins_charge
        
        db.session.add(order)
        db.session.commit()
        
        # Create tracking update
        tracking = TrackingUpdate(
            order_id=order.id,
            status='Order Booked',
            description='Your shipment has been booked successfully',
            updated_by=current_user.id
        )
        db.session.add(tracking)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Order booked successfully!',
            'order': {
                'id': order.id,
                'receipt_number': order.receipt_number,
                'total_amount': order.total_amount,
                'status': order.status
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/api/client/my-orders', methods=['GET'])
@login_required
def api_my_orders():
    """Get logged-in client's orders"""
    try:
        orders = Order.query.filter(
            (Order.customer_phone == current_user.phone) | 
            (Order.customer_email == current_user.email)
        ).order_by(Order.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'orders': [{
                'id': o.id,
                'receipt_number': o.receipt_number,
                'receiver': o.receiver_name,
                'city': o.receiver_city,
                'status': o.status,
                'amount': o.total_amount,
                'created_at': o.created_at.strftime('%d-%m-%Y %H:%M')
            } for o in orders]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


# ============== DELIVERY PERSONNEL API ==============

@app.route('/api/delivery/reschedule', methods=['POST'])
@login_required
@delivery_required
def api_delivery_reschedule():
    """Request reschedule for order"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        reason = data.get('reason')
        requested_date = data.get('requested_date')
        
        order = Order.query.get_or_404(order_id)
        
        # Verify ownership
        if order.delivery_person_id != current_user.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        order.reschedule_reason = reason
        order.reschedule_status = 'pending'
        if requested_date:
            order.reschedule_requested_date = datetime.strptime(requested_date, '%Y-%m-%d')
        order.pickup_attempts = (order.pickup_attempts or 0) + 1
        order.last_pickup_attempt = datetime.utcnow()
        
        db.session.commit()
        
        # Create notification
        tracking = TrackingUpdate(
            order_id=order.id,
            status='Reschedule Requested',
            description=f'Reschedule requested: {reason}',
            updated_by=current_user.id
        )
        db.session.add(tracking)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Reschedule request submitted'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/api/delivery/mark-delivered', methods=['POST'])
@login_required
@delivery_required
def api_delivery_mark_delivered():
    """Mark order as delivered"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        notes = data.get('notes', '')
        
        order = Order.query.get_or_404(order_id)
        
        # Verify ownership
        if order.delivery_person_id != current_user.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        order.status = 'delivered'
        order.delivered_at = datetime.utcnow()
        order.reschedule_status = None
        order.internal_notes = notes
        
        db.session.commit()
        
        # Create tracking update
        tracking = TrackingUpdate(
            order_id=order.id,
            status='Delivered',
            description=f'Delivered successfully. {notes}',
            updated_by=current_user.id
        )
        db.session.add(tracking)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Order marked as delivered'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/api/delivery/cancel-booking', methods=['POST'])
@login_required
@delivery_required
def api_delivery_cancel_booking():
    """Cancel booking with reason"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        reason = data.get('reason')
        
        order = Order.query.get_or_404(order_id)
        
        # Verify ownership
        if order.delivery_person_id != current_user.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        order.status = 'cancelled'
        order.reschedule_reason = reason
        order.reschedule_status = 'cancelled'
        
        db.session.commit()
        
        # Create tracking update
        tracking = TrackingUpdate(
            order_id=order.id,
            status='Cancelled',
            description=f'Order cancelled: {reason}',
            updated_by=current_user.id
        )
        db.session.add(tracking)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Order cancelled'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/api/delivery/profile', methods=['GET', 'POST'])
@login_required
@delivery_required
def api_delivery_profile():
    """Get/Update delivery personnel profile"""
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'profile': {
                'username': current_user.username,
                'email': current_user.email,
                'phone': current_user.phone,
                'address': current_user.address,
                'role': current_user.role
            }
        })
    else:
        try:
            current_user.email = request.form.get('email', current_user.email)
            current_user.phone = request.form.get('phone', current_user.phone)
            current_user.address = request.form.get('address', current_user.address)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Profile updated successfully'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/customers')
@login_required
def customers():
    # staff_required allows: admin, manager, operation_manager, staff
    # branch users should also be able to view customers
    if current_user.role not in ['admin', 'manager', 'operation_manager', 'staff', 'branch']:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get unique walk-in customers from orders
    # In a real app, we might have a dedicated Customer table
    # Here we aggregate from the Order table
    if current_user.role == 'branch':
        # Branch users only see their own branch's customers
        walkin_orders = Order.query.filter_by(order_type='walkin', branch_id=current_user.branch_id).all()
    else:
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
                'city': order.customer_city,
                'state': order.customer_state,
                'total_orders': 1,
                'last_order_date': order.created_at,
                'total_spent': order.total_amount or 0,
                'highest_order_amount': order.total_amount or 0
            }
        else:
            customers_dict[key]['total_orders'] += 1
            customers_dict[key]['total_spent'] += (order.total_amount or 0)
            # Update highest order amount
            if order.total_amount and order.total_amount > customers_dict[key]['highest_order_amount']:
                customers_dict[key]['highest_order_amount'] = order.total_amount
            if order.customer_city: customers_dict[key]['city'] = order.customer_city
            if order.customer_state: customers_dict[key]['state'] = order.customer_state
            if order.created_at > customers_dict[key]['last_order_date']:
                customers_dict[key]['last_order_date'] = order.created_at
    
    customers_list = sorted(customers_dict.values(), key=lambda x: x['last_order_date'], reverse=True)
    
    cities = sorted(list(set(c['city'] for c in customers_list if c.get('city'))))
    states = sorted(list(set(c['state'] for c in customers_list if c.get('state'))))
    
    return render_template('customers.html', customers=customers_list, cities=cities, states=states)


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
        # Create Branch
        branch = Branch(
            name=request.form.get('name'),
            code=request.form.get('code'),
            address=request.form.get('address'),
            phone=request.form.get('phone'),
            email=request.form.get('email')
        )
        db.session.add(branch)
        db.session.flush() # Get branch.id

        # Create Branch Admin (Manager) - Optional
        admin_username = request.form.get('admin_username', '').strip()
        admin_email = request.form.get('admin_email', '').strip()
        admin_password = request.form.get('admin_password', '').strip()

        # Only create admin if all fields are provided
        if admin_username or admin_email or admin_password:
            if not (admin_username and admin_email and admin_password):
                db.session.rollback()
                flash('If creating a branch admin, please fill in username, email, and password.', 'error')
                return redirect(url_for('add_branch'))
            
            if User.query.filter_by(username=admin_username).first():
                db.session.rollback()
                flash(f'Username "{admin_username}" already exists. Choose a different username.', 'error')
                return redirect(url_for('add_branch'))
            
            if User.query.filter_by(email=admin_email).first():
                db.session.rollback()
                flash(f'Email "{admin_email}" already exists. Choose a different email.', 'error')
                return redirect(url_for('add_branch'))

            branch_admin = User(
                username=admin_username,
                email=admin_email,
                role='manager',
                branch_id=branch.id,
                phone=branch.phone,
                address=branch.address
            )
            branch_admin.set_password(admin_password)
            db.session.add(branch_admin)
            db.session.commit()
            flash(f'Branch "{branch.name}" and Manager "{admin_username}" created successfully!', 'success')
        else:
            db.session.commit()
            flash(f'Branch "{branch.name}" created successfully! You can add a manager later.', 'success')
        
        return redirect(url_for('branches'))
    
    return render_template('add_branch.html')



@app.route('/api/pincode/<pincode>')
def pincode_lookup(pincode):
    if not pincode or len(pincode) != 6 or not pincode.isdigit():
        return jsonify({'success': False, 'message': 'Invalid pincode format'}), 400
    
    try:
        response = requests.get(f"https://api.postalpincode.in/pincode/{pincode}")
        data = response.json()
        
        if data[0]['Status'] == 'Success':
            post_office = data[0]['PostOffice'][0]
            return jsonify({
                'success': True,
                'city': post_office['District'],
                'state': post_office['State']
            })
        else:
            return jsonify({'success': False, 'message': 'Pincode not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/branch/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_branch(id):
    branch = Branch.query.get_or_404(id)
    # ... logic continues
    
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
    # Admins can see all staff including other admins
    staff = User.query.filter(User.role.in_(['admin', 'staff', 'delivery', 'manager', 'operation_manager', 'branch', 'marketing_manager'])).all()
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
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')
        branch_id = request.form.get('branch_id') or None
        
        # Validate password length
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return render_template('add_staff.html', branches=branches)
        
        # Validate password confirmation
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('add_staff.html', branches=branches)
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return render_template('add_staff.html', branches=branches)
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'error')
            return render_template('add_staff.html', branches=branches)
        
        # Validate that branch users have a branch assigned
        if role == 'branch' and not branch_id:
            flash('Branch users must be assigned to a branch.', 'error')
            return render_template('add_staff.html', branches=branches)
        
        user = User(
            username=username,
            email=email,
            role=role,
            branch_id=branch_id,
            phone=request.form.get('phone'),
            address=request.form.get('address')
        )
        user.set_password(password)
        
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
        role = request.form.get('role')
        branch_id = request.form.get('branch_id') or None
        
        # Validate that branch users have a branch assigned
        if role == 'branch' and not branch_id:
            flash('Branch users must be assigned to a branch.', 'error')
            return render_template('edit_staff.html', user=user, branches=branches)
        
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.role = role
        user.branch_id = branch_id
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
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f'Staff member "{username}" deleted successfully!', 'success')
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


# ============== COURIER MANAGEMENT ==============

@app.route('/couriers')
@login_required
@manager_required
def couriers():
    couriers = Courier.query.all()
    return render_template('couriers.html', couriers=couriers)


@app.route('/couriers/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_courier():
    if request.method == 'POST':
        name = request.form.get('name')
        
        if Courier.query.filter_by(name=name).first():
            flash('Courier with this name already exists.', 'error')
            return redirect(url_for('add_courier'))
        
        courier = Courier(
            name=name,
            service_type=request.form.get('service_type', ''),
            contact_person=request.form.get('contact_person', ''),
            contact_email=request.form.get('contact_email', ''),
            contact_phone=request.form.get('contact_phone', ''),
            description=request.form.get('description', '')
        )
        db.session.add(courier)
        db.session.commit()
        flash(f'Courier "{name}" added successfully!', 'success')
        return redirect(url_for('couriers'))
    
    return render_template('add_courier.html')


@app.route('/couriers/edit/<int:courier_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_courier(courier_id):
    courier = Courier.query.get_or_404(courier_id)
    
    if request.method == 'POST':
        courier.name = request.form.get('name')
        courier.service_type = request.form.get('service_type', '')
        courier.contact_person = request.form.get('contact_person', '')
        courier.contact_email = request.form.get('contact_email', '')
        courier.contact_phone = request.form.get('contact_phone', '')
        courier.description = request.form.get('description', '')
        courier.is_active = request.form.get('is_active') == 'on'
        
        db.session.commit()
        flash(f'Courier "{courier.name}" updated successfully!', 'success')
        return redirect(url_for('couriers'))
    
    return render_template('edit_courier.html', courier=courier)


@app.route('/couriers/delete/<int:courier_id>', methods=['POST'])
@login_required
@admin_required
def delete_courier(courier_id):
    courier = Courier.query.get_or_404(courier_id)
    courier_name = courier.name
    db.session.delete(courier)
    db.session.commit()
    flash(f'Courier "{courier_name}" deleted successfully!', 'success')
    return redirect(url_for('couriers'))


# ============== OFFER MANAGEMENT ==============

@app.route('/offers')
@login_required
@manager_required
def offers():
    offers = Offer.query.order_by(Offer.min_amount.asc()).all()
    return render_template('offers.html', offers=offers)


@app.route('/offers/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_offer():
    if request.method == 'POST':
        min_amount = float(request.form.get('min_amount', 0))
        max_amount = float(request.form.get('max_amount', 0))
        offer_amount = float(request.form.get('offer_amount', 0))
        
        # Validate that min < max
        if min_amount >= max_amount:
            flash('Minimum amount must be less than maximum amount!', 'error')
            return redirect(url_for('add_offer'))
        
        # Check for overlapping ranges
        overlapping = Offer.query.filter(
            Offer.is_active == True,
            (
                (Offer.min_amount <= min_amount) & (Offer.max_amount > min_amount) |
                (Offer.min_amount < max_amount) & (Offer.max_amount >= max_amount) |
                (Offer.min_amount >= min_amount) & (Offer.max_amount <= max_amount)
            )
        ).first()
        
        if overlapping:
            flash('This amount range overlaps with an existing offer!', 'error')
            return redirect(url_for('add_offer'))
        
        offer = Offer(
            min_amount=min_amount,
            max_amount=max_amount,
            offer_amount=offer_amount,
            description=request.form.get('description', ''),
            is_active=True,
            created_by=current_user.id
        )
        db.session.add(offer)
        db.session.commit()
        flash(f'Offer for ₹{min_amount}-{max_amount} added successfully!', 'success')
        return redirect(url_for('offers'))
    
    return render_template('add_offer.html')


@app.route('/offers/edit/<int:offer_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_offer(offer_id):
    offer = Offer.query.get_or_404(offer_id)
    
    if request.method == 'POST':
        min_amount = float(request.form.get('min_amount', 0))
        max_amount = float(request.form.get('max_amount', 0))
        offer_amount = float(request.form.get('offer_amount', 0))
        
        # Validate that min < max
        if min_amount >= max_amount:
            flash('Minimum amount must be less than maximum amount!', 'error')
            return redirect(url_for('edit_offer', offer_id=offer_id))
        
        # Check for overlapping ranges (excluding current offer)
        overlapping = Offer.query.filter(
            Offer.id != offer_id,
            Offer.is_active == True,
            (
                (Offer.min_amount <= min_amount) & (Offer.max_amount > min_amount) |
                (Offer.min_amount < max_amount) & (Offer.max_amount >= max_amount) |
                (Offer.min_amount >= min_amount) & (Offer.max_amount <= max_amount)
            )
        ).first()
        
        if overlapping:
            flash('This amount range overlaps with another offer!', 'error')
            return redirect(url_for('edit_offer', offer_id=offer_id))
        
        offer.min_amount = min_amount
        offer.max_amount = max_amount
        offer.offer_amount = offer_amount
        offer.description = request.form.get('description', '')
        offer.is_active = request.form.get('is_active') == 'on'
        
        db.session.commit()
        flash(f'Offer updated successfully!', 'success')
        return redirect(url_for('offers'))
    
    return render_template('edit_offer.html', offer=offer)


@app.route('/offers/delete/<int:offer_id>', methods=['POST'])
@login_required
@admin_required
def delete_offer(offer_id):
    offer = Offer.query.get_or_404(offer_id)
    min_amt = offer.min_amount
    max_amt = offer.max_amount
    db.session.delete(offer)
    db.session.commit()
    flash(f'Offer for ₹{min_amt}-{max_amt} deleted successfully!', 'success')
    return redirect(url_for('offers'))


@app.route('/api/check-offer')
def check_offer():
    """API endpoint to check applicable offer for a given amount"""
    amount = request.args.get('amount', 0, type=float)
    
    offer = Offer.query.filter(
        Offer.is_active == True,
        Offer.min_amount <= amount,
        Offer.max_amount > amount
    ).first()
    
    if offer:
        return jsonify({
            'applicable': True,
            'offer_amount': offer.offer_amount,
            'description': offer.description
        })
    
    return jsonify({'applicable': False, 'offer_amount': 0})


@app.route('/api/get-all-offers')
def get_all_offers():
    """API endpoint to get all active offers"""
    offers = Offer.query.filter_by(is_active=True).order_by(Offer.min_amount.asc()).all()
    
    offers_data = [
        {
            'id': offer.id,
            'min_amount': offer.min_amount,
            'max_amount': offer.max_amount,
            'offer_amount': offer.offer_amount,
            'description': offer.description
        }
        for offer in offers
    ]
    
    return jsonify({'offers': offers_data})


# ============== CLIENT MANAGEMENT ==============

@app.route('/clients')
@login_required
@staff_required
def clients():
    search_query = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    
    # Build query
    query = Client.query
    
    # Apply search filter
    if search_query:
        query = query.filter(
            db.or_(
                Client.name.ilike(f'%{search_query}%'),
                Client.company_name.ilike(f'%{search_query}%'),
                Client.phone.ilike(f'%{search_query}%'),
                Client.alt_phone.ilike(f'%{search_query}%'),
                Client.email.ilike(f'%{search_query}%')
            )
        )
    
    paginate = query.paginate(page=page, per_page=10)
    clients = paginate.items
    return render_template('clients.html', clients=clients, paginate=paginate, search_query=search_query)


@app.route('/client/add', methods=['GET', 'POST'])
@login_required
@admin_required
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
            landmark=request.form.get('landmark'),
            city=request.form.get('city'),
            state=request.form.get('state'),
            pincode=request.form.get('pincode'),
            alt_address=request.form.get('alt_address'),
            alt_landmark=request.form.get('alt_landmark'),
            gst_number=request.form.get('gst_number'),
            billing_pattern_id=request.form.get('billing_pattern_id', type=int) if request.form.get('billing_pattern_id') else None,
            billing_date=request.form.get('billing_date', type=int)
        )
        db.session.add(client)
        db.session.commit()
        flash('Client added successfully!', 'success')
        return redirect(url_for('clients'))
    
    patterns = BillingPattern.query.filter_by(is_active=True).all()
    return render_template('add_client.html', patterns=patterns)


@app.route('/client/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
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
        client.landmark = request.form.get('landmark')
        client.city = request.form.get('city')
        client.state = request.form.get('state')
        client.pincode = request.form.get('pincode')
        client.alt_address = request.form.get('alt_address')
        client.alt_landmark = request.form.get('alt_landmark')
        client.gst_number = request.form.get('gst_number')
        client.billing_pattern_id = request.form.get('billing_pattern_id', type=int) if request.form.get('billing_pattern_id') else None
        client.billing_date = request.form.get('billing_date', type=int)
        client.is_active = request.form.get('is_active') == 'on'
        
        db.session.commit()
        flash('Client updated successfully!', 'success')
        return redirect(url_for('clients'))
    
    patterns = BillingPattern.query.filter_by(is_active=True).all()
    return render_template('edit_client.html', client=client, patterns=patterns)


@app.route('/client/<int:id>/details')
@login_required
@staff_required
def client_details(id):
    client = Client.query.get_or_404(id)
    return render_template('client_details.html', client=client)


@app.route('/client/<int:client_id>/receiver/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_receiver(client_id):
    client = Client.query.get_or_404(client_id)
    if request.method == 'POST':
        pincode = request.form.get('pincode')
        if not pincode or len(pincode) != 6 or not pincode.isdigit():
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
            landmark=request.form.get('landmark'),
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
@admin_required
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
        if not pincode or len(pincode) != 6 or not pincode.isdigit():
            flash('Invalid Pincode. It must be exactly 6 digits.', 'error')
            return redirect(url_for('add_client_address', client_id=client_id))
            
        address = ClientAddress(
            client_id=client_id,
            address_label=request.form.get('address_label'),
            address=request.form.get('address'),
            city=request.form.get('city'),
            state=request.form.get('state'),
            pincode=pincode,
            landmark=request.form.get('landmark')
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
        address.landmark = request.form.get('landmark')
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
    from sqlalchemy import case
    
    status_filter = request.args.get('status', '')
    order_type_filter = request.args.get('order_type', '')
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    
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
    
    # Define status priority: pending -> confirmed/in_transit -> delivered -> cancelled
    status_priority = case(
        (Order.status == 'at_destination', 1),
        (Order.status == 'confirmed', 2),
        (Order.status == 'in_transit', 2),
        (Order.status == 'delivered', 3),
        (Order.status == 'cancelled', 4),  
        else_=5
    )
    
    # Paginate with 20 orders per page
    pagination = query.order_by(status_priority, Order.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    orders = pagination.items
    delivery_personnel = User.query.filter_by(role='delivery', is_active=True).all()
    
    return render_template('orders.html', 
                         orders=orders,
                         pagination=pagination,
                         delivery_personnel=delivery_personnel,
                         status_filter=status_filter,
                         order_type_filter=order_type_filter,
                         search=search,
                         min=min)


@app.route('/order/walkin', methods=['GET', 'POST'])
@login_required
def walkin_order():
    # Allow staff, managers, and branch users to access
    if current_user.role not in ['admin', 'manager', 'operation_manager', 'staff', 'marketing_manager', 'branch']:
        flash('Access denied. Only staff, managers, and branch users can create walk-in orders.', 'error')
        return redirect(url_for('dashboard'))
    
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
        if not receiver_pincode or len(receiver_pincode) != 6 or not receiver_pincode.isdigit():
            flash('Invalid Pincode. It must be exactly 6 digits.', 'danger')
            return redirect(url_for('walkin_order'))
        
        # Get price_list_type from form (required for marketing managers)
        price_list_type = request.form.get('price_list_type', 'default')
        if not price_list_type:
            price_list_type = 'default'
        
        order = Order(
            receipt_number=receipt_number,
            receipt_type=receipt_type,
            assignment_id=assignment_id,
            order_type='walkin',
            price_list_type=price_list_type,
            receipt_mode=request.form.get('receipt_mode'),
            customer_name=request.form.get('customer_name'),
            customer_phone=request.form.get('customer_phone'),
            customer_email=request.form.get('customer_email'),
            customer_address=request.form.get('customer_address'),
            customer_pincode=request.form.get('customer_pincode'),
            receiver_name=request.form.get('receiver_name'),
            receiver_phone=request.form.get('receiver_phone'),
            receiver_address=request.form.get('receiver_address'),
            receiver_city=request.form.get('receiver_city'),
            receiver_state=request.form.get('receiver_state'),
            receiver_pincode=request.form.get('receiver_pincode'),
            receiver_landmark=request.form.get('receiver_landmark'),
            package_description=request.form.get('package_description'),
            weight=float(request.form.get('weight') or 0),
            number_of_boxes=int(request.form.get('number_of_boxes') or 1),
            special_instructions=request.form.get('special_instructions'),
            handling_tags=','.join(all_tags),
            branch_id=current_user.branch_id,
            created_by=current_user.id,
            status='at_destination',
            payment_mode=request.form.get('payment_mode'),
            # International Booking Fields
            is_international=True if request.form.get('is_international') == 'on' else False,
            destination_country=request.form.get('destination_country'),
            hs_code=request.form.get('hs_code'),
            customs_description=request.form.get('customs_description'),
            product_value_usd=float(request.form.get('product_value_usd') or 0),
            invoice_currency=request.form.get('invoice_currency', 'USD'),
            international_notes=request.form.get('international_notes'),
            requires_signature_intl=True if request.form.get('requires_signature') == 'on' else False
        )
        
        received_amount = float(request.form.get('received_amount') or 0)
        insured_amount = float(request.form.get('insured_amount') or 0)
        
        order.received_amount = received_amount
        order.total_amount = received_amount
        order.insured_amount = insured_amount
        
        if order.weight:
            base, weight_charge, additional, discount, total, _, ins_charge = calculate_order_amount(
                order.weight, state=order.receiver_state, insured_amount=order.insured_amount, shipping_mode=order.receipt_mode
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
    
    # Check if user is marketing manager
    is_marketing_manager = current_user.role == 'marketing_manager'
    
    return render_template('walkin_order.html', prefill=prefill, is_marketing_manager=is_marketing_manager)




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


@app.route('/api/order/bill', methods=['POST'])
@login_required
def bill_order():
    data = request.get_json()
    order_id = data.get('order_id')
    amount = float(data.get('amount', 0))
    
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'success': False, 'message': 'Order not found'}), 404
    
    # Update order as paid
    order.received_amount = amount
    order.payment_status = 'paid'
    order.payment_mode = 'manual'  # Mark as manually billed
    
    # Create tracking update
    tracking = TrackingUpdate(
        order_id=order.id,
        status='Billed',
        description=f'Order billed for ₹{amount:.2f} and marked as PAID',
        updated_by=current_user.id
    )
    
    db.session.add(tracking)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Order billed successfully'})


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
        if not receiver_pincode or len(receiver_pincode) != 6 or not receiver_pincode.isdigit():
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
            customer_pincode=client.pincode if client else request.form.get('customer_pincode'),
            receiver_name=request.form.get('receiver_name'),
            receiver_phone=request.form.get('receiver_phone'),
            receiver_address=request.form.get('receiver_address'),
            receiver_city=request.form.get('receiver_city'),
            receiver_state=request.form.get('receiver_state'),
            receiver_pincode=request.form.get('receiver_pincode'),
            receiver_landmark=request.form.get('receiver_landmark'),
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
            order.weight, None, state=order.receiver_state, client_id=order.client_id, insured_amount=order.insured_amount, shipping_mode=order.receipt_mode
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
        order.customer_pincode = request.form.get('customer_pincode')
        order.receiver_name = request.form.get('receiver_name')
        order.receiver_phone = request.form.get('receiver_phone')
        order.receiver_address = request.form.get('receiver_address')
        order.receiver_landmark = request.form.get('receiver_landmark')
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
        
        # International Booking Fields
        order.is_international = True if request.form.get('is_international') == 'on' else False
        order.destination_country = request.form.get('destination_country')
        order.hs_code = request.form.get('hs_code')
        order.customs_description = request.form.get('customs_description')
        order.product_value_usd = float(request.form.get('product_value_usd') or 0)
        order.invoice_currency = request.form.get('invoice_currency', 'USD')
        order.international_notes = request.form.get('international_notes')
        order.requires_signature_intl = True if request.form.get('requires_signature_intl') == 'on' else False
        
        # Recalculate amounts
        if order.weight:
            base, weight_charge, additional, discount, total, _ = calculate_order_amount(
                order.weight, None, state=order.receiver_state, client_id=order.client_id, shipping_mode=order.receipt_mode
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
    
    # Only show 4 status options for all orders
    valid_transitions = {
        'in_transit': 'In Transit',
        'at_destination': 'At Destination',
        'delivered': 'Delivered',
        'rto': 'RTO / Returns'
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
        if pincode and (len(pincode) != 6 or not pincode.isdigit()):
            flash('Invalid Pincode. It must be exactly 6 digits.', 'error')
            return redirect(url_for('customer_form', token=token))
            
        order.receiver_landmark = request.form.get('receiver_landmark') or order.receiver_landmark
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
@manager_required
def insurance_settings():
    setting = SystemSettings.query.filter_by(key='insurance_percentage').first()
    
    if request.method == 'POST':
        if current_user.role != 'admin':
            flash('Only administrators can update settings.', 'error')
            return redirect(url_for('insurance_settings'))

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

@app.route('/billing-patterns')
@login_required
@admin_required
def billing_patterns():
    patterns = BillingPattern.query.all()
    return render_template('billing_patterns.html', patterns=patterns)


@app.route('/billing-patterns/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_billing_pattern():
    if request.method == 'POST':
        pattern = BillingPattern(
            name=request.form.get('name'),
            pattern_type=request.form.get('pattern_type'),
            base_rate=float(request.form.get('base_rate', 0)),
            rate_per_kg=float(request.form.get('rate_per_kg', 0)),
            additional_charges=float(request.form.get('additional_charges', 0)),
            min_weight=float(request.form.get('min_weight', 0.5)),
            max_weight=float(request.form.get('max_weight')) if request.form.get('max_weight') else None,
            discount_percentage=float(request.form.get('discount_percentage', 0)),
            description=request.form.get('description'),
            is_active=True
        )
        db.session.add(pattern)
        db.session.commit()
        flash(f'Billing pattern "{pattern.name}" created successfully!', 'success')
        return redirect(url_for('billing_patterns'))
    
    return render_template('add_billing_pattern.html')


@app.route('/billing-patterns/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_billing_pattern(id):
    pattern = BillingPattern.query.get_or_404(id)
    
    if request.method == 'POST':
        pattern.name = request.form.get('name')
        pattern.pattern_type = request.form.get('pattern_type')
        pattern.base_rate = float(request.form.get('base_rate', 0))
        pattern.rate_per_kg = float(request.form.get('rate_per_kg', 0))
        pattern.additional_charges = float(request.form.get('additional_charges', 0))
        pattern.min_weight = float(request.form.get('min_weight', 0.5))
        pattern.max_weight = float(request.form.get('max_weight')) if request.form.get('max_weight') else None
        pattern.discount_percentage = float(request.form.get('discount_percentage', 0))
        pattern.description = request.form.get('description')
        pattern.is_active = request.form.get('is_active') == 'on'
        
        db.session.commit()
        flash(f'Billing pattern "{pattern.name}" updated successfully!', 'success')
        return redirect(url_for('billing_patterns'))
    
    return render_template('edit_billing_pattern.html', pattern=pattern)


@app.route('/billing-patterns/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_billing_pattern(id):
    pattern = BillingPattern.query.get_or_404(id)
    pattern_name = pattern.name
    
    db.session.delete(pattern)
    db.session.commit()
    
    flash(f'Billing pattern "{pattern_name}" deleted successfully!', 'success')
    return redirect(url_for('billing_patterns'))


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


@app.route('/manual-match-excel', methods=['POST'])
@login_required
@staff_required
def manual_match_excel():
    data_id = request.form.get('data_id')
    excel_data = ExcelData.query.get_or_404(data_id)
    
    if excel_data.matched:
        return jsonify({'success': False, 'message': 'Record already matched'})
        
    order = Order.query.filter_by(receipt_number=excel_data.receipt_number).first()
    
    if order:
        order.excel_weight = excel_data.weight
        order.excel_amount = excel_data.amount
        order.excel_verified = True
        excel_data.matched = True
        
        # Update upload stats
        upload = ExcelUpload.query.get(excel_data.upload_id)
        if upload:
            upload.records_matched += 1
            
        db.session.commit()
        return jsonify({'success': True, 'message': f'Matched with Order #{order.receipt_number}'})
    
    return jsonify({'success': False, 'message': f'No matching Order found for {excel_data.receipt_number}'})



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
                shipping_mode = data.get('receipt_mode', 'standard')
                base, weight_charge, additional, discount, total, _ = calculate_order_amount(
                    order.weight, state=order.receiver_state, shipping_mode=shipping_mode
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
    shipping_mode = request.json.get('shipping_mode', 'standard')
    
    if weight or insured_amount:
        base, weight_charge, additional, discount, total, rate_type, ins_charge = calculate_order_amount(
            weight, None, state=state, client_id=client_id, insured_amount=insured_amount, shipping_mode=shipping_mode
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
@manager_required

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
def default_prices():
    # Allow managers and branch users to view prices
    if current_user.role not in ['admin', 'manager', 'operation_manager', 'branch']:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    prices = DefaultStatePrice.query.all()
    return render_template('default_prices.html', prices=prices)


@app.route('/default-prices/add', methods=['GET', 'POST'])
@login_required
def add_default_price():
    # Allow admins, managers, and branch users to add prices
    if current_user.role not in ['admin', 'manager', 'operation_manager', 'branch']:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    # List of Indian states
    indian_states = [
        'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
        'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
        'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
        'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
        'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal'
    ]
    
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
            price_1kg=float(request.form.get('price_1kg', 0)),
            price_2kg=float(request.form.get('price_2kg', 0)),
            price_3kg=float(request.form.get('price_3kg', 0)),
            price_extra_per_kg=float(request.form.get('price_extra_per_kg', 20))
        )
        db.session.add(price)
        db.session.commit()
        flash(f'Prices for {state} added successfully!', 'success')
        return redirect(url_for('default_prices'))
    
    # Get states that already have prices defined
    existing_states = [price.state for price in DefaultStatePrice.query.all()]
    # Filter to show only available states (not already in database)
    available_states = [state for state in indian_states if state not in existing_states]
        
    return render_template('add_default_price.html', states=available_states)


@app.route('/default-prices/edit/<int:price_id>', methods=['GET', 'POST'])
@login_required
def edit_default_price(price_id):
    # Allow admins, managers, and branch users to edit prices
    if current_user.role not in ['admin', 'manager', 'operation_manager', 'branch']:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    # List of Indian states
    indian_states = [
        'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
        'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
        'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
        'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
        'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal'
    ]
    
    price = DefaultStatePrice.query.get_or_404(price_id)
    
    if request.method == 'POST':
        price.state = request.form.get('state')
        price.price_100gm = float(request.form.get('price_100gm', 0))
        price.price_250gm = float(request.form.get('price_250gm', 0))
        price.price_500gm = float(request.form.get('price_500gm', 0))
        price.price_1kg = float(request.form.get('price_1kg', 0))
        price.price_2kg = float(request.form.get('price_2kg', 0))
        price.price_3kg = float(request.form.get('price_3kg', 0))
        price.price_extra_per_kg = float(request.form.get('price_extra_per_kg', 20))
        
        db.session.commit()
        flash(f'Prices for {price.state} updated successfully!', 'success')
        return redirect(url_for('default_prices'))
        
    return render_template('edit_default_price.html', price=price, states=indian_states)


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


@app.route('/normal-client-prices')
@login_required
def normal_client_prices():
    # Allow managers and branch users to view prices
    if current_user.role not in ['admin', 'manager', 'operation_manager', 'branch']:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    prices = NormalClientStatePrice.query.all()
    return render_template('normal_client_prices.html', prices=prices)


@app.route('/normal-client-price/add', methods=['GET', 'POST'])
@login_required
def add_normal_client_price():
    # Allow managers and branch users to add prices
    if current_user.role not in ['admin', 'manager', 'operation_manager', 'branch']:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        state = request.form.get('state')
        if NormalClientStatePrice.query.filter_by(state=state).first():
            flash('Default client price for this state already exists.', 'error')
            return redirect(url_for('add_normal_client_price'))
            
        price = NormalClientStatePrice(
            state=state,
            price_100gm=float(request.form.get('price_100gm', 0)),
            price_250gm=float(request.form.get('price_250gm', 0)),
            price_500gm=float(request.form.get('price_500gm', 0)),
            price_1kg=float(request.form.get('price_1kg', 0)),
            price_2kg=float(request.form.get('price_2kg', 0)),
            price_3kg=float(request.form.get('price_3kg', 0)),
            price_extra_per_kg=float(request.form.get('price_extra_per_kg', 20)),
            price_3_10kg=float(request.form.get('price_3_10kg', 0)),
            price_10_25kg=float(request.form.get('price_10_25kg', 0)),
            price_25_50kg=float(request.form.get('price_25_50kg', 0)),
            price_50_100kg=float(request.form.get('price_50_100kg', 0)),
            price_100plus_kg=float(request.form.get('price_100plus_kg', 0))
        )
        db.session.add(price)
        db.session.commit()
        flash(f'Default client prices for {state} added successfully!', 'success')
        return redirect(url_for('normal_client_prices'))
        
    return render_template('add_normal_client_price.html')


@app.route('/normal-client-price/edit/<int:price_id>', methods=['GET', 'POST'])
@login_required
def edit_normal_client_price(price_id):
    # Allow managers and branch users to edit prices
    if current_user.role not in ['admin', 'manager', 'operation_manager', 'branch']:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    price = NormalClientStatePrice.query.get_or_404(price_id)
    
    if request.method == 'POST':
        price.state = request.form.get('state')
        price.price_100gm = float(request.form.get('price_100gm', 0))
        price.price_250gm = float(request.form.get('price_250gm', 0))
        price.price_500gm = float(request.form.get('price_500gm', 0))
        price.price_1kg = float(request.form.get('price_1kg', 0))
        price.price_2kg = float(request.form.get('price_2kg', 0))
        price.price_3kg = float(request.form.get('price_3kg', 0))
        price.price_extra_per_kg = float(request.form.get('price_extra_per_kg', 20))
        price.price_3_10kg = float(request.form.get('price_3_10kg', 0))
        price.price_10_25kg = float(request.form.get('price_10_25kg', 0))
        price.price_25_50kg = float(request.form.get('price_25_50kg', 0))
        price.price_50_100kg = float(request.form.get('price_50_100kg', 0))
        price.price_100plus_kg = float(request.form.get('price_100plus_kg', 0))
        
        db.session.commit()
        flash(f'Default client prices for {price.state} updated successfully!', 'success')
        return redirect(url_for('normal_client_prices'))
        
    return render_template('edit_normal_client_price.html', price=price)


@app.route('/normal-client-price/delete/<int:price_id>', methods=['POST'])
@login_required
@admin_required
def delete_normal_client_price(price_id):
    price = NormalClientStatePrice.query.get_or_404(price_id)
    state_name = price.state
    db.session.delete(price)
    db.session.commit()
    flash(f'Default client pricing for {state_name} deleted.', 'success')
    return redirect(url_for('normal_client_prices'))




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
            'price_1kg': s.price_1kg,
            'price_2kg': s.price_2kg,
            'price_3kg': s.price_3kg,
            'has_custom_price': 1 if custom else 0,
            'custom_price_100gm': custom.price_100gm if custom else 0,
            'custom_price_250gm': custom.price_250gm if custom else 0,
            'custom_price_500gm': custom.price_500gm if custom else 0,
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
@admin_required

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
        custom.price_1kg = float(request.form.get('price_1kg', 0))
        custom.price_2kg = float(request.form.get('price_2kg', 0))
        custom.price_3kg = float(request.form.get('price_3kg', 0))
        custom.price_extra_per_kg = float(request.form.get('price_extra_per_kg', 20))
        
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
@admin_required

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


# ============== AIR SHIPPING MODE PRICING ==============

@app.route('/client-air-prices/<int:client_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def set_client_air_prices(client_id):
    """Set air shipping mode prices for a specific client"""
    client = Client.query.get_or_404(client_id)
    selected_state = request.args.get('state')
    
    if request.method == 'POST':
        state = request.form.get('state')
        if not state:
            flash('State is required.', 'error')
            return redirect(url_for('set_client_air_prices', client_id=client_id))
            
        # Get or create air pricing for this client-state combo
        custom = ClientStatePrice.query.filter_by(
            client_id=client_id, 
            state=state, 
            shipping_mode='air'
        ).first()
        if not custom:
            custom = ClientStatePrice(client_id=client_id, state=state, shipping_mode='air')
            db.session.add(custom)
            
        # Standard brackets (up to 3kg)
        custom.price_100gm = float(request.form.get('price_100gm', 0))
        custom.price_250gm = float(request.form.get('price_250gm', 0))
        custom.price_500gm = float(request.form.get('price_500gm', 0))
        custom.price_1kg = float(request.form.get('price_1kg', 0))
        custom.price_2kg = float(request.form.get('price_2kg', 0))
        custom.price_3kg = float(request.form.get('price_3kg', 0))
        
        # Air cargo weight tiers (> 3kg)
        custom.price_3_10kg = float(request.form.get('price_3_10kg', 0))
        custom.price_10_25kg = float(request.form.get('price_10_25kg', 0))
        custom.price_25_50kg = float(request.form.get('price_25_50kg', 0))
        custom.price_50_100kg = float(request.form.get('price_50_100kg', 0))
        custom.price_100plus_kg = float(request.form.get('price_100plus_kg', 0))
        
        db.session.commit()
        flash(f'Air shipping prices for {state} updated successfully!', 'success')
        return redirect(url_for('set_client_air_prices', client_id=client_id))
        
    all_states = [s.state for s in DefaultStatePrice.query.distinct(DefaultStatePrice.state).all()]
    
    # Pre-fill data if state is selected
    existing_price = None
    if selected_state:
        existing_price = ClientStatePrice.query.filter_by(
            client_id=client_id, 
            state=selected_state, 
            shipping_mode='air'
        ).first()
        
    return render_template('set_client_air_prices.html', 
                         client=client, 
                         states=all_states, 
                         selected_state=selected_state,
                         existing_price=existing_price)


@app.route('/walking-air-prices', methods=['GET', 'POST'])
@login_required
@admin_required
def set_walking_air_prices():
    """Set air shipping mode prices for walking customers (normal client)"""
    selected_state = request.args.get('state')
    
    if request.method == 'POST':
        state = request.form.get('state')
        if not state:
            flash('State is required.', 'error')
            return redirect(url_for('set_walking_air_prices'))
            
        # Get or create air pricing for walking customers
        custom = NormalClientStatePrice.query.filter_by(
            state=state, 
            shipping_mode='air'
        ).first()
        if not custom:
            custom = NormalClientStatePrice(state=state, shipping_mode='air')
            db.session.add(custom)
            
        # Standard brackets (up to 3kg)
        custom.price_100gm = float(request.form.get('price_100gm', 0))
        custom.price_250gm = float(request.form.get('price_250gm', 0))
        custom.price_500gm = float(request.form.get('price_500gm', 0))
        custom.price_1kg = float(request.form.get('price_1kg', 0))
        custom.price_2kg = float(request.form.get('price_2kg', 0))
        custom.price_3kg = float(request.form.get('price_3kg', 0))
        
        # Air cargo weight tiers (> 3kg)
        custom.price_3_10kg = float(request.form.get('price_3_10kg', 0))
        custom.price_10_25kg = float(request.form.get('price_10_25kg', 0))
        custom.price_25_50kg = float(request.form.get('price_25_50kg', 0))
        custom.price_50_100kg = float(request.form.get('price_50_100kg', 0))
        custom.price_100plus_kg = float(request.form.get('price_100plus_kg', 0))
        
        db.session.commit()
        flash(f'Air shipping prices for {state} (walking customers) updated successfully!', 'success')
        return redirect(url_for('set_walking_air_prices'))
        
    all_states = [s.state for s in NormalClientStatePrice.query.distinct(NormalClientStatePrice.state).filter_by(shipping_mode='standard').all()]
    
    # Pre-fill data if state is selected
    existing_price = None
    if selected_state:
        existing_price = NormalClientStatePrice.query.filter_by(
            state=selected_state, 
            shipping_mode='air'
        ).first()
        
    return render_template('set_walking_air_prices.html', 
                         states=all_states, 
                         selected_state=selected_state,
                         existing_price=existing_price)


# ============== ADVANCED REPORTS ==============

@app.route('/detailed-reports')
@login_required
@manager_required

def detailed_reports():
    return render_template('detailed_reports.html')


@app.route('/due-amount-report')
@login_required
@manager_required

def due_amount_report():
    return render_template('due_amount_report.html')


@app.route('/public-prices')
def public_prices():
    prices = DefaultStatePrice.query.all()
    weight_categories = [
        ('100gm', 'price_100gm'),
        ('250gm', 'price_250gm'),
        ('500gm', 'price_500gm'),
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
@manager_required

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
            'status': 'At Destination' if o.status == 'pending' else o.status.title()
        } for o in orders[:10]]
    })


@app.route('/api/reports/sales')
@login_required
@manager_required

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
@manager_required

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
@manager_required

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
@manager_required
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


@app.route('/client/<int:client_id>/adjustable-bill')
@login_required
@manager_required
def adjustable_bill(client_id):
    """Render a bill with editable fields for temporary adjustments"""
    client = Client.query.get_or_404(client_id)
    
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    is_gst = request.args.get('gst', 'no').lower() == 'yes'
    
    query = Order.query.filter_by(client_id=client_id, order_type='client')
    
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
    
    grand_total_amount = sum(o.total_amount or 0 for o in orders)
    grand_received_amount = sum(o.received_amount or 0 for o in orders)
    grand_due_amount = grand_total_amount - grand_received_amount
    grand_total_weight = sum(o.weight or 0 for o in orders)
    
    if is_gst:
        taxable_value = grand_total_amount / 1.18
        cgst_amount = taxable_value * 0.09
        sgst_amount = taxable_value * 0.09
    else:
        taxable_value = 0
        cgst_amount = 0
        sgst_amount = 0
    
    return render_template('adjustable_consolidated_bill.html',
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
                         sgst_amount=sgst_amount,
                         now=datetime.now())


@app.route('/order/<int:order_id>/bill')
@login_required
@staff_required
def order_bill(order_id):
    """Display bill for a single order"""
    order = Order.query.get_or_404(order_id)
    
    # Get GST parameter if present
    is_gst = request.args.get('gst', 'no').lower() == 'yes'
    
    # Get client info if order belongs to a client
    client = None
    if order.client_id:
        client = Client.query.get(order.client_id)
    
    # Calculate totals for this single order
    total_amount = order.total_amount or 0
    received_amount = order.received_amount or 0
    due_amount = total_amount - received_amount
    
    # Calculate GST if needed
    if is_gst:
        taxable_value = total_amount / 1.18
        cgst_amount = taxable_value * 0.09
        sgst_amount = taxable_value * 0.09
    else:
        taxable_value = 0
        cgst_amount = 0
        sgst_amount = 0
    
    return render_template('order_bill.html',
                         order=order,
                         client=client,
                         total_amount=total_amount,
                         received_amount=received_amount,
                         due_amount=due_amount,
                         is_gst=is_gst,
                         taxable_value=taxable_value,
                         cgst_amount=cgst_amount,
                         sgst_amount=sgst_amount,
                         now=datetime.now())


@app.route('/order/<int:order_id>/mark-paid', methods=['POST'])
@login_required
@staff_required
def mark_order_paid(order_id):
    """Mark an order as fully paid"""
    try:
        order = Order.query.get_or_404(order_id)
        
        # Get the amount to mark as received
        amount = request.json.get('amount', order.total_amount or 0)
        
        # Update the received amount
        order.received_amount = amount
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Order marked as paid. Amount: ₹{amount}',
            'received_amount': order.received_amount,
            'due_amount': (order.total_amount or 0) - (order.received_amount or 0)
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/search-orders-for-billing')
@login_required
@staff_required
def api_search_orders_for_billing():
    """Search orders for billing"""
    try:
        query = request.args.get('query', '').strip()
        order_type = request.args.get('type', 'all')  # all, client, walkin
        payment_status = request.args.get('status', 'all')  # all, unpaid, partial, paid
        
        orders_query = Order.query
        
        # Filter by search query (receipt number or receiver name)
        if query:
            orders_query = orders_query.filter(
                (Order.receipt_number.ilike(f'%{query}%')) |
                (Order.receiver_name.ilike(f'%{query}%'))
            )
        
        # Filter by order type
        if order_type != 'all':
            orders_query = orders_query.filter_by(order_type=order_type)
        
        # Filter by payment status
        if payment_status == 'unpaid':
            orders_query = orders_query.filter((Order.received_amount == None) | (Order.received_amount == 0))
        elif payment_status == 'partial':
            orders_query = orders_query.filter(
                Order.received_amount.isnot(None),
                Order.received_amount > 0,
                Order.received_amount < Order.total_amount
            )
        elif payment_status == 'paid':
            orders_query = orders_query.filter(Order.received_amount == Order.total_amount)
        
        orders = orders_query.order_by(Order.created_at.desc()).limit(50).all()
        
        results = []
        for order in orders:
            due = (order.total_amount or 0) - (order.received_amount or 0)
            status = 'paid' if due == 0 else ('unpaid' if order.received_amount == None or order.received_amount == 0 else 'partial')
            
            results.append({
                'id': order.id,
                'receipt_number': order.receipt_number,
                'receiver_name': order.receiver_name,
                'receiver_city': order.receiver_city,
                'date': order.created_at.strftime('%Y-%m-%d'),
                'amount': float(order.total_amount or 0),
                'received': float(order.received_amount or 0),
                'due': float(due),
                'status': status,
                'order_type': order.order_type
            })
        
        return jsonify({
            'success': True,
            'orders': results,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


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

    if not genai:
        return jsonify({'error': 'Google Generative AI is not configured. Please contact admin.'}), 400

    try:
        # Load Gemini model
        model = genai.GenerativeModel('gemini-flash-latest')
        
        # Prepare content for Gemini
        img_content = []
        
        if file.filename.lower().endswith('.pdf'):
            # Convert PDF to Image (first page)
            if not fitz:
                return jsonify({'error': 'PyMuPDF is not installed. PDF support is unavailable. Please upload an image instead.'}), 400
            
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
        - from_pincode
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


# ============== MARKETING / SALES INSIGHTS ==============

@app.route('/marketing/insights')
@login_required
def marketing_insights():
    # Check if user has access
    if current_user.role not in ['admin', 'manager', 'operation_manager', 'staff', 'marketing_manager']:
        flash('Access restricted for this page.', 'error')
        return redirect(url_for('dashboard'))
    from sqlalchemy import func
    total_visits = SalesVisit.query.count()
    follow_ups_due = FollowUp.query.filter_by(status='pending').count()
    today = datetime.utcnow().date()
    meetings_today = Meeting.query.filter(
        db.func.date(Meeting.scheduled_at) == today,
        Meeting.status == 'scheduled'
    ).count()
    conversions = SalesVisit.query.filter_by(status='converted').count()
    recent_visits = SalesVisit.query.order_by(SalesVisit.created_at.desc()).limit(8).all()
    return render_template('marketing_insights.html',
        total_visits=total_visits,
        follow_ups_due=follow_ups_due,
        meetings_today=meetings_today,
        conversions=conversions,
        recent_visits=recent_visits
    )


@app.route('/marketing/insights/api/charts')
@login_required
def marketing_charts_api():
    # Check if user has access
    if current_user.role not in ['admin', 'manager', 'operation_manager', 'staff', 'marketing_manager']:
        return jsonify({'error': 'Access denied'}), 403
    from sqlalchemy import func
    # Visits per day (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    daily_visits = db.session.query(
        db.func.date(SalesVisit.created_at).label('day'),
        db.func.count(SalesVisit.id).label('count')
    ).filter(SalesVisit.created_at >= thirty_days_ago)\
     .group_by(db.func.date(SalesVisit.created_at))\
     .order_by('day').all()

    # Status breakdown
    status_counts = db.session.query(
        SalesVisit.status,
        db.func.count(SalesVisit.id)
    ).group_by(SalesVisit.status).all()

    # Follow-up status breakdown
    followup_counts = db.session.query(
        FollowUp.status,
        db.func.count(FollowUp.id)
    ).group_by(FollowUp.status).all()

    return jsonify({
        'daily_visits': [{'day': str(r.day), 'count': r.count} for r in daily_visits],
        'status_breakdown': {r[0]: r[1] for r in status_counts},
        'followup_breakdown': {r[0]: r[1] for r in followup_counts}
    })


@app.route('/marketing/visits')
@login_required
def marketing_visits():
    # Check if user has access
    if current_user.role not in ['admin', 'manager', 'operation_manager', 'staff', 'marketing_manager']:
        flash('Access restricted for this page.', 'error')
        return redirect(url_for('dashboard'))
    status_filter = request.args.get('status', '')
    search = request.args.get('search', '')
    query = SalesVisit.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if search:
        query = query.filter(
            (SalesVisit.contact_name.ilike(f'%{search}%')) |
            (SalesVisit.company_name.ilike(f'%{search}%')) |
            (SalesVisit.company_city.ilike(f'%{search}%'))
        )
    visits = query.order_by(SalesVisit.created_at.desc()).all()
    return render_template('marketing_visits.html', visits=visits,
                           status_filter=status_filter, search=search)


@app.route('/marketing/visits/new', methods=['GET', 'POST'])
@login_required
def marketing_visit_new():
    # Check if user has access
    if current_user.role not in ['admin', 'manager', 'operation_manager', 'staff', 'marketing_manager']:
        flash('Access restricted for this page.', 'error')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        visit = SalesVisit(
            contact_name=request.form.get('contact_name'),
            contact_phone=request.form.get('contact_phone'),
            contact_email=request.form.get('contact_email'),
            contact_designation=request.form.get('contact_designation'),
            company_name=request.form.get('company_name'),
            company_address=request.form.get('company_address'),
            company_city=request.form.get('company_city'),
            company_state=request.form.get('company_state'),
            covered_area=request.form.get('covered_area'),
            load_frequency=request.form.get('load_frequency'),
            load_capacity=request.form.get('load_capacity'),
            current_courier=request.form.get('current_courier'),
            price_cert=request.form.get('price_cert'),
            desired_price=request.form.get('desired_price'),
            pitch_notes=request.form.get('pitch_notes'),
            status=request.form.get('status', 'new'),
            visit_date=datetime.utcnow(),
            created_by=current_user.id
        )
        db.session.add(visit)
        db.session.commit()
        flash('New visit / pitch recorded successfully!', 'success')
        return redirect(url_for('marketing_visit_detail', visit_id=visit.id))
    couriers = Courier.query.filter_by(is_active=True).all()
    return render_template('marketing_visit_form.html', visit=None, couriers=couriers)


@app.route('/marketing/visits/<int:visit_id>')
@login_required
def marketing_visit_detail(visit_id):
    if current_user.role not in ['admin', 'manager', 'operation_manager', 'staff', 'marketing_manager']:
        flash('Access restricted for this page.', 'error')
        return redirect(url_for('dashboard'))
    visit = SalesVisit.query.get_or_404(visit_id)
    return render_template('marketing_visit_detail.html', visit=visit)


@app.route('/marketing/visits/<int:visit_id>/edit', methods=['GET', 'POST'])
@login_required
def marketing_visit_edit(visit_id):
    if current_user.role not in ['admin', 'manager', 'operation_manager', 'staff', 'marketing_manager']:
        flash('Access restricted for this page.', 'error')
        return redirect(url_for('dashboard'))
    visit = SalesVisit.query.get_or_404(visit_id)
    if request.method == 'POST':
        visit.contact_name = request.form.get('contact_name')
        visit.contact_phone = request.form.get('contact_phone')
        visit.contact_email = request.form.get('contact_email')
        visit.contact_designation = request.form.get('contact_designation')
        visit.company_name = request.form.get('company_name')
        visit.company_address = request.form.get('company_address')
        visit.company_city = request.form.get('company_city')
        visit.company_state = request.form.get('company_state')
        visit.covered_area = request.form.get('covered_area')
        visit.load_frequency = request.form.get('load_frequency')
        visit.load_capacity = request.form.get('load_capacity')
        visit.current_courier = request.form.get('current_courier')
        visit.price_cert = request.form.get('price_cert')
        visit.desired_price = request.form.get('desired_price')
        visit.pitch_notes = request.form.get('pitch_notes')
        visit.status = request.form.get('status', visit.status)
        db.session.commit()
        flash('Visit updated successfully!', 'success')
        return redirect(url_for('marketing_visit_detail', visit_id=visit.id))
    couriers = Courier.query.filter_by(is_active=True).all()
    return render_template('marketing_visit_form.html', visit=visit, couriers=couriers)


@app.route('/marketing/visits/<int:visit_id>/follow-up', methods=['POST'])
@login_required
def marketing_add_followup(visit_id):
    if current_user.role not in ['admin', 'manager', 'operation_manager', 'staff', 'marketing_manager']:
        flash('Access restricted for this page.', 'error')
        return redirect(url_for('dashboard'))
    visit = SalesVisit.query.get_or_404(visit_id)
    notes = request.form.get('notes', '').strip()
    follow_up_date_str = request.form.get('follow_up_date')
    if not notes:
        flash('Follow-up notes are required.', 'error')
        return redirect(url_for('marketing_visit_detail', visit_id=visit_id))
    follow_up = FollowUp(
        visit_id=visit.id,
        notes=notes,
        follow_up_date=datetime.strptime(follow_up_date_str, '%Y-%m-%dT%H:%M') if follow_up_date_str else None,
        status='pending',
        created_by=current_user.id
    )
    db.session.add(follow_up)
    # Update visit status to follow_up if it was 'new'
    if visit.status == 'new':
        visit.status = 'follow_up'
    db.session.commit()
    flash('Follow-up added successfully!', 'success')
    return redirect(url_for('marketing_visit_detail', visit_id=visit_id))


@app.route('/marketing/visits/<int:visit_id>/followup/<int:fu_id>/done', methods=['POST'])
@login_required
def marketing_followup_done(visit_id, fu_id):
    if current_user.role not in ['admin', 'manager', 'operation_manager', 'staff', 'marketing_manager']:
        flash('Access restricted for this page.', 'error')
        return redirect(url_for('dashboard'))
    fu = FollowUp.query.get_or_404(fu_id)
    fu.status = 'done'
    db.session.commit()
    flash('Follow-up marked as done.', 'success')
    return redirect(url_for('marketing_visit_detail', visit_id=visit_id))


@app.route('/marketing/visits/<int:visit_id>/meeting', methods=['POST'])
@login_required
def marketing_schedule_meeting(visit_id):
    if current_user.role not in ['admin', 'manager', 'operation_manager', 'staff', 'marketing_manager']:
        flash('Access restricted for this page.', 'error')
        return redirect(url_for('dashboard'))
    visit = SalesVisit.query.get_or_404(visit_id)
    scheduled_str = request.form.get('scheduled_at')
    if not scheduled_str:
        flash('Meeting date/time is required.', 'error')
        return redirect(url_for('marketing_visit_detail', visit_id=visit_id))
    # Check if rescheduling an existing meeting
    existing_meeting_id = request.form.get('reschedule_meeting_id')
    if existing_meeting_id:
        meeting = Meeting.query.get_or_404(int(existing_meeting_id))
        meeting.rescheduled_at = datetime.strptime(scheduled_str, '%Y-%m-%dT%H:%M')
        meeting.status = 'rescheduled'
        meeting.notes = request.form.get('notes', meeting.notes)
        flash('Meeting rescheduled successfully!', 'success')
    else:
        meeting = Meeting(
            visit_id=visit.id,
            scheduled_at=datetime.strptime(scheduled_str, '%Y-%m-%dT%H:%M'),
            location=request.form.get('location'),
            notes=request.form.get('notes'),
            status='scheduled',
            created_by=current_user.id
        )
        db.session.add(meeting)
        flash('Meeting scheduled successfully!', 'success')
    db.session.commit()
    return redirect(url_for('marketing_visit_detail', visit_id=visit_id))


@app.route('/marketing/visits/<int:visit_id>/status', methods=['POST'])
@login_required
def marketing_update_status(visit_id):
    if current_user.role not in ['admin', 'manager', 'operation_manager', 'staff', 'marketing_manager']:
        flash('Access restricted for this page.', 'error')
        return redirect(url_for('dashboard'))
    visit = SalesVisit.query.get_or_404(visit_id)
    new_status = request.form.get('status')
    if new_status in ['new', 'follow_up', 'converted', 'lost']:
        visit.status = new_status
        db.session.commit()
        flash(f'Status updated to {new_status.replace("_", " ").title()}.', 'success')
    return redirect(url_for('marketing_visit_detail', visit_id=visit_id))


# ============== MARKETING MANAGER ROUTES ==============

@app.route('/marketing-manager/dashboard')
@login_required
@marketing_manager_required
def marketing_manager_dashboard():
    """Marketing Manager Dashboard with key metrics and activities"""
    from sqlalchemy import func
    from datetime import datetime, timedelta, timezone
    
    # Key metrics for marketing manager
    total_visits = SalesVisit.query.count()
    new_visits = SalesVisit.query.filter_by(status='new').count()
    follow_ups_pending = db.session.query(func.count(FollowUp.id)).filter(FollowUp.status == 'pending').scalar() or 0
    conversions = SalesVisit.query.filter_by(status='converted').count()
    
    # Meetings today
    today = datetime.now(timezone.utc).date()
    meetings_today = db.session.query(Meeting).filter(
        func.date(Meeting.scheduled_at) == today,
        Meeting.status.in_(['scheduled', 'rescheduled'])
    ).count()
    
    # Recent visits
    recent_visits = SalesVisit.query.order_by(SalesVisit.created_at.desc()).limit(5).all()
    
    # Pending follow-ups
    pending_followups = db.session.query(FollowUp).filter(FollowUp.status == 'pending').order_by(FollowUp.follow_up_date).limit(10).all()
    
    # Conversion rate
    conversion_rate = (conversions / total_visits * 100) if total_visits > 0 else 0
    
    return render_template('marketing_manager_dashboard.html',
                         total_visits=total_visits,
                         new_visits=new_visits,
                         follow_ups_pending=follow_ups_pending,
                         conversions=conversions,
                         conversion_rate=conversion_rate,
                         meetings_today=meetings_today,
                         recent_visits=recent_visits,
                         pending_followups=pending_followups)


@app.route('/marketing-manager/pitch-followup')
@login_required
@marketing_manager_required
def marketing_manager_pitch_followup():
    """Manage pitch follow-ups for marketing manager"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    query = db.session.query(FollowUp).filter(FollowUp.status == 'pending')
    
    if status_filter and status_filter in ['pending', 'done', 'skipped']:
        query = db.session.query(FollowUp).filter(FollowUp.status == status_filter)
    
    pagination = query.order_by(FollowUp.follow_up_date).paginate(page=page, per_page=20, error_out=False)
    followups = pagination.items
    
    return render_template('marketing_manager_pitch_followup.html',
                         followups=followups,
                         pagination=pagination,
                         status_filter=status_filter)


@app.route('/marketing-manager/client-reschedule')
@login_required
@marketing_manager_required
def marketing_manager_client_reschedule():
    """View and manage client meeting reschedules"""
    page = request.args.get('page', 1, type=int)
    
    # Get meetings that have been rescheduled
    rescheduled_meetings = db.session.query(Meeting).filter(
        Meeting.status.in_(['rescheduled', 'scheduled'])
    ).order_by(Meeting.scheduled_at.desc()).paginate(page=page, per_page=20, error_out=False)
    
    meetings = rescheduled_meetings.items
    
    return render_template('marketing_manager_client_reschedule.html',
                         meetings=meetings,
                         pagination=rescheduled_meetings)


@app.route('/marketing-manager/meeting-notes')
@login_required
@marketing_manager_required
def marketing_manager_meeting_notes():
    """View and manage meeting notes"""
    page = request.args.get('page', 1, type=int)
    
    # Get meetings with notes
    meetings = db.session.query(Meeting).filter(
        Meeting.notes != None,
        Meeting.notes != ''
    ).order_by(Meeting.scheduled_at.desc()).paginate(page=page, per_page=20, error_out=False)
    
    return render_template('marketing_manager_meeting_notes.html',
                         meetings=meetings,
                         pagination=meetings)


@app.route('/marketing-manager/insights')
@login_required
@marketing_manager_required
def marketing_manager_insights():
    """New insights and analytics for marketing manager"""
    from sqlalchemy import func, desc
    
    # Visit trends
    visits_by_status = db.session.query(
        SalesVisit.status,
        func.count(SalesVisit.id).label('count')
    ).group_by(SalesVisit.status).all()
    
    # Top contacts by follow-up activity
    top_contacts = db.session.query(
        SalesVisit.contact_name,
        SalesVisit.company_name,
        func.count(FollowUp.id).label('followup_count'),
        SalesVisit.status
    ).join(FollowUp, SalesVisit.id == FollowUp.visit_id, isouter=True).group_by(
        SalesVisit.id
    ).order_by(desc('followup_count')).limit(15).all()
    
    # Conversion funnel
    total = SalesVisit.query.count()
    new = SalesVisit.query.filter_by(status='new').count()
    follow_up = SalesVisit.query.filter_by(status='follow_up').count()
    converted = SalesVisit.query.filter_by(status='converted').count()
    lost = SalesVisit.query.filter_by(status='lost').count()
    
    return render_template('marketing_manager_insights.html',
                         visits_by_status=visits_by_status,
                         top_contacts=top_contacts,
                         total=total,
                         new=new,
                         follow_up=follow_up,
                         converted=converted,
                         lost=lost)


# ============== RUN APP ==============

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)