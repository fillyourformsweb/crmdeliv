import unittest
from app import app, calculate_order_amount
from models import db, Client, DefaultStatePrice, SystemSettings
from tests.test_models import BaseTestCase

class PricingTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        with app.app_context():
            # Add default price for a state
            dp = DefaultStatePrice(
                state='maharashtra',
                shipping_mode='standard',
                price_100gm=50,
                price_250gm=75,
                price_500gm=100,
                price_1kg=150,
                price_extra_per_kg=20
            )
            db.session.add(dp)
            
            # Add insurance setting
            s = SystemSettings(key='insurance_percentage', value='1.0')
            db.session.add(s)
            db.session.commit()

    def test_standard_pricing_calc(self):
        with app.app_context():
            # Test 500g (0.5kg)
            res = calculate_order_amount(0.5, state='Maharashtra', insured_amount=100)
            # res: (base, weight_charge, additional, discount, total, price_list_type, insurance_charge)
            base, weight_charge, additional, discount, total, price_type, insurance = res
            
            self.assertEqual(base, 100) # price_500gm
            self.assertEqual(insurance, 1.0) # 1% of 100
            self.assertEqual(total, 101.0)
            self.assertEqual(price_type, 'state')

    def test_prime_express_pricing(self):
         with app.app_context():
            # Add prime express rate
            dp = DefaultStatePrice(
                state='delhi',
                shipping_mode='prime_express',
                price_1kg=200,
                price_extra_per_kg=50
            )
            db.session.add(dp)
            db.session.commit()

            # Test 1.5kg Prime Express
            # Formula for 1.1-1.5kg: price_1kg + (price_1kg / 2)
            res = calculate_order_amount(1.5, state='Delhi', shipping_mode='prime_express')
            total = res[4]
            self.assertEqual(total, 300.0) # 200 + 100

if __name__ == '__main__':
    unittest.main()
