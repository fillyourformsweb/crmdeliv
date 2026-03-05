from app import app, db, BranchNew
with app.app_context():
    branches = BranchNew.query.all()
    for b in branches:
        print(f'ID: {b.id}, Code: {b.code}, Name: {b.name}')
