import unittest

from gateways.payment_gateway import PaymentGateway
from models import Order
from services.order_service import OrderService
from validators import validate_order


class HiddenEur(unittest.TestCase):
    def test_eur_checkout(self):
        r = OrderService(PaymentGateway()).checkout(Order(order_id="E1", customer_id="C", amount=10.0, currency="EUR"))
        self.assertEqual(r["status"], "PAID")

    def test_unknown_currency_still_rejected(self):
        with self.assertRaises(ValueError):
            validate_order(Order(order_id="E2", customer_id="C", amount=10.0, currency="JPY"))
