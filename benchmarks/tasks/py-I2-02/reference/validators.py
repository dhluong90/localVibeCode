"""Domain Validation Rules for Enterprise Orders."""

from __future__ import annotations

from models import Order

SUPPORTED_CURRENCIES = {"USD", "EUR", "VND", "SGD"}
SUPPORTED_TIERS = {"STANDARD", "VIP", "ENTERPRISE"}


def validate_customer_tier(tier: str) -> bool:
    """Validates that the customer tier is supported."""
    if tier not in SUPPORTED_TIERS:
        raise ValueError(f"Unsupported customer tier: {tier}")
    return True


def validate_order(order: Order) -> bool:
    """Validates order amount and currency compliance."""
    if not order.order_id or not order.customer_id:
        raise ValueError("order_id and customer_id are required.")
    if order.amount <= 0:
        raise ValueError("Order amount must be strictly positive.")
    if order.currency not in SUPPORTED_CURRENCIES:
        raise ValueError(f"Unsupported currency: {order.currency}")
    validate_customer_tier(order.customer_tier)
    return True
