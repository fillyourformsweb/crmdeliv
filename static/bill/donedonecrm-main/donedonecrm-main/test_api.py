
from app import app, db, User
import json

app.config['TESTING'] = True
client = app.test_client()

with app.app_context():
    # We need to bypass login_required or simulate a session
    # The easiest way in a test is to use a session transaction
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'admin'
        sess['username'] = 'admin'
        sess['_fresh'] = True

    print("Testing GET /api/quick_services...")
    response = client.get('/api/quick_services')
    print(f"Status: {response.status_code}")
    print(f"Data: {response.get_data(as_text=True)}")

    print("\nTesting POST /api/quick_services...")
    data = {
        'name': 'New Test Service',
        'price': 25.0,
        'unit': 'Per Hour',
        'description': 'Description here'
    }
    response = client.post('/api/quick_services', 
                           data=json.dumps(data),
                           content_type='application/json')
    print(f"Status: {response.status_code}")
    print(f"Data: {response.get_data(as_text=True)}")

    print("\nTesting DELETE /api/quick_services?id=100...")
    response = client.delete('/api/quick_services?id=100')
    print(f"Status: {response.status_code}")
    print(f"Data: {response.get_data(as_text=True)}")

    print("\nTesting GET /api/quick_services again (should not show ID 100)...")
    response = client.get('/api/quick_services')
    print(f"Data: {response.get_data(as_text=True)}")
