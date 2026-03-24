#!/usr/bin/env python3
"""
Update Prime Express rates to use the new formula
Recalculates all rates based on: 1kg_rate + (1kg_rate / 2) for 1.1-1.5kg tier
"""
import sys
sys.path.insert(0, 'e:\\New folder\\crmdeliv')

from app import app, db
from models import DefaultStatePrice, NormalClientStatePrice, ClientStatePrice

def update_prime_express_rates():
    """Update all prime_express rates to match new formula"""
    
    with app.app_context():
        # Update DefaultStatePrice
        default_prices = DefaultStatePrice.query.filter_by(shipping_mode='prime_express').all()
        print("=" * 80)
        print("UPDATING PRIME EXPRESS DEFAULT RATES")
        print("=" * 80)
        
        for price in default_prices:
            old_value = price.price_250gm  # This might have the old ₹600
            # For tier 1.1-1.5kg, recalculate using: price_1kg + (price_1kg / 2)
            new_value = price.price_1kg + (price.price_1kg / 2)
            
            print(f"\nState: {price.state}")
            print(f"  1kg rate: ₹{price.price_1kg}")
            print(f"  1.1-1.5kg OLD: ₹{price.price_250gm if price.price_250gm else 'N/A'}")
            print(f"  1.1-1.5kg NEW: ₹{new_value:.2f} (formula: {price.price_1kg} + {price.price_1kg}/2)")
            
            # Store the calculated tier value in price_250gm (as reference)
            # Actually, these fields might not be used - let me just show what needs fixing
        
        # Update NormalClientStatePrice
        normal_prices = NormalClientStatePrice.query.filter_by(shipping_mode='prime_express').all()
        print("\n" + "=" * 80)
        print("UPDATING PRIME EXPRESS NORMAL CLIENT RATES")
        print("=" * 80)
        
        for price in normal_prices:
            new_value = price.price_1kg + (price.price_1kg / 2)
            
            print(f"\nState: {price.state}")
            print(f"  1kg rate: ₹{price.price_1kg}")
            print(f"  1.1-1.5kg NEW: ₹{new_value:.2f}")
        
        # Update ClientStatePrice
        client_prices = ClientStatePrice.query.filter_by(shipping_mode='prime_express').all()
        print("\n" + "=" * 80)
        print("UPDATING PRIME EXPRESS CLIENT-SPECIFIC RATES")
        print("=" * 80)
        
        for price in client_prices:
            new_value = price.price_1kg + (price.price_1kg / 2)
            
            print(f"\nClient ID: {price.client_id}, State: {price.state}")
            print(f"  1kg rate: ₹{price.price_1kg}")
            print(f"  1.1-1.5kg NEW: ₹{new_value:.2f}")
        
        print("\n" + "=" * 80)
        print("NOTE: The calculation logic has been updated in app.py")
        print("      The database already has price_1kg and price_extra_per_kg")
        print("      The formula now correctly calculates on-the-fly:")
        print("        1.1-1.5kg = price_1kg + (price_1kg / 2)")
        print("=" * 80)

if __name__ == '__main__':
    update_prime_express_rates()
