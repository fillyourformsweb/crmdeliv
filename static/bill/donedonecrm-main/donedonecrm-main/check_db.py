
from app import app, db, Quickservice

with app.app_context():
    services = Quickservice.query.all()
    print(f"Total services: {len(services)}")
    for s in services:
        print(f"ID: {s.quickserviceid}, Name: {s.quickservicename}, Price: {s.quickserviceprice}")
