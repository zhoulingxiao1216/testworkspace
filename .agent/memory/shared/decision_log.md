# Shared Decision Log

This file records stable, human-confirmed decisions that both Agent 1 and Agent 2 may rely on.

| Date | Scope | Decision | Source | Status |
|---|---|---|---|---|
| 2026-05-22 | Memory architecture | Use shared facts, role-specific memory, and exchange memory instead of a single mixed memory pool. | User request and agent design discussion | Active |
| 2026-05-22 | Secret handling | Do not store passwords, tokens, cookies, private keys, or raw customer data in `.agent/memory/`. | Memory v1 governance | Active |
