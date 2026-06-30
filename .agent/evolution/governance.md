# Agent Evolution Governance

This directory controls how memory becomes durable agent behavior.

## Promotion Pipeline

```text
Observation -> memory -> repeated validation -> promotion candidate -> human review -> skill/workflow/spec update
```

## Promotion Criteria

A memory item may be promoted when all conditions are true:

1. It has been observed or used successfully at least 3 times, or the user explicitly approves it.
2. It has no known counterexample in `rejected_learnings.md` or current project evidence.
3. It does not conflict with current PRD, `superpowers-base.md`, or execution safety rules.
4. It does not contain secrets or customer-private data.
5. It improves repeatability, coverage, safety, or execution speed.

## Historical Learning Import

Historical projects may be used as learning samples, but they must pass a sanitization gate before entering memory or evolution:

1. Do not copy raw credentials, tokens, cookies, customer data, screenshots containing private data, or full execution payloads into `.agent`.
2. Convert project-specific facts into reusable forms: role, permission scope, fixture need, blocker type, risk pattern, and verified rule.
3. Keep original artifacts in their project directories; memory should link to project identity and summarize reusable lessons only.
4. If a historical file contains credential-like fields, record that as a blocker or known issue, not as executable memory.
5. Promotion candidates from historical projects need evidence type and risk level, even when the source project already passed release testing.

## Risk Classes

| Class | Examples | Promotion Rule |
|---|---|---|
| Low | Selector hints, local launch commands, non-secret endpoint paths | Agent may propose; human review preferred |
| Medium | Test design heuristics, queue ordering, report conventions | Human review required |
| High | Permission changes, DB access policy, production environment behavior, financial assertions | Explicit human approval required |

## DB Permission Boundary

Agent 2 may use database access in two modes only:

1. `readonly`: default mode, limited to `SELECT / WITH / EXPLAIN`.
2. `mock_write`: controlled test data seed mode, limited to Agent 2 execution setup in non-production environments.

`mock_write` is valid only when all gates in `deps.skill_agent2_test_execution` pass: explicit enable flag, non-production environment, database-name guard or human non-production confirmation, table allowlist, SQL marker, single statement, no schema/permission operations, audit log write, and cleanup or residual-state record.

Any production DB write, schema change, permission change, stored procedure call, bulk import/export, or write outside mock table allowlists must be rejected or quarantined.

## Rejection Rules

Reject or quarantine a learning when:

1. It is based on a one-off environment incident.
2. It contradicts PRD or a human decision.
3. It contains secret material.
4. It would cause Agent 1 and Agent 2 role pollution.
5. It encourages direct DB writes outside the controlled Agent 2 `mock_write` protocol, or any unsafe production change.

## Role Isolation

Agent 1 may not convert Agent 2 execution failures into design truth without evidence.

Agent 2 may not change Agent 1 test cases or `superpowers.md`; it must write feedback to `exchange/`.

Shared memory contains stable facts only.
