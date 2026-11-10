"""Domain Validation Rules for Enterprise Orders."""

from __future__ import annotations

from models import Order

SUPPORTED_CURRENCIES = {"USD", "EUR", "VND", "SGD"}
SUPPORTED_COUPONS = {"SAVE10"}


def validate_order(order: Order) -> bool:
    """Validates order amount and currency compliance."""
    if not order.order_id or not order.customer_id:
        raise ValueError("order_id and customer_id are required.")
    if order.amount <= 0:
        raise ValueError("Order amount must be strictly positive.")
    if order.currency not in SUPPORTED_CURRENCIES:
        raise ValueError(f"Unsupported currency: {order.currency}")
    if order.coupon_code is not None and order.coupon_code not in SUPPORTED_COUPONS:
        raise ValueError(f"Unsupported coupon: {order.coupon_code}")
    return True
