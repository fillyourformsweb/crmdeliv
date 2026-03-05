from app import app, db, Attendance, PendingTaskReason
from sqlalchemy import text

def migrate():
    with app.app_context():
        # Create all tables (this will create pending_task_reasons if it doesn't exist)
        db.create_all()
        
        # Manually add columns to attendance table if they don't exist
        try:
            with db.engine.connect() as conn:
                # SQLite doesn't support 'IF NOT EXISTS' for columns easily in a single statement
                # We'll just try and catch
                try:
                    conn.execute(text("ALTER TABLE attendance ADD COLUMN online_cash FLOAT DEFAULT 0.0"))
                    print("Added online_cash column to attendance table")
                except Exception as e:
                    print(f"online_cash column might already exist: {e}")
                
                try:
                    conn.execute(text("ALTER TABLE attendance ADD COLUMN extra_amount FLOAT DEFAULT 0.0"))
                    print("Added extra_amount column to attendance table")
                except Exception as e:
                    print(f"extra_amount column might already exist: {e}")
                
                conn.commit()
            print("Migration completed successfully.")
        except Exception as e:
            print(f"Migration error: {e}")

if __name__ == "__main__":
    migrate()
