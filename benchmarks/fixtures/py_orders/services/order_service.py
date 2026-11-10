"""Enterprise Order Service orchestrating validation, pricing, and payment."""
from __future__ import annotations

from gateways.payment_gateway import PaymentGateway
from models import Order
from validators import validate_order

class OrderService:
    """Core business service for processing enterprise customer orders."""
    def __init__(self, gateway: PaymentGateway) -> None:
        self.gateway = gateway

    def calculate_payable_amount(self, order: Order) -> float:
        """Calculates the final payable amount for an order based on customer_tier."""
        validate_order(order)
        if order.customer_tier == 'VIP':
            return round(order.amount * 0.90, 2)
        elif order.customer_tier == 'ENTERPRISE':
            return round(order.amount * 0.80, 2)
        else:
            return round(order.amount, 2)

    def checkout(self, order: Order) -> dict[str, str | float]:
        """Validates the order, calculates payable amount, and executes payment."""
        payable = self.calculate_payable_amount(order)
        tx_id = self.gateway.charge(order, payable)
        order.status = 'PAID'
        return {
            'order_id': order.order_id,
            'tx_id': tx_id,
            'charged_amount': payable,
            'status': order.status,
        }
