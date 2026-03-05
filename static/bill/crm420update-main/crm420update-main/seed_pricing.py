from app import app, db
from models import DefaultStatePrice, Client, ClientStatePrice
import random

def seed_pricing():
    with app.app_context():
        print("Seeding Pricing Data...")
        
        # 1. Default State Prices
        states = [
            'Maharashtra', 'Delhi', 'Karnataka', 'Tamil Nadu', 
            'Gujarat', 'West Bengal', 'Rajasthan', 'Telangana'
        ]
        
        for state in states:
            if not DefaultStatePrice.query.filter_by(state=state).first():
                base = random.randint(40, 80)
                price = DefaultStatePrice(
                    state=state,
                    price_100gm=base,
                    price_250gm=base + 10,
                    price_500gm=base + 20,
                    price_750gm=base + 40,
                    price_1kg=base + 60,
                    price_2kg=(base + 60) * 2 - 20,
                    price_3kg=(base + 60) * 3 - 50
                )
                db.session.add(price)
                print(f"Added default prices for {state}")
        
        db.session.commit()
        
        # 2. Client Custom Prices
        clients = Client.query.all()
        if not clients:
            print("No clients found. Please run seed_db.py first or manually add clients.")
        else:
            # Pick a random client to have special rates for a few states
            client = clients[0]
            print(f"Setting custom prices for client: {client.name}")
            
            for state in states[:3]: # First 3 states
                if not ClientStatePrice.query.filter_by(client_id=client.id, state=state).first():
                    base = random.randint(30, 60) # Cheaper rates for client
                    custom = ClientStatePrice(
                        client_id=client.id,
                        state=state,
                        price_100gm=base,
                        price_250gm=base + 5,
                        price_500gm=base + 15,
                        price_750gm=base + 30,
                        price_1kg=base + 50,
                        price_2kg=(base + 50) * 2 - 30,
                        price_3kg=(base + 50) * 3 - 60
                    )
                    db.session.add(custom)
                    print(f"Added custom prices for {client.name} in {state}")
            
            db.session.commit()
            
        print("Pricing seeding complete.")

if __name__ == '__main__':
    seed_pricing()
