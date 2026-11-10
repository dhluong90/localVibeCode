"""Unit tests for the Enterprise Order & Payment microservice."""

from __future__ import annotations

import unittest

from gateways.payment_gateway import PaymentGateway
from models import Order
from services.order_service import OrderService


class TestEnterpriseOrderService(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = PaymentGateway()
        self.service = OrderService(self.gateway)

    def test_standard_order_checkout(self) -> None:
        order = Order(order_id="ORD-101", customer_id="CUST-1", amount=100.0, currency="USD")
        result = self.service.checkout(order)
        self.assertEqual(result["charged_amount"], 100.0)
        self.assertEqual(result["status"], "PAID")

    def test_vip_order_discount(self) -> None:
        order = Order(
            order_id="ORD-102",
            customer_id="CUST-2",
            amount=200.0,
            currency="USD",
            customer_tier="VIP",
        )
        result = self.service.checkout(order)
        self.assertEqual(result["charged_amount"], 180.0)
        self.assertEqual(result["status"], "PAID")

    def test_invalid_amount_raises(self) -> None:
        order = Order(order_id="ORD-103", customer_id="CUST-3", amount=-50.0, currency="USD")
        with self.assertRaises(ValueError):
            self.service.checkout(order)

    def test_enterprise_order_discount(self) -> None:
        order = Order(
            order_id="ORD-104",
            customer_id="CUST-4",
            amount=500.0,
            currency="USD",
            customer_tier="ENTERPRISE",
        )
        result = self.service.checkout(order)
        self.assertEqual(result["charged_amount"], 400.0)
        self.assertEqual(result["status"], "PAID")


if __name__ == "__main__":
    unittest.main()
