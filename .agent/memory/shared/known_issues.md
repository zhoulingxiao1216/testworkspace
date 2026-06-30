# Shared Known Issues

Use this file for stable cross-project issues. One-off execution failures belong in Agent 2 execution history.

| Date | Project | Issue | Impact | Workaround | Status |
|---|---|---|---|---|---|
| 2026-05-23 | historical_learning_import | Some historical project artifacts contain credential-like fields or raw test credentials. | Directly importing full historical docs into `.agent/memory` can leak secrets and pollute reusable learning with environment-specific facts. | Import only sanitized summaries: role, permission, fixture need, blocker type, and reusable rule. Keep raw credentials outside `.agent`. | Active |
