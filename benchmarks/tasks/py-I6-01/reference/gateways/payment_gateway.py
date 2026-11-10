"""Internal Enterprise Payment Gateway Adapter."""

from __future__ import annotations

from dataclasses import dataclass

from models import Order


@dataclass
class ChargeResult:
    """Result of a successful charge."""

    tx_id: str
    amount: float


class PaymentGateway:
    """Handles charging and refunding customer orders against the enterprise ledger."""

    def __init__(self) -> None:
        self.ledger: dict[str, float] = {}

    def charge(self, order: Order, final_amount: float) -> ChargeResult:
        """Charges the specified final_amount for the order and records it in the ledger."""
        rounded = round(final_amount, 2)
        if rounded <= 0:
            raise ValueError("Charge amount must be positive.")
        self.ledger[order.order_id] = rounded
        return ChargeResult(tx_id=f"TX-{order.order_id}", amount=rounded)
