import unittest

from gateways.payment_gateway import PaymentGateway
from models import Order
from services.order_service import OrderService
from validators import validate_order


class HiddenCoupon(unittest.TestCase):
    def setUp(self):
        self.svc = OrderService(PaymentGateway())

    def test_standard_with_coupon(self):
        r = self.svc.checkout(Order(order_id="C1", customer_id="X", amount=100.0, coupon_code="SAVE10"))
        self.assertEqual(r["charged_amount"], 90.0)

    def test_vip_with_coupon_applies_after_tier_discount(self):
        r = self.svc.checkout(Order(order_id="C2", customer_id="X", amount=200.0, customer_tier="VIP", coupon_code="SAVE10"))
        self.assertEqual(r["charged_amount"], 170.0)

    def test_unknown_coupon_rejected(self):
        with self.assertRaises(ValueError):
            self.svc.checkout(Order(order_id="C3", customer_id="X", amount=100.0, coupon_code="BOGUS"))

    def test_no_coupon_unchanged(self):
        r = self.svc.checkout(Order(order_id="C4", customer_id="X", amount=500.0, customer_tier="ENTERPRISE"))
        self.assertEqual(r["charged_amount"], 400.0)

    def test_positional_construction_still_works(self):
        self.assertEqual(Order("C5", "X", 10.0).coupon_code, None)
