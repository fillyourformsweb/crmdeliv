from app import app, db
from models import DefaultStatePrice, Client, ClientStatePrice
import random

def seed_pricing():
    with app.app_context():
        print("Seeding Pricing Data for all 36 Indian States & UTs...")

        # All 28 States + 8 Union Territories of India
        states = [
            # 28 States
            'Andhra Pradesh',
            'Arunachal Pradesh',
            'Assam',
            'Bihar',
            'Chhattisgarh',
            'Goa',
            'Gujarat',
            'Haryana',
            'Himachal Pradesh',
            'Jharkhand',
            'Karnataka',
            'Kerala',
            'Madhya Pradesh',
            'Maharashtra',
            'Manipur',
            'Meghalaya',
            'Mizoram',
            'Nagaland',
            'Odisha',
            'Punjab',
            'Rajasthan',
            'Sikkim',
            'Tamil Nadu',
            'Telangana',
            'Tripura',
            'Uttar Pradesh',
            'Uttarakhand',
            'West Bengal',
            # 8 Union Territories
            'Andaman and Nicobar Islands',
            'Chandigarh',
            'Dadra and Nagar Haveli and Daman and Diu',
            'Delhi',
            'Jammu and Kashmir',
            'Ladakh',
            'Lakshadweep',
            'Puducherry',
        ]

        added = 0
        for state in states:
            if not DefaultStatePrice.query.filter_by(state=state).first():
                base = random.randint(40, 90)
                price = DefaultStatePrice(
                    state=state,
                    price_100gm=base,
                    price_250gm=base + 10,
                    price_500gm=base + 25,
                    price_750gm=base + 45,
                    price_1kg=base + 65,
                    price_2kg=(base + 65) * 2 - 20,
                    price_3kg=(base + 65) * 3 - 50,
                )
                db.session.add(price)
                print(f"  Added default prices for {state}")
                added += 1
            else:
                print(f"  Skipped (already exists): {state}")

        db.session.commit()
        print(f"\nDefault state prices: {added} new records added.")

        # 2. Client Custom Prices (first client gets discounted rates for first 5 states)
        clients = Client.query.all()
        if not clients:
            print("No clients found. Skipping client custom prices.")
        else:
            client = clients[0]
            print(f"\nSetting custom prices for client: {client.name}")
            ca = 0
            for state in states[:5]:
                if not ClientStatePrice.query.filter_by(client_id=client.id, state=state).first():
                    base = random.randint(30, 60)
                    custom = ClientStatePrice(
                        client_id=client.id,
                        state=state,
                        price_100gm=base,
                        price_250gm=base + 5,
                        price_500gm=base + 15,
                        price_750gm=base + 30,
                        price_1kg=base + 50,
                        price_2kg=(base + 50) * 2 - 30,
                        price_3kg=(base + 50) * 3 - 60,
                    )
                    db.session.add(custom)
                    print(f"  Added custom prices for {client.name} in {state}")
                    ca += 1
            db.session.commit()
            print(f"Client custom prices: {ca} new records added.")

        print("\nPricing seeding complete!")

if __name__ == '__main__':
    seed_pricing()
