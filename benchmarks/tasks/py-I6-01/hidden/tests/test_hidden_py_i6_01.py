import unittest

from gateways.payment_gateway import PaymentGateway
from models import Order
from services.order_service import OrderService
from validators import validate_order

from gateways.payment_gateway import ChargeResult


class HiddenChargeResult(unittest.TestCase):
    def test_charge_returns_result(self):
        r = PaymentGateway().charge(Order(order_id="X1", customer_id="C", amount=20.0), 12.5)
        self.assertIsInstance(r, ChargeResult)
        self.assertEqual(r.tx_id, "TX-X1")
        self.assertEqual(r.amount, 12.5)

    def test_checkout_dict_unchanged(self):
        r = OrderService(PaymentGateway()).checkout(Order(order_id="X2", customer_id="C", amount=100.0))
        self.assertEqual(r, {"order_id": "X2", "tx_id": "TX-X2", "charged_amount": 100.0, "status": "PAID"})
