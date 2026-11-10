"""Fixed FX rates used to report charged amounts in USD."""
from __future__ import annotations

RATES_TO_USD = {"USD": 1.0, "EUR": 1.10, "SGD": 0.75, "VND": 0.00004}


def to_usd(amount: float, currency: str) -> float:
    """Converts an amount in the given currency to USD, rounded to 2 decimals."""
    if currency not in RATES_TO_USD:
        raise ValueError(f"Unknown currency: {currency}")
    return round(amount * RATES_TO_USD[currency], 2)
