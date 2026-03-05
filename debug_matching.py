from app import app, db
from models import Order, ExcelData

with app.app_context():
    order_receipts = [o.receipt_number for o in Order.query.limit(20).all()]
    excel_receipts = [e.receipt_number for e in ExcelData.query.limit(20).all()]
    
    print(f"Order Receipts in DB: {order_receipts}")
    print(f"Excel Receipts in DB: {excel_receipts}")
    
    matches = Order.query.filter(Order.receipt_number.in_(excel_receipts)).all()
    print(f"Direct matches found: {len(matches)}")
