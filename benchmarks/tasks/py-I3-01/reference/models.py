"""Enterprise Domain Models for Order & Payment Processing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Order:
    """Represents a customer purchase order."""

    order_id: str
    customer_id: str
    amount: float
    currency: str = "USD"
    status: str = "PENDING"
    customer_tier: str = "STANDARD"
    coupon_code: Optional[str] = None
