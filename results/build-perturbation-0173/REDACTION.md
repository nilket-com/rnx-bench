# Redaction of the E2 environment

Condition E2 ran with the controller's full inherited environment, captured once. In the retained `run1/diag.json` (key `E2`) and `run1/B-env-E0-vs-E2.jsonl` (each E2 sample's `env`), every value outside an allowlist is replaced with `<redacted: N bytes>`. Keys and value byte lengths are kept, and no measured count changed. The allowlist is the same as `results/borrow-context-type-0172/REDACTION.md`. The producer `diag.py` is unchanged.
