from app import app, db, User, BranchNew
with app.app_context():
    users = User.query.all()
    print(f"{'ID':<5} | {'Username':<20} | {'Branch ID':<10} | {'Branch Name':<20}")
    print("-" * 60)
    for u in users:
        branch_name = u.branch.name if u.branch else "None"
        print(f"{u.id:<5} | {u.username:<20} | {str(u.branch_id):<10} | {branch_name:<20}")
