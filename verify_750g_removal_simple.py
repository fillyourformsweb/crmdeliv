
def calculate_from_state_price(weight, price_obj):
    if weight <= 0.1: amount = price_obj.price_100gm
    elif weight <= 0.25: amount = price_obj.price_250gm
    elif weight <= 0.5: amount = price_obj.price_500gm
    elif weight <= 1.0: amount = price_obj.price_1kg
    elif weight <= 2.0: amount = price_obj.price_2kg
    elif weight <= 3.0: amount = price_obj.price_3kg
    else: amount = 0 # Handle > 3kg if needed
    
    return amount

class MockPrice:
    def __init__(self, p100, p250, p500, p1, p2, p3):
        self.price_100gm = p100
        self.price_250gm = p250
        self.price_500gm = p500
        self.price_1kg = p1
        self.price_2kg = p2
        self.price_3kg = p3

def test_750g_removal():
    print("Starting 750g removal verification...")
    
    price_obj = MockPrice(10, 20, 30, 100, 200, 300)
    
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
