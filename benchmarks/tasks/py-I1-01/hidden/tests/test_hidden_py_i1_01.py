import unittest

from gateways.payment_gateway import PaymentGateway
from models import Order
from services.order_service import OrderService
from validators import validate_order


class HiddenZeroAmount(unittest.TestCase):
    def test_zero_amount_rejected(self):
        with self.assertRaises(ValueError):
            validate_order(Order(order_id="O1", customer_id="C1", amount=0.0))

    def test_small_positive_accepted(self):
        self.assertTrue(validate_order(Order(order_id="O1", customer_id="C1", amount=0.01)))
