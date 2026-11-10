import unittest

from gateways.payment_gateway import PaymentGateway
from models import Order
from services.order_service import OrderService
from validators import validate_order

from validators import validate_customer_tier


class HiddenTierValidation(unittest.TestCase):
    def test_supported_tiers(self):
        for tier in ("STANDARD", "VIP", "ENTERPRISE"):
            self.assertTrue(validate_customer_tier(tier))

    def test_unsupported_tier_raises(self):
        with self.assertRaises(ValueError):
            validate_customer_tier("GOLD")

    def test_validate_order_rejects_unknown_tier(self):
        with self.assertRaises(ValueError):
            validate_order(Order(order_id="O", customer_id="C", amount=10.0, customer_tier="GOLD"))

    def test_checkout_rejects_unknown_tier(self):
        with self.assertRaises(ValueError):
            OrderService(PaymentGateway()).checkout(
                Order(order_id="O", customer_id="C", amount=10.0, customer_tier="PLATINUM"))
