from app import app, db, Role, User

with app.app_context():
    print("Deleting all existing roles...")
    Role.query.delete()
    db.session.commit()
    print("✓ All roles deleted")
    
    print("\nDeleting test users...")
    User.query.filter(User.useridname.in_(['teststaff', 'testmanager'])).delete()
    db.session.commit()
    print("✓ Test users deleted")
    
    print("\nRecreating default roles...")
    from app import create_default_roles
    create_default_roles()
    print("✓ Default roles recreated")
    
    print("\nVerifying roles:")
    for role in Role.query.all():
        print(f"  - {role.roleidname}: {role.rolename}")
