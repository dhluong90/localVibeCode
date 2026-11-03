# Enterprise Architecture & Coding Guardrails (AISDLC Factory Standard)

1. **Clean Architecture & Separation of Concerns:**
   - Domain models (`models.py`) MUST NOT import from services or external gateways.
   - Business logic resides in `services/`, while validation rules reside in `validators.py`.
2. **Type Safety & Documentation:**
   - Every public function and method MUST include explicit Python type annotations (inputs and return type).
   - Every public class and function MUST have a concise docstring explaining its contract.
3. **Backward Compatibility (Blast-Radius Protection):**
   - Do NOT remove or rename existing public function parameters without providing default values if 1-hop inbound callers depend on them.
4. **Error Handling & Auditability:**
   - Raise explicit domain exceptions (`ValueError`, custom domain errors) with clear messages rather than returning silent `None` or swallowing exceptions.
   - Financial calculations must round to 2 decimal places (`round(val, 2)`) and validate non-negative amounts.
