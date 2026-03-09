from app import app, calculate_order_amount
from models import db, Client, ClientStatePrice, NormalClientStatePrice, DefaultStatePrice

def verify_pricing():
    with app.app_context():
        print("--- Pricing Logic Verification ---")
        
        state = "Maharashtra"
        state_lower = state.lower()
        
        # Cleanup existing test data if any
        DefaultStatePrice.query.filter_by(state=state).delete()
        NormalClientStatePrice.query.filter_by(state=state).delete()
        ClientStatePrice.query.filter_by(state=state).delete()
        db.session.commit()
        
        # 1. Setup Price Master (DefaultStatePrice)
        p_master = DefaultStatePrice(state=state, price_1kg=100)
        db.session.add(p_master)
        db.session.commit()
        
        # Test Case 1: Walk-in order should use Price Master
        res = calculate_order_amount(weight=1.0, state=state, client_id=None)
        print(f"Walk-in (Expected 100): {res[4]} (Source: {res[5]})")
        
        # Test Case 2: Client order (no custom, no normal default) should use Price Master
        res = calculate_order_amount(weight=1.0, state=state, client_id=1)
        print(f"Client No Custom (Expected 100): {res[4]} (Source: {res[5]})")
        
        # 2. Setup Normal Client Default (NormalClientStatePrice)
        n_client = NormalClientStatePrice(state=state, price_1kg=80)
        db.session.add(n_client)
        db.session.commit()
        
        # Test Case 3: Client order (no custom) should now use Normal Client Default
        res = calculate_order_amount(weight=1.0, state=state, client_id=1)
        print(f"Client Default (Expected 80): {res[4]} (Source: {res[5]})")
        
        # Test Case 4: Walk-in should STILL use Price Master
        res = calculate_order_amount(weight=1.0, state=state, client_id=None)
        print(f"Walk-in Still Master (Expected 100): {res[4]} (Source: {res[5]})")
        
        # 3. Setup Client Specific Price
        c_spec = ClientStatePrice(client_id=1, state=state, price_1kg=60)
        db.session.add(c_spec)
        db.session.commit()
        
        # Test Case 5: Client order (with custom) should use Client Specific Price
        res = calculate_order_amount(weight=1.0, state=state, client_id=1)
        print(f"Client Specific (Expected 60): {res[4]} (Source: {res[5]})")
        
        # Test Case 6: Different client should still use Normal Client Default
        res = calculate_order_amount(weight=1.0, state=state, client_id=2)
        print(f"Other Client (Expected 80): {res[4]} (Source: {res[5]})")
        
        print("\nVerification complete.")

if __name__ == "__main__":
    verify_pricing()
