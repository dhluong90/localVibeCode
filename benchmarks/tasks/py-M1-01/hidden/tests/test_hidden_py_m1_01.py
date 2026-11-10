import unittest

from gateways.payment_gateway import PaymentGateway
from models import Order
from services.order_service import OrderService
from validators import validate_order


class HiddenDefaultTier(unittest.TestCase):
    def test_default_tier_is_standard(self):
        self.assertEqual(Order(order_id="D", customer_id="C", amount=1.0).customer_tier, "STANDARD")
