import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here-change-in-production'
    # Use absolute path to instance folder DB to avoid ambiguity
    basedir = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'instance', 'crm_delivery.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'png', 'jpg', 'jpeg', 'pdf'}
    BASE_RECEIPT_NUMBER = '100371900086'
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    
    # ============ EMAIL CONFIGURATION ============
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_FROM_NAME = os.environ.get('MAIL_FROM_NAME', 'CRM Delivery System')
    MAIL_FROM_EMAIL = os.environ.get('MAIL_FROM_EMAIL', 'noreply@crmdelivery.com')
    
    # ============ FEATURE FLAGS ============
    ENABLE_OTP_VERIFICATION = os.environ.get('ENABLE_OTP_VERIFICATION', 'True').lower() == 'true'
    ENABLE_EMAIL_NOTIFICATIONS = os.environ.get('ENABLE_EMAIL_NOTIFICATIONS', 'True').lower() == 'true'
    ENABLE_AUTO_BACKUPS = os.environ.get('ENABLE_AUTO_BACKUPS', 'True').lower() == 'true'
    
    # ============ APPLICATION SETTINGS ============
    TIMEZONE = os.environ.get('TIMEZONE', 'Asia/Kolkata')
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    DEVELOPMENT_MODE = os.environ.get('DEVELOPMENT_MODE', 'False').lower() == 'true'
    CONSOLE_LOG = os.environ.get('CONSOLE_LOG', 'True').lower() == 'true'
    
    # ============ SECURITY ============
    JWT_EXPIRY_DAYS = int(os.environ.get('JWT_EXPIRY_DAYS', 30))
    
    # ============ API SETTINGS ============
    PINCODE_API_ENDPOINT = os.environ.get('PINCODE_API_ENDPOINT', 'https://api.postalpincode.in/pincode/')
    API_RATE_LIMIT = int(os.environ.get('API_RATE_LIMIT', 100))