import unittest

from gateways.payment_gateway import PaymentGateway
from models import Order
from services.order_service import OrderService
from validators import validate_order

from services.fx_rates import to_usd


class HiddenFx(unittest.TestCase):
    def test_to_usd(self):
        self.assertEqual(to_usd(100.0, "EUR"), 110.0)
        self.assertEqual(to_usd(1_000_000.0, "VND"), 40.0)
        self.assertEqual(to_usd(10.0, "USD"), 10.0)

    def test_unknown_currency(self):
        with self.assertRaises(ValueError):
            to_usd(10.0, "JPY")

    def test_checkout_reports_usd(self):
        svc = OrderService(PaymentGateway())
        r = svc.checkout(Order(order_id="F1", customer_id="X", amount=100.0, currency="EUR"))
        self.assertEqual(r["charged_amount"], 100.0)
        self.assertEqual(r["charged_amount_usd"], 110.0)
        r = svc.checkout(Order(order_id="F2", customer_id="X", amount=200.0, currency="SGD", customer_tier="VIP"))
        self.assertEqual(r["charged_amount"], 180.0)
        self.assertEqual(r["charged_amount_usd"], 135.0)
