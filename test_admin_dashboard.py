#!/usr/bin/env python
"""Test script to verify admin_dashboard works correctly"""

from app import app, db
from models import Order, User
from sqlalchemy import func
from datetime import datetime, timedelta

print("Testing admin_dashboard queries...")

try:
    with app.app_context():
        # Simulate the admin_dashboard function
        days_filter = 30
        start_date = datetime.now(timezone.utc) - timedelta(days=days_filter)
        
        print("\n1. Testing total_shipments query...")
        total_shipments = Order.query.count()
        print(f"   ✓ Total Shipments: {total_shipments}")
        
        print("\n2. Testing total_revenue query...")
        total_revenue = db.session.query(func.sum(Order.total_amount)).scalar() or 0
        print(f"   ✓ Total Revenue: {total_revenue}")
        
        print("\n3. Testing recent_shipments query...")
        recent_shipments = Order.query.filter(Order.created_at >= start_date).count()
        print(f"   ✓ Recent Shipments: {recent_shipments}")
        
        print("\n4. Testing status_dist query...")
        status_dist_rows = db.session.query(
            Order.status,
            func.count(Order.id).label('count')
        ).filter(Order.created_at >= start_date).group_by(Order.status).all()
        status_dist = [{'status': row.status, 'count': row.count} for row in status_dist_rows]
        print(f"   ✓ Status Distribution: {status_dist}")
        
        print("\n5. Testing daily_revenue query...")
        daily_revenue_rows = db.session.query(
            func.date(Order.created_at).label('order_date'),
            func.count(Order.id).label('order_count'),
            func.sum(Order.total_amount).label('daily_total')
        ).filter(Order.created_at >= (datetime.now(timezone.utc) - timedelta(days=7))).group_by(
            func.date(Order.created_at)
        ).order_by('order_date').all()
        daily_revenue = [{'order_date': str(row.order_date), 'order_count': row.order_count, 'daily_total': float(row.daily_total) if row.daily_total else 0} for row in daily_revenue_rows]
        print(f"   ✓ Daily Revenue: {len(daily_revenue)} entries")
        
        print("\n✅ ALL QUERIES WORKING CORRECTLY!")
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
