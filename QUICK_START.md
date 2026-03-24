# CRM Delivery - Quick Start Guide

## 📋 Overview
This guide provides quick setup and running instructions for the CRM Delivery System.

## 🚀 Quickest Setup (Windows)

```batch
setup.bat
run.bat
```

That's it! The setup script will:
1. Create `.env` from `.env.example`
2. Check Python installation
3. Create virtual environment
4. Install all dependencies
5. Create instance directory

Then `run.bat` will start the Flask application.

## 🚀 Quickest Setup (Linux/Mac)

```bash
chmod +x setup.sh run.sh
./setup.sh
./run.sh
```

## 📁 Setup Scripts

### `setup.bat` (Windows) / `setup.sh` (Linux/Mac)
**One-time setup script** - Run this first to prepare your environment.

**What it does:**
- Creates `.env` file from `.env.example`
- Verifies Python 3.8+ installation
- Creates Python virtual environment
- Installs project dependencies from `requirements.txt`
- Creates `instance/` directory for database and uploads

**When to use:**
- First time setting up the project
- After adding new dependencies
- If you accidentally delete `venv` directory

**Usage:**
```
# Windows
setup.bat

# Linux/Mac
./setup.sh
```

---

### `run.bat` (Windows) / `run.sh` (Linux/Mac)
**Quick start script** - Run this to start the application.

**What it does:**
- Activates virtual environment
- Checks dependencies installed
- Starts Flask development server
- Opens at http://localhost:5000

**When to use:**
- Every time you want to run the application
- After subsequent edits to code

**Usage:**
```
# Windows
run.bat

# Linux/Mac
./run.sh
```

---

## ⚙️ Configuration Files

### `.env`
**Environment variables configuration** - Created by `setup.bat`/`.sh`

Copy from `.env.example` and update:
- `SECRET_KEY`: Generate using: `python -c 'import secrets; print(secrets.token_hex(32))'`
- `MAIL_SERVER`: SMTP server (smtp.gmail.com, smtp-mail.outlook.com, etc.)
- `MAIL_USERNAME`: Email address for sending OTPs
- `MAIL_PASSWORD`: Email password or app-specific password
- `GEMINI_API_KEY`: Google Gemini API key (if using AI features)
- `DATABASE_URL`: Database connection string (default: SQLite)

For detailed setup instructions → See **ENV_SETUP_GUIDE.md**

### `.env.example`
**Configuration template** - Do not edit directly

Use this as reference for available configuration options.

---

## 🔍 First Time Setup Checklist

- [ ] Run `setup.bat` (Windows) or `./setup.sh` (Linux/Mac)
- [ ] Edit `.env` file with your configuration
  - [ ] Set `SECRET_KEY`
  - [ ] Configure email (`MAIL_*` settings)
  - [ ] Set `GEMINI_API_KEY` if needed
- [ ] Run `run.bat` (Windows) or `./run.sh` (Linux/Mac)
- [ ] Visit http://localhost:5000
- [ ] Login with default credentials or create new account

---

## 📊 Directory Structure After Setup

```
crmdeliv/
├── venv/                          # Virtual environment (created by setup)
├── instance/                      # Database and instance files (created by setup)
│   ├── deliveries.db             # SQLite database (auto-created on first run)
│   └── uploads/                  # File uploads directory
├── .env                          # Configuration (created by setup)
├── .env.example                  # Configuration template
├── setup.bat / setup.sh          # Setup script
├── run.bat / run.sh              # Run script
├── app.py                        # Flask application
├── config.py                     # Flask configuration
├── requirements.txt              # Python dependencies
├── ENV_SETUP_GUIDE.md           # Detailed setup guide
├── QUICK_START.md               # This file
└── ... (other files)
```

---

## 🐛 Troubleshooting

### Python not found
**Error:** `'python' is not recognized as an internal or external command`

**Solution:** 
- Install Python 3.8+ from https://python.org
- During installation, check "Add Python to PATH"
- Restart command prompt/terminal

### Virtual environment won't activate
**Error:** Script execution is disabled on this system

**Solution (Windows):**
```
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Port 5000 already in use
**Error:** `Address already in use`

**Solution:** 
Change port in `.env`:
```
FLASK_PORT=5001
```

### Module not found error
**Error:** `ModuleNotFoundError: No module named 'flask'`

**Solution:**
- Make sure virtual environment is activated
- Re-run: `pip install -r requirements.txt`

### Email not sending
**Error:** OTP email not arriving

**Solution:**
1. Check `.env` has correct MAIL_* settings
2. For Gmail: Use app-specific password (not account password)
3. Less secure apps must be enabled (if using account password)
4. Check spam folder for email
5. See **ENV_SETUP_GUIDE.md** for provider-specific setup

---

## ✨ New Features: Enhanced Client Order Management

### 1. Saved Receiver Selection
- When creating a client order, quick-select from saved receivers
- Auto-populates all receiver details (name, phone, address, city, state, pincode)
- Saves time for repeat deliveries to same locations

### 2. Handling Tags
- 18 predefined handling tags to mark special shipping instructions
- Tags include: FRAGILE, HANDLE WITH CARE, KEEP DRY, DO NOT BEND, PERISHABLE, HAZARDOUS, etc.
- Custom tags for special requirements (max 50 characters)
- Tags print on shipping label for proper handling

### 3. Additional Charges
- Track four types of charges per order:
  - **Insured Value**: Insurance premium for package contents
  - **Stationary Charge**: Packaging materials cost
  - **Matrix Charge**: Warehouse/processing fee
  - **Custom Charge**: Any miscellaneous charges
- All charges summed and included in order total

### 4. Real-time Pricing Summary
- Live pricing breakdown showing:
  1. Base + Weight Charge
  2. Insurance Surcharge
  3. Additional Charges
  4. **Grand Total**
- Auto-updates when weight, state, insured amount, or charges change

**For detailed workflow → See WORKFLOW.md (Flow 2: Client Order Creation)**

---

## 📚 Additional Resources

- **ENV_SETUP_GUIDE.md** - Detailed configuration for each email provider
- **README.md** - Full project documentation
- **CREDENTIALS.md** - Credential management guide

---

## 🔐 Security Notes

- **Never commit `.env` file** to version control (already in .gitignore)
- **Keep `SECRET_KEY` secret** - Generate on each environment
- **Use strong email passwords** - Consider app-specific passwords for Gmail/Outlook
- **Rotate API keys regularly** - Especially GEMINI_API_KEY in production

---

## 📞 Support

For additional help:
1. Check ENV_SETUP_GUIDE.md for detailed setup instructions
2. Review troubleshooting section above
3. Check Flask development server logs (printed to console)
4. Review app.py for application configuration

---

**Created:** 2024  
**Version:** 1.0  
**Status:** Production Ready
