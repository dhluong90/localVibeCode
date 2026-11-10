import unittest

from gateways.payment_gateway import PaymentGateway
from models import Order


class TestPaymentGateway(unittest.TestCase):
    def setUp(self):
        self.gw = PaymentGateway()
        self.order = Order(order_id="P1", customer_id="C", amount=10.0)

    def test_rounding(self):
        self.gw.charge(self.order, 10.006)
        self.assertEqual(self.gw.ledger["P1"], 10.01)

    def test_zero_rejected(self):
        with self.assertRaises(ValueError):
            self.gw.charge(self.order, 0.0)

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            self.gw.charge(self.order, -5.0)

    def test_tx_id_and_ledger(self):
        self.assertEqual(self.gw.charge(self.order, 7.5), "TX-P1")
        self.assertEqual(self.gw.ledger, {"P1": 7.5})
