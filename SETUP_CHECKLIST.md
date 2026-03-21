# CRM Delivery System - Complete Setup Checklist

## 🎯 Phase 1: Environment Preparation

### Step 1: Initial Directory Setup
- [ ] Navigate to project directory: `e:\New folder\crmdeliv`
- [ ] Verify all project files present (app.py, config.py, requirements.txt, etc.)
- [ ] Open command prompt or PowerShell in project directory

### Step 2: Python Installation
- [ ] Check Python installed: `python --version`
  - If not installed, download from https://python.org (Python 3.8+)
  - During installation, **CHECK** "Add Python to PATH"
- [ ] Verify pip works: `pip --version`

### Step 3: Execute Setup Script
- [ ] Run: `setup.bat` (Windows) or `./setup.sh` (Linux/Mac)
  - Script will generate `.env` from `.env.example`
  - Script will create `venv` virtual environment
  - Script will install all dependencies
- [ ] Verify output shows: "[SUCCESS]" messages
- [ ] If errors, review error messages and troubleshooting section

---

## 🔐 Phase 2: Configuration & Credentials

### Step 4: Open .env File
- [ ] Open `.env` file in text editor (Notepad, VS Code, etc.)
- [ ] **DO NOT** commit this file to git (already in .gitignore)
- [ ] Locate required fields (see steps below)

### Step 5: Generate SECRET_KEY
**Purpose:** Encryption key for session management and security

**Location in .env:** Line ~1
```
SECRET_KEY=
```

**How to generate:**
Open command prompt and run:
```
python -c "import secrets; print(secrets.token_hex(32))"
```

**Example output:**
```
a7f3e9b1c2d4f6a8e0b3c5d7f9a1c3e5f7a9b1c3d5e7f9a1b3c5d7e9f0a1b3
```

Copy the output and paste after `SECRET_KEY=`:
```
SECRET_KEY=a7f3e9b1c2d4f6a8e0b3c5d7f9a1c3e5f7a9b1c3d5e7f9a1b3c5d7e9f0a1b3
```

- [ ] SECRET_KEY set (64 characters, no quotes)
- [ ] **Important:** Different key for development, staging, and production

---

### Step 6: Configure Email (SMTP)

**Purpose:** Send OTP emails for signup and password reset

**Supported Providers:**
- [ ] Gmail
- [ ] Outlook
- [ ] AWS SES
- [ ] SendGrid
- [ ] Generic SMTP

#### Option A: Gmail (Easiest)

1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" and "Windows Computer"
3. Copy the 16-character app password
4. Update `.env`:

```
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=xxxx xxxx xxxx xxxx    (16-char app password, remove spaces)
MAIL_FROM_EMAIL=your-email@gmail.com
```

- [ ] Gmail SMTP configured (if using Gmail)

#### Option B: Outlook

1. Use your Outlook email and password
2. Update `.env`:

```
MAIL_SERVER=smtp-mail.outlook.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@outlook.com
MAIL_PASSWORD=your-outlook-password
MAIL_FROM_EMAIL=your-email@outlook.com
```

- [ ] Outlook SMTP configured (if using Outlook)

#### Option C: AWS SES

1. Configure SMTP credentials in AWS SES console
2. Update `.env`:

```
MAIL_SERVER=email-smtp.us-east-1.amazonaws.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-aws-smtp-username
MAIL_PASSWORD=your-aws-smtp-password
MAIL_FROM_EMAIL=noreply@yourdomain.com
```

- [ ] AWS SES configured (if using AWS)

#### Option D: Custom SMTP Server

Update `.env` with your server details:

```
MAIL_SERVER=your-smtp-server.com
MAIL_PORT=587          (or 465 for SSL, or 25 for non-TLS)
MAIL_USE_TLS=True      (False for SSL, False for no TLS)
MAIL_USERNAME=username-or-email
MAIL_PASSWORD=password
MAIL_FROM_EMAIL=sender@domain.com
```

- [ ] Email SMTP configured with valid credentials
- [ ] Test email address saved for verification later

---

### Step 7: Configure Gemini API (Optional)

**Purpose:** AI-powered features in application

**If NOT using AI features:**
- [ ] Leave blank or set dummy value: `GEMINI_API_KEY=test`

**If using AI features:**

1. Go to https://ai.google.dev/
2. Create account and get API key
3. Update `.env`:

```
GEMINI_API_KEY=your-actual-api-key-here
```

- [ ] Gemini API key configured (or marked as not needed)

---

### Step 8: Configure Database

**Purpose:** Store application data

**Default (SQLite):**
```
DATABASE_URL=sqlite:///instance/deliveries.db
```

- [ ] Keep default (localhost development)

**For PostgreSQL (if available):**

Update `.env`:
```
DATABASE_URL=postgresql://username:password@localhost:5432/crmdelivery
```

Then install PostgreSQL driver:
```
pip install psycopg2-binary
```

- [ ] Database URL configured

---

### Step 9: Configure File Upload Settings

**Location in .env:**
```
MAX_UPLOAD_SIZE=16777216          (16 MB in bytes)
ALLOWED_EXTENSIONS=pdf,csv,xlsx,xls,txt,jpg,png,jpeg
```

**Adjust if needed:**
- Increase `MAX_UPLOAD_SIZE` for larger files
- Add/remove file types in `ALLOWED_EXTENSIONS`

- [ ] File upload settings reviewed and adjusted if needed

---

### Step 10: Configure Security Settings

**JWT Configuration (for API/web tokens):**
```
JWT_EXPIRY_DAYS=30
```

- Adjust token expiry if needed (default: 30 days)

**CORS Configuration (for API access):**
```
CORS_ORIGINS=http://localhost:5000,http://localhost:3000
```

- Add frontend URLs if accessing from different domain

**Other Security:**
```
SECURE_COOKIES=False        (Set True in production with HTTPS)
TESTING_MODE=False          (Never True in production)
```

- [ ] Security settings reviewed and configured

---

### Step 11: Optional Feature Flags

**Location in .env:**
```
ENABLE_OTP_VERIFICATION=True           (Email OTP for signup)
ENABLE_EMAIL_NOTIFICATIONS=True        (Auto-send emails)
ENABLE_AUTO_BACKUPS=False              (Auto database backups)
```

Configure based on your needs:

- [ ] Enable/disable OTP verification as needed
- [ ] Enable/disable email notifications as needed
- [ ] Enable/disable auto-backups as needed

---

### Step 12: System Configuration

**Timezone (affects reporting and timestamps):**
```
TIMEZONE=Asia/Kolkata    (or your timezone)
```

**Log Level (for debugging):**
```
LOG_LEVEL=DEBUG          (Use INFO in production)
```

**Development Mode:**
```
DEVELOPMENT_MODE=True    (Set False in production)
```

- [ ] Timezone configured for your region
- [ ] Log level appropriate for environment
- [ ] Development mode flag set correctly

---

## ✅ Phase 3: Verification & Testing

### Step 13: Verify Configuration File

- [ ] Open `.env` file and visually inspect:
  - [ ] SECRET_KEY: Present and 64+ characters
  - [ ] MAIL_SERVER: Not empty
  - [ ] MAIL_USERNAME: Valid email address
  - [ ] MAIL_PASSWORD: Filled in (saved, not stored as text)
  - [ ] DATABASE_URL: Valid connection string
  - [ ] All required settings filled

- [ ] No test/placeholder values remain (except optional API keys)

---

### Step 14: Verify Dependencies

Run in command prompt:
```
pip list | find "Flask"
```

Expected output should show installed packages. If empty, run:
```
pip install -r requirements.txt
```

- [ ] All dependencies installed
- [ ] Virtual environment activated (shows "venv" in prompt)

---

### Step 15: Test Application Start

Run:
```
run.bat    (Windows)
./run.sh   (Linux/Mac)
```

**Expected output:**
```
[INFO] Activating virtual environment...
[SUCCESS] All checks passed!
Starting Flask Application...
Server will start at: http://localhost:5000
 * Running on http://127.0.0.1:5000
```

- [ ] Flask server starts without errors
- [ ] No "ModuleNotFoundError" messages
- [ ] Server accessible at http://localhost:5000

---

### Step 16: Test Web Interface

1. Open browser: http://localhost:5000
2. You should see the login page

**Check if:**
- [ ] Login page loads without errors
- [ ] Page styling looks correct (no broken CSS/images)
- [ ] "Create Account" link visible

---

### Step 17: Test Signup Process

1. Click "Create Account" link
2. Fill in registration form:
   - Username: `testuser`
   - Email: `your-test-email@gmail.com` (or test email)
   - Password: `Test@123` (something with mixed case and numbers)
   - Confirm: Same password
3. Click "Sign Up"

**Expected behavior:**
- [ ] Form validates correctly (e.g., password must match)
- [ ] Form submits to verification page
- [ ] See "6-digit OTP" entry screen

---

### Step 18: Test Email Delivery

**During OTP verification page:**

1. Check your email inbox (the email you entered during signup)
2. Look for subject: "CRM Delivery - Verify Your Email"

**If email received:**
- [ ] Email arrived within 30 seconds
- [ ] OTP code visible in email
- [ ] Email from address correct (MAIL_FROM_EMAIL)

**If email NOT received:**

Check these in order:
1. Check spam/junk folder
2. Verify MAIL_* settings in `.env` are correct
3. For Gmail: Confirm app-specific password used (not account password)
4. For Outlook: Enable "Less Secure App Access" if using account password
5. Check console output for error messages (run.bat shows detailed logs)

**Continue with verification:**
- [ ] Enter the 6-digit OTP from email
- [ ] Click "Verify"
- [ ] Account created successfully
- [ ] Redirected to login page

---

### Step 19: Test Login

1. Login page should show
2. Enter credentials:
   - Username: `testuser`
   - Password: `Test@123`
3. Click "Login"

**Expected behavior:**
- [ ] Login successful
- [ ] Redirected to dashboard
- [ ] Menu shows appropriate options for user role
- [ ] No error messages

- [ ] Login works with created account

---

### Step 20: Test Dashboard Access

Based on the role assigned (should be "staff" for signup):

- [ ] Dashboard loads without errors
- [ ] Data displays correctly
- [ ] Sidebar shows appropriate menu items
- [ ] No database errors in console

- [ ] Dashboard functionality verified

---

## 📊 Phase 4: Production Preparation

### Step 21: Change Environment to Production

When ready to deploy (not yet):

1. Update `.env`:
```
FLASK_ENV=production
DEVELOPMENT_MODE=False
DEBUG_MODE=False
LOG_LEVEL=INFO
SECURE_COOKIES=True
```

2. Generate new SECRET_KEY (different from development)

3. Use production database:
```
DATABASE_URL=postgresql://user:pass@prod-server:5432/crmdelivery
```

4. Update email credentials to production account

- [ ] Production environment configuration noted (for later)

---

### Step 22: Backup Configuration

1. Create secure backup of `.env`:
   ```
   copy .env .env.backup
   ```

2. Store securely (encrypted, not in version control)

3. Document all configuration secrets in secure location (password manager, etc.)

- [ ] Configuration backup created

---

### Step 23: Database Initialization (If Needed)

First-run database creation:

The Flask app creates database on first run. To verify:
1. Check `instance/deliveries.db` exists
2. Should appear after application first loads

**If manual initialization needed:**
```
python
>>> from app import app, db
>>> with app.app_context():
>>>     db.create_all()
>>> exit()
```

- [ ] Database file exists: `instance/deliveries.db`

---

### Step 24: Create Admin User (If Needed)

For admin access without signup:

```
python
>>> from app import app, db
>>> from models import User
>>> with app.app_context():
>>>     admin = User(username='admin', email='admin@example.com', password='AdminPassword123', role='admin')
>>>     db.session.add(admin)
>>>     db.session.commit()
>>> exit()
```

- [ ] Admin user created (optional, can use signup instead)

---

## 🎉 Phase 5: Completion

### Final Verification Checklist

- [ ] `.env` file exists with all required settings
- [ ] SECRET_KEY generated and set
- [ ] Email SMTP configured and credentials verified
- [ ] Database initialized and accessible
- [ ] Virtual environment setup and dependencies installed
- [ ] Flask application starts without errors
- [ ] Web interface loads correctly
- [ ] Signup/verification flow works
- [ ] Login works with created account
- [ ] Dashboard accessible and shows data
- [ ] Email sending verified (test email received)

---

### Summary of Configuration Files

**Key Files Created/Modified:**
1. ✅ `.env` - Configuration (YOU CREATED)
2. ✅ `config.py` - Flask config reading from .env
3. ✅ `app.py` - Sign up routes and OTP email
4. ✅ Database - Auto-created on first run

**Documentation Files:**
1. ✅ `QUICK_START.md` - Quick setup instructions
2. ✅ `ENV_SETUP_GUIDE.md` - Detailed configuration guide
3. ✅ `SETUP_CHECKLIST.md` - This file
4. ✅ `README.md` - Project overview

---

## 🆘 Troubleshooting Reference

### Email Not Sending

**Gmail:**
- Use app-specific password, not account password
- Generate at: https://myaccount.google.com/apppasswords
- Account must have 2FA enabled

**Outlook:**
- Enable "Less Secure App Access"
- Or use app-specific password if available

**Check Credentials:**
- Verify MAIL_USERNAME and MAIL_PASSWORD are exact
- No extra spaces before/after
- Special characters properly escaped

**Check Logs:**
- Run Flask app in console (run.bat)
- Watch for email errors in application output

### Application Won't Start

**Port Already In Use:**
- Change port in .env: `FLASK_PORT=5001`

**Module Not Found:**
- Verify virtual environment activated: `venv\Scripts\activate`
- Reinstall dependencies: `pip install -r requirements.txt`

**Database Error:**
- Delete `instance/deliveries.db` to start fresh
- Flask will recreate on next run

### Can't Login

**Incorrect Credentials:**
- Verify username/password entered during signup
- Remember: Case-sensitive

**Database Issue:**
- Check `instance/deliveries.db` exists
- Try deleting and restarting application

---

## 📞 Next Steps

Once all checkmarks completed:

1. ✅ **Congratulations!** System is fully configured
2. **Optional:** Create additional admin users
3. **Optional:** Customize email templates
4. **Optional:** Configure backup strategy
5. **Ready:** Deploy to production when needed

---

**Configuration Status:** ✅ COMPLETE
**Estimated Time:** 30-60 minutes
**Difficulty:** Beginner (mostly copy-paste)
**Support Files:** ENV_SETUP_GUIDE.md (detailed provider instructions)

---

**Last Updated:** 2024  
**Version:** 1.0  
**Status:** Production Ready
