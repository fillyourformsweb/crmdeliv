#!/usr/bin/env python3
"""
Test Insurance Fee Calculation
"""

print("=" * 60)
print("INSURANCE FEE CALCULATION TEST")
print("=" * 60)

# Test cases
test_cases = [
    (30, 1.0, "30 × 1%"),
    (100, 1.0, "100 × 1%"),
    (500, 1.0, "500 × 1%"),
    (1000, 1.0, "1000 × 1%"),
    (30, 2.0, "30 × 2%"),
    (100, 2.0, "100 × 2%"),
]

print(f"\n{'Insured Value':<15} {'Insurance %':<12} {'Calculation':<20} {'Insurance Fee':<15}")
print("-" * 60)

for insured, percentage, description in test_cases:
    insurance_fee = (insured * percentage) / 100
    print(f"₹{insured:<14.0f} {percentage}%       {description:<20} ₹{insurance_fee:<14.2f}")

print("\n" + "=" * 60)
print("NOTE: With default 1% insurance:")
print("  - Insured ₹30 = ₹0.30 fee (very small!)")
print("  - Insured ₹100 = ₹1.00 fee")
print("  - Insured ₹1000 = ₹10.00 fee")
print("\nIf fee shows ₹0, it might be due to rounding or display")
print("=" * 60)
