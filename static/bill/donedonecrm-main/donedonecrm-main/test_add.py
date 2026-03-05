
import requests

# We need to be logged in. Since I don't have a session, I'll use a direct DB insert to test persistence first.
# Wait, let's just use the app context to add a service and see if it shows up in GET.

from app import app, db, Quickservice

with app.app_context():
    print("Adding a new test service...")
    new_service = Quickservice(
        quickserviceid=100,
        quickservicename="AI Debugging",
        quickserviceprice=99.99,
        unit="Per Question",
        description="Help you fix your code"
    )
    db.session.add(new_service)
    db.session.commit()
    print("Service added.")

    services = Quickservice.query.all()
    print(f"Total services in DB: {len(services)}")
    for s in services:
        if s.quickserviceid == 100:
            print(f"Found it: {s.quickservicename}")
