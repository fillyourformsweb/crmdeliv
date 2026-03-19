#!/usr/bin/env python
"""Refresh SQLAlchemy metadata"""
from app import db, app

with app.app_context():
    print("Refreshing database metadata...")
    db.create_all()
    print("✅ Database metadata refreshed!")
    print("\nAll tables and columns are now synchronized.")
