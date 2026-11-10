import unittest

from models import Order
from validators import validate_order


class TestValidateOrder(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(validate_order(Order(order_id="O", customer_id="C", amount=1.0)))

    def test_missing_order_id(self):
        with self.assertRaises(ValueError):
            validate_order(Order(order_id="", customer_id="C", amount=1.0))

    def test_missing_customer_id(self):
        with self.assertRaises(ValueError):
            validate_order(Order(order_id="O", customer_id="", amount=1.0))

    def test_zero_amount(self):
        with self.assertRaises(ValueError):
            validate_order(Order(order_id="O", customer_id="C", amount=0.0))

    def test_negative_amount(self):
        with self.assertRaises(ValueError):
            validate_order(Order(order_id="O", customer_id="C", amount=-1.0))

    def test_unsupported_currency(self):
        with self.assertRaises(ValueError):
            validate_order(Order(order_id="O", customer_id="C", amount=1.0, currency="JPY"))
