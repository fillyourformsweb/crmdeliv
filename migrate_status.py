from app import app, db, Order
with app.app_context():
    count = Order.query.filter_by(status='pending').update({Order.status: 'at_destination'})
    db.session.commit()
    print(f"Updated {count} orders from 'pending' to 'at_destination'")
