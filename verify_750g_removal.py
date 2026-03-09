
import os
import sys
from app import app, db, DefaultStatePrice, Client, ClientStatePrice, NormalClientStatePrice, calculate_from_state_price

def test_750g_removal():
    with app.app_context():
        print("Starting 750g removal verification...")
        
        # Test case: Global Price Master
        # Mocking a price object
        class MockPrice:
            def __init__(self, p100, p250, p500, p1, p2, p3):
                self.price_100gm = p100
                self.price_250gm = p250
                self.price_500gm = p500
                self.price_1kg = p1
                self.price_2kg = p2
                self.price_3kg = p3
        
        price_obj = MockPrice(10, 20, 30, 100, 200, 300)
        
        # weights to test
        # 0.1 -> 10
        # 0.25 -> 20
        # 0.5 -> 30
        # 0.6 -> 100 (previously would have been 750g price if defined, or 1kg)
        # 0.75 -> 100
        # 0.8 -> 100
        # 1.0 -> 100
        
        test_weights = [
            (0.1, 10),
            (0.25, 20),
            (0.5, 30),
            (0.6, 100),
            (0.75, 100),
            (1.0, 100),
            (1.5, 200),
            (2.5, 300)
        ]
        
        success = True
        for weight, expected in test_weights:
            actual = calculate_from_state_price(weight, price_obj)
            if actual == expected:
                print(f"  PASS: Weight {weight}kg -> ₹{actual}")
            else:
                print(f"  FAIL: Weight {weight}kg -> Expected ₹{expected}, got ₹{actual}")
                success = False
        
        if success:
            print("\nVerification SUCCESSFUL: Weights > 0.5kg and <= 1.0kg correctly fall into 1kg category.")
        else:
            print("\nVerification FAILED.")

if __name__ == "__main__":
    test_750g_removal()
