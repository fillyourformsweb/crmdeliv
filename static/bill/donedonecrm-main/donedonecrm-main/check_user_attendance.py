from app import app, db, Attendance, User
from datetime import datetime, timezone

with app.app_context():
    today = datetime.now(timezone.utc).date()
    # Find Ratnakar Tripathi (username 'Ratnakar Tripathi')
    user = User.query.filter_by(username='Ratnakar Tripathi').first()
    if user:
        print(f"User: {user.username} (ID: {user.id})")
        print(f"Current Branch ID in User model: {user.branch_id}")
        
        attendances = Attendance.query.filter_by(user_id=user.id).all()
        print(f"\nAttendance records for {user.username}:")
        print(f"{'ID':<5} | {'Date':<15} | {'Branch ID':<10} | {'Status':<15}")
        print("-" * 50)
        for a in attendances:
            check_in_date = a.check_in.date() if a.check_in else "N/A"
            print(f"{a.id:<5} | {str(check_in_date):<15} | {str(a.branch_id):<10} | {a.status:<15}")
    else:
        print("User Ratnakar Tripathi not found")
