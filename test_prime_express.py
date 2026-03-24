#!/usr/bin/env python3
"""
Test Prime Express Pricing Logic
Tests weight-based calculation tiers
"""

# Mock price object for testing
class MockPriceObj:
    def __init__(self, price_1kg=180, price_extra_per_kg=120):
        self.price_1kg = price_1kg
        self.price_extra_per_kg = price_extra_per_kg
        self.shipping_mode = 'prime_express'

def calculate_from_state_price(weight, price_obj, shipping_mode='standard'):
    """Prime Express calculation function (copied from app.py)"""
    amount = 0
    
    # Check if this is prime_express (special weight-based tiers)
    is_prime_express = getattr(price_obj, 'shipping_mode', 'standard').lower() == 'prime_express' or shipping_mode.lower() == 'prime_express'
    
    if is_prime_express:
        # Prime Express special weight-based calculation
        price_1kg = getattr(price_obj, 'price_1kg', 0) or 0
        price_extra = getattr(price_obj, 'price_extra_per_kg', 0) or 0
        
        if weight <= 1.0:
            # ≤1kg: charge 1kg rate
            amount = price_1kg
        elif weight <= 1.5:
            # 1.1-1.5kg: charge (1kg rate + 1kg rate/2)
            amount = price_1kg + (price_1kg / 2)
        elif weight <= 2.0:
            # 1.51-2kg: charge (1kg rate × 2)
            amount = price_1kg * 2
        else:
            # >2kg: use per-kg rate for entire weight
            amount = weight * price_extra if price_extra > 0 else (price_1kg * 2)
    
    if amount == 0:
        return None
    
    return amount

# Test data
test_cases = [
    # (weight, expected_formula, expected_amount)
    (0.5, "≤1kg: 1kg rate", 180),
    (1.0, "≤1kg: 1kg rate", 180),
    (1.1, "1.1-1.5kg: 1kg + 1kg/2", 270),
    (1.25, "1.1-1.5kg: 1kg + 1kg/2", 270),
    (1.5, "1.1-1.5kg: 1kg + 1kg/2", 270),
    (1.51, "1.51-2kg: 1kg × 2", 360),
    (1.75, "1.51-2kg: 1kg × 2", 360),
    (2.0, "1.51-2kg: 1kg × 2", 360),
    (2.5, ">2kg: 2.5kg × 120/kg", 300),
    (3.0, ">2kg: 3kg × 120/kg", 360),
    (5.0, ">2kg: 5kg × 120/kg", 600),
]

print("=" * 70)
print("PRIME EXPRESS PRICING TEST")
print("=" * 70)
print(f"{'Weight (kg)':<12} {'Formula':<30} {'Expected ₹':<12} {'Actual ₹':<12} {'Status':<8}")
print("-" * 70)

price_obj = MockPriceObj(price_1kg=180, price_extra_per_kg=120)

all_passed = True
for weight, formula, expected in test_cases:
    actual = calculate_from_state_price(weight, price_obj, 'prime_express')
    passed = actual == expected
    status = "✅ PASS" if passed else "❌ FAIL"
    
    if not passed:
        all_passed = False
    
    print(f"{weight:<12.2f} {formula:<30} {expected:<12.2f} {actual:<12.2f} {status:<8}")

print("-" * 70)

# Test with different base rates
print("\n" + "=" * 70)
print("TEST WITH DIFFERENT BASE RATES (1kg rate = ₹200, extra = ₹150/kg)")
print("=" * 70)

price_obj2 = MockPriceObj(price_1kg=200, price_extra_per_kg=150)

test_cases2 = [
    (0.8, "≤1kg: 1kg rate", 200),
    (1.2, "1.1-1.5kg: 1kg + 1kg/2", 300),
    (1.75, "1.51-2kg: 1kg × 2", 400),
    (3.0, ">2kg: 3kg × 150/kg", 450),
]

print(f"{'Weight (kg)':<12} {'Formula':<30} {'Expected ₹':<12} {'Actual ₹':<12} {'Status':<8}")
print("-" * 70)

for weight, formula, expected in test_cases2:
    actual = calculate_from_state_price(weight, price_obj2, 'prime_express')
    passed = actual == expected
    status = "✅ PASS" if passed else "❌ FAIL"
    
    if not passed:
        all_passed = False
    
    print(f"{weight:<12.2f} {formula:<30} {expected:<12.2f} {actual:<12.2f} {status:<8}")

print("-" * 70)

# Summary
print("\n" + "=" * 70)
if all_passed:
    print("✅ ALL TESTS PASSED!")
else:
    print("❌ SOME TESTS FAILED!")
print("=" * 70)
