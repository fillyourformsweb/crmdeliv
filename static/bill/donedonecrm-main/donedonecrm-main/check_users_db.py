
from app import app, db, User, BranchNew

with app.app_context():
    users = User.query.all()
    print("Users Table Contents:")
    print("-" * 30)
    for u in users:
        branch_name = u.branch.name if u.branch else "None"
        branch_code = u.branch.code if u.branch else "None"
        print(f"ID: {u.id}, Username: {u.username}, BranchID: {u.branch_id}, BranchName: {branch_name}, BranchCode: {branch_code}")
    print("-" * 30)
