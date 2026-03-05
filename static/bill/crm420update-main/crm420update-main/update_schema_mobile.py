from app import app, db
from sqlalchemy import text

def update_schema():
    with app.app_context():
        # Check if columns exist
        with db.engine.connect() as conn:
            try:
                # Try simple select to check columns
                conn.execute(text("SELECT otp_code FROM users LIMIT 1"))
                print("Columns already exist.")
            except Exception:
                print("Adding OTP columns...")
                try:
                    conn.execute(text("ALTER TABLE users ADD COLUMN otp_code VARCHAR(6)"))
                    conn.execute(text("ALTER TABLE users ADD COLUMN otp_expiry DATETIME"))
                    conn.commit()
                    print("Columns added successfully.")
                except Exception as e:
                    print(f"Error adding columns: {e}")

if __name__ == '__main__':
    update_schema()
