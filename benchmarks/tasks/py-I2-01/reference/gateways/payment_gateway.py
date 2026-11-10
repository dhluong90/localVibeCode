"""Internal Enterprise Payment Gateway Adapter."""

from __future__ import annotations

from models import Order


class PaymentGateway:
    """Handles charging and refunding customer orders against the enterprise ledger."""

    def __init__(self) -> None:
        self.ledger: dict[str, float] = {}

    def charge(self, order: Order, final_amount: float) -> str:
        """Charges the specified final_amount for the order and records it in the ledger."""
        rounded = round(final_amount, 2)
        if rounded <= 0:
            raise ValueError("Charge amount must be positive.")
        self.ledger[order.order_id] = rounded
        return f"TX-{order.order_id}"

    def refund(self, order_id: str) -> float:
        """Refunds a charged order and removes it from the ledger."""
        if order_id not in self.ledger:
            raise ValueError(f"Order {order_id} was never charged.")
        return self.ledger.pop(order_id)
