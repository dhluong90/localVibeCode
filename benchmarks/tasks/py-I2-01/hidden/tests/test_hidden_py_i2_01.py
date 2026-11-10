import unittest

from gateways.payment_gateway import PaymentGateway
from models import Order
from services.order_service import OrderService
from validators import validate_order


class HiddenRefund(unittest.TestCase):
    def test_refund_returns_amount_and_removes_entry(self):
        gw = PaymentGateway()
        gw.charge(Order(order_id="R-1", customer_id="C", amount=50.0), 45.0)
        self.assertEqual(gw.refund("R-1"), 45.0)
        self.assertNotIn("R-1", gw.ledger)

    def test_refund_unknown_raises(self):
        with self.assertRaises(ValueError):
            PaymentGateway().refund("NOPE")

    def test_double_refund_raises(self):
        gw = PaymentGateway()
        gw.charge(Order(order_id="R-2", customer_id="C", amount=5.0), 5.0)
        gw.refund("R-2")
        with self.assertRaises(ValueError):
            gw.refund("R-2")
