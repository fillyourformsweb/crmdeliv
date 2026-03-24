#!/usr/bin/env python3
"""
Test Prime Express Pricing for Uttarakhand Data
Validates the displayed rates against the formula
"""

# Uttarakhand rates from screenshot
class UttarakhandPrice:
    def __init__(self):
        self.price_1kg = 100  # ≤1KG
        self.price_extra_per_kg = 100  # EXTRA/KG
        self.shipping_mode = 'prime_express'

def calculate_prime_express(weight, price_1kg, price_extra_per_kg):
    """Prime Express calculation"""
    if weight <= 1.0:
        # ≤1kg: charge 1kg rate
        return price_1kg
    elif weight <= 1.5:
        # 1.1-1.5kg: charge (1kg rate + 1kg rate/2)
        return price_1kg + (price_1kg / 2)
    elif weight <= 2.0:
        # 1.51-2kg: charge (1kg rate × 2)
        return price_1kg * 2
    else:
        # >2kg: use per-kg rate
        return weight * price_extra_per_kg

# Uttarakhand test
uttarakhand = UttarakhandPrice()

print("=" * 80)
print("PRIME EXPRESS - UTTARAKHAND PRICING VALIDATION")
print("=" * 80)
print(f"\nBase Rate (1kg): ₹{uttarakhand.price_1kg}")
print(f"Extra per kg (>2kg): ₹{uttarakhand.price_extra_per_kg}\n")

print(f"{'Weight Range':<20} {'Formula':<35} {'Should Be':<15} {'Currently Shows':<15}")
print("-" * 80)

test_data = [
    ("≤1kg", 0.5, "price_1kg = 100", 100, 100),
    ("1.1-1.5kg", 1.25, "100 + 100/2 = 150", 150, 600),  # ❌ MISMATCH!
    ("1.51-2kg", 1.75, "100 × 2 = 200", 200, 200),
    (">2kg (5kg)", 5.0, "5 × 100 = 500", 500, None),
]

print()
for tier, weight, formula, correct_val, current_val in test_data:
    calculated = calculate_prime_express(weight, uttarakhand.price_1kg, uttarakhand.price_extra_per_kg)
    status = "✅" if current_val is None or calculated == current_val else "❌ NEEDS UPDATE"
    
    current_display = f"₹{current_val}" if current_val else "N/A"
    print(f"{tier:<20} {formula:<35} ₹{correct_val:<14.0f} {current_display:<15} {status}")

print("\n" + "=" * 80)
print("ISSUE FOUND:")
print("=" * 80)
print("\n❌ The 1.1-1.5KG tier shows ₹600.00")
print("   But with the new formula it should be: ₹150.00 (100 + 100/2)")
print("\nThis is because the old rates used a fixed ₹500 addon.")
print("New rates should follow the formula: 1kg_rate + (1kg_rate / 2)")
print("\n" + "=" * 80)
