from app import app
from models import db, Receiver, ClientAddress

def seed():
    with app.app_context():
        # Target client ID found earlier
        client_id = 1
        
        # Add Dummy Receivers
        receivers = [
            Receiver(
                client_id=client_id,
                name="John Doe",
                company_name="Tech Solutions Ltd",
                phone="9876543210",
                email="john@techsolutions.com",
                address="123 Innovation Drive, Sector 5",
                city="Bangalore",
                state="Karnataka",
                pincode="560001",
                gst_number="29ABCDE1234F1Z5",
                bill_pattern="BLR-NORTH-01"
            ),
            Receiver(
                client_id=client_id,
                name="Jane Smith",
                company_name="Global Retail",
                phone="8765432109",
                email="jane@globalretail.in",
                address="45 Market Street, Fort Area",
                city="Mumbai",
                state="Maharashtra",
                pincode="400001",
                gst_number="27FGHIJ5678K2Z9",
                bill_pattern="MUM-SOUTH-04"
            )
        ]
        
        # Add Dummy Sender Addresses
        addresses = [
            ClientAddress(
                client_id=client_id,
                address_label="Central Warehouse",
                address="Plot 56, Industrial Estate",
                city="Chennai",
                state="Tamil Nadu",
                pincode="600032"
            ),
            ClientAddress(
                client_id=client_id,
                address_label="Regional Office",
                address="Suite 4B, Business Towers",
                city="Delhi",
                state="Delhi",
                pincode="110001"
            )
        ]
        
        db.session.add_all(receivers)
        db.session.add_all(addresses)
        db.session.commit()
        print("Successfully added dummy receivers and addresses for Client ID 1.")

if __name__ == "__main__":
    seed()
