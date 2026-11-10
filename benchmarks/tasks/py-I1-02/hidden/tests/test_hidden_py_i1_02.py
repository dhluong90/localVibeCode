import unittest

from gateways.payment_gateway import PaymentGateway
from models import Order
from services.order_service import OrderService
from validators import validate_order


class HiddenLedgerKey(unittest.TestCase):
    def test_two_orders_same_customer(self):
        gw = PaymentGateway()
        svc = OrderService(gw)
        svc.checkout(Order(order_id="A-1", customer_id="C-9", amount=10.0))
        svc.checkout(Order(order_id="A-2", customer_id="C-9", amount=20.0))
        self.assertEqual(gw.ledger, {"A-1": 10.0, "A-2": 20.0})
