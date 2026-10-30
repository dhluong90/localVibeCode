# Enterprise Security Checklist (Offline SAST Guardrails)

1. **No Hardcoded Secrets:** Never hardcode API keys, passwords, or tokens in source code.
2. **Input Sanitization:** Validate all numerical limits, currency codes, and status transitions before mutating state.
3. **No Arbitrary Execution:** Never use `eval()`, `exec()`, or `subprocess` with `shell=True` in business logic.
