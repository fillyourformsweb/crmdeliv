from app import app, db, User, BranchNew
with app.app_context():
    # Find Ratnakar Tripathi (username 'Ratnakar Tripathi')
    user = User.query.filter_by(username='Ratnakar Tripathi').first()
    if user:
        # Assign to 'sadads' (ID 1)
        user.branch_id = 1
        db.session.commit()
        print(f"User {user.username} has been assigned to Branch ID 1 (sadads)")
    else:
        print("User Ratnakar Tripathi not found")
