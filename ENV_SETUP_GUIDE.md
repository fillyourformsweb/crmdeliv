# Environment Setup Guide for CRM Delivery System

## Overview
This guide will help you set up the `.env` file with all necessary configurations for the CRM Delivery System.

## Quick Setup

### 1. Copy the Example File
```bash
cp .env.example .env
```

### 2. Update Configuration Values
Edit the `.env` file and replace the placeholder values with your actual configuration.

---

## Configuration Details

### Flask Settings

#### SECRET_KEY
- **Purpose**: Used for session encryption and CSRF protection
- **How to Generate**:
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
- **Example**:
  ```
  SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
  ```

#### FLASK_ENV
- **Values**: `development` or `production`
- **Default**: `development`
- **Tip**: Set to `production` when deploying

#### FLASK_DEBUG
- **Values**: `True` or `False`
- **Default**: `False`
- **Warning**: Never enable in production

---

### Database Configuration

#### DATABASE_URL
Choose one of the following options:

**SQLite (Default - for development)**
```
DATABASE_URL=sqlite:///instance/crm_delivery.db
```

**PostgreSQL (Recommended for production)**
```
DATABASE_URL=postgresql://username:password@localhost:5432/crmdeliv
```

**MySQL**
```
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/crmdeliv
```

> **Note**: Create the database before running the application

---

### Email/SMTP Configuration

Used for sending OTP codes and notifications.

#### Gmail Setup (Recommended)
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Factor Authentication
3. Create an [App Password](https://myaccount.google.com/apppasswords)
4. Use the generated password in `MAIL_PASSWORD`

```
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=xxxx xxxx xxxx xxxx
MAIL_FROM_EMAIL=your_email@gmail.com
```

#### Outlook Setup
```
MAIL_SERVER=smtp-mail.outlook.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@outlook.com
MAIL_PASSWORD=your_password
```

#### AWS SES Setup
```
MAIL_SERVER=email-smtp.region.amazonaws.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_ses_username
MAIL_PASSWORD=your_ses_password
```

#### SendGrid Setup
```
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=apikey
MAIL_PASSWORD=SG.xxxxxxxxxxxxxxxxxxxxx
```

---

### AI Integration

#### Google Gemini API
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create an API key
3. Add to `.env`:
```
GEMINI_API_KEY=your_api_key_here
```

---

### File Upload Settings

#### MAX_UPLOAD_SIZE
- **Value**: 16 (in MB)
- **Range**: 1-100 MB recommended
- **Example**: `MAX_UPLOAD_SIZE=16`

#### ALLOWED_EXTENSIONS
- **Default**: `xlsx,xls,png,jpg,jpeg,pdf`
- **Tip**: Add or remove extensions separated by commas

```
ALLOWED_EXTENSIONS=xlsx,xls,png,jpg,jpeg,pdf,doc,docx
```

---

### Feature Flags

#### OTP Verification
```
ENABLE_OTP_VERIFICATION=True   # Enable/disable email OTP
```

#### Email Notifications
```
ENABLE_EMAIL_NOTIFICATIONS=True   # Enable/disable email notifications
```

#### Auto Backups
```
ENABLE_AUTO_BACKUPS=True   # Enable/disable automatic database backups
```

---

### Security Settings

#### JWT Token Expiry
```
JWT_EXPIRY_DAYS=30   # Token validity in days
```

#### CORS Origins
```
CORS_ORIGINS=http://localhost:5000,http://localhost:3000
```

---

## Complete Example

Here's a complete `.env` file for development:

```
# Flask
SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
FLASK_ENV=development
FLASK_DEBUG=False

# Database
DATABASE_URL=sqlite:///instance/crm_delivery.db

# Email
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=xxxx xxxx xxxx xxxx
MAIL_FROM_EMAIL=your_email@gmail.com

# Gemini
GEMINI_API_KEY=your_api_key_here

# Features
ENABLE_OTP_VERIFICATION=True
ENABLE_EMAIL_NOTIFICATIONS=True

# Settings
TIMEZONE=Asia/Kolkata
LOG_LEVEL=INFO
```

---

## Troubleshooting

### Email Not Sending

1. **Check Gmail**: Verify app password is correct
   - Gmail rejects weak passwords
   - Use the generated app password, not your account password

2. **Check Configuration**:
   ```python
   # In Python shell
   from config import Config
   print(Config.MAIL_SERVER)
   print(Config.MAIL_USERNAME)
   print(Config.MAIL_PASSWORD)  # Should not be empty
   ```

3. **Development Mode**: 
   - Set `DEVELOPMENT_MODE=True` to print OTP to console instead

### Database Connection Issues

1. **SQLite**: Ensure `instance` folder exists
   ```bash
   mkdir -p instance
   ```

2. **PostgreSQL**: Check if service is running
   ```bash
   # Linux/Mac
   pg_isready -h localhost -p 5432
   ```

3. **Connection String**: Verify syntax is correct

### API Key Issues

1. **Gemini**: Verify key from [AI Studio](https://makersuite.google.com/app/apikey)
2. **Check Quotas**: Ensure you haven't exceeded usage limits

---

## Security Best Practices

1. **Never commit `.env` to Git**:
   ```bash
   # .gitignore should contain:
   .env
   .env.local
   *.env.secret
   ```

2. **Rotate Keys Regularly**: Update API keys and secrets periodically

3. **Use Strong Secrets**:
   ```bash
   # Generate 32-character secret
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

4. **Different Values for Environments**:
   - Development: Can use weak credentials
   - Production: Use strong secrets and proper credentials

5. **Backup Safely**: Store `.env` backups securely, not in version control

---

## Environment-Specific Setup

### Development
```
FLASK_ENV=development
FLASK_DEBUG=True
DEVELOPMENT_MODE=True
DATABASE_URL=sqlite:///instance/crm_delivery.db
```

### Production
```
FLASK_ENV=production
FLASK_DEBUG=False
DEVELOPMENT_MODE=False
DATABASE_URL=postgresql://username:password@prod-server:5432/crmdeliv
SECRET_KEY=<strong-generated-secret>
```

### Testing
```
FLASK_ENV=testing
DATABASE_URL=sqlite:///:memory:
ENABLE_OTP_VERIFICATION=False
```

---

## Verification Checklist

After setting up `.env`, verify:

- [ ] `.env` file exists in project root
- [ ] `SECRET_KEY` is set to a strong value
- [ ] `DATABASE_URL` is valid
- [ ] `MAIL_USERNAME` and `MAIL_PASSWORD` are correct
- [ ] `GEMINI_API_KEY` is set (if using AI features)
- [ ] All required variables are set
- [ ] `.env` is in `.gitignore`

---

## Next Steps

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Initialize database:
   ```bash
   python
   >>> from app import app, db
   >>> with app.app_context():
   ...     db.create_all()
   >>> exit()
   ```

3. Run the application:
   ```bash
   python app.py
   ```

4. Access at: `http://localhost:5000`

---

## More Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Gmail App Passwords](https://support.google.com/accounts/answer/185833)
- [Google Gemini API](https://makersuite.google.com/)

---

For questions or issues, please refer to the project documentation or create an issue in the repository.
