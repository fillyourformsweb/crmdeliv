from app import app, db, Order
from sqlalchemy import func
with app.app_context():
    print(db.session.query(Order.status, func.count(Order.id)).group_by(Order.status).all())
