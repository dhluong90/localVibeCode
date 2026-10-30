# GRAPH_REPORT.md — Deterministic AST Knowledge Graph

## 1. Architectural God Nodes (Core Centrality Ranking)
- **`models.py`** (Score: `8`) — Enterprise Domain Models for Order & Payment Processing. | Inbound Callers: `['gateways/payment_gateway.py', 'services/order_service.py', 'tests/test_orders.py', 'validators.py']` | Outbound Imports: `[]`
- **`gateways/payment_gateway.py`** (Score: `5`) — Internal Enterprise Payment Gateway Adapter. | Inbound Callers: `['services/order_service.py', 'tests/test_orders.py']` | Outbound Imports: `['models.py']`
- **`services/order_service.py`** (Score: `5`) — Enterprise Order Service orchestrating validation, pricing, and payment. | Inbound Callers: `['tests/test_orders.py']` | Outbound Imports: `['gateways/payment_gateway.py', 'models.py', 'validators.py']`
- **`tests/test_orders.py`** (Score: `3`) — Unit tests for the Enterprise Order & Payment microservice. | Inbound Callers: `[]` | Outbound Imports: `['gateways/payment_gateway.py', 'models.py', 'services/order_service.py']`
- **`validators.py`** (Score: `3`) — Domain Validation Rules for Enterprise Orders. | Inbound Callers: `['services/order_service.py']` | Outbound Imports: `['models.py']`

## 2. Repository Structural Skeleton (Signatures Only)

### File: `gateways/payment_gateway.py`
  - `class PaymentGateway:`  # Handles charging and refunding customer orders against the enterprise ledger.
    - `def __init__(self) -> None:`
    - `def charge(self, order: Order, final_amount: float) -> str:`  # Charges the specified final_amount for the order and records it in the ledger.

### File: `models.py`
  - `class Order:
    order_id: str
    customer_id: str
    amount: float
    currency: str = 'USD'
    status: str = 'PENDING'
    customer_tier: str = 'STANDARD'`  # Represents a customer purchase order.

### File: `services/order_service.py`
  - `class OrderService:`  # Core business service for processing enterprise customer orders.
    - `def __init__(self, gateway: PaymentGateway) -> None:`
    - `def calculate_payable_amount(self, order: Order) -> float:`  # Calculates the final payable amount for an order based on customer_tier.
    - `def checkout(self, order: Order) -> dict[str, str | float]:`  # Validates the order, calculates payable amount, and executes payment.

### File: `tests/test_orders.py`
  - `class TestEnterpriseOrderService(unittest.TestCase):`
    - `def setUp(self) -> None:`
    - `def test_standard_order_checkout(self) -> None:`
    - `def test_vip_order_discount(self) -> None:`
    - `def test_invalid_amount_raises(self) -> None:`
    - `def test_enterprise_order_discount(self) -> None:`

### File: `validators.py`
  - `def validate_order(order: Order) -> bool:`  # Validates order amount and currency compliance.
