from app import app
from models import Order, ReceiptSetting, StaffReceiptAssignment, DefaultStatePrice, ClientStatePrice

with app.app_context():
    print("--- ALL Receipt Settings ---")
    settings = ReceiptSetting.query.all()
    for s in settings:
        print(f"ID {s.id}: Prefix={s.prefix}, Base={s.base_number}, Seq={s.current_sequence}, Active={s.is_active}")
    
    print("\n--- ALL Staff Assignments ---")
    assignments = StaffReceiptAssignment.query.all()
    for a in assignments:
        print(f"Assignment ID {a.id}: User={a.user_id}, Branch={a.branch_id}, Prefix={a.prefix}, Base={a.base_number}, Seq={a.current_sequence}, Active={a.is_active}")

    print("\n--- Pricing Verification ---")
    all_prices = DefaultStatePrice.query.all()
    if all_prices:
        print(f"Total States: {len(all_prices)}")
        for p in all_prices:
            print(f"State: {p.state}, 1kg={p.price_1kg}")
    else:
        print("No DefaultStatePrice entries found in DB.")

    print("\n--- Order Form Context (Likely User) ---")
    # Let's assume user id 1 (admin) or something
    from models import User
    u = User.query.get(1) # Try to see what admin gets
    if u:
        import app as app_module
        predicted = app_module.get_next_receipt_number(u)
        print(f"Admin's predicted receipt: {predicted}")
    
    # Check for User 19 or 17 from assignments
    for uid in [17, 19]:
        u = User.query.get(uid)
        if u:
            predicted = app_module.get_next_receipt_number(u)
            print(f"User {uid} ({u.username}) predicted receipt: {predicted}")
