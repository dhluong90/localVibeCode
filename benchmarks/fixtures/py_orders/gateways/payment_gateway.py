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
