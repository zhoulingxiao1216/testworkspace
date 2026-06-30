# Agent Memory v1

This directory is the controlled long-term memory layer for the workspace agents.

## Layer Model

| Layer | Path | Purpose | Writers |
|---|---|---|---|
| Shared facts | `shared/` | Stable facts confirmed across Agent 1 and Agent 2 | Human-confirmed updates, cautious agent updates |
| Agent 1 memory | `agent1-test-design/` | Requirement analysis, test design, coverage, and rule-design lessons | Agent 1 |
| Agent 2 memory | `agent2-test-execution/` | Execution, environment, selector, API, and blocker lessons | Agent 2 |
| Exchange | `exchange/` | Cross-agent feedback, remediation, and coverage-gap handoff | Agent 1 and Agent 2 |

## Runtime State Is Not Memory

`.agent/runs/` stores per-task run state, review artifacts, and orchestration metadata. It is intentionally separate from long-term memory.

- Use `runs/` for one project's current state, pending agent, review verdicts, and final summary.
- Use `memory/` only for reusable facts or lessons that should survive beyond the current run.
- Use `reflections/` after a run closes to summarize what happened.
- Use `evolution/` only for promotion candidates that may later become skill or workflow rules.

## Exchange Routing Rule

Agent 2 feedback is a proposal, not a direct command to Agent 1.

Required routing:

1. Agent 2 writes feedback with `F-xxx` ids.
2. The orchestrator classifies each item using `exchange/orchestrator_decision_schema.yaml`.
3. Only items classified as `assign_to_agent1` become Agent 1 remediation work.
4. Missing environment, accounts, permissions, test data, SMS channel, API, or DB mock authorization must stay as `external_blocker` or `human_confirmation`.
5. Agent 1 must not invent external facts to close Agent 2 blockers.

## Access Rules

Agent 1 reads:

- `shared/`
- `agent1-test-design/`
- `exchange/`

Agent 1 writes:

- `agent1-test-design/`
- `exchange/`
- `shared/` only when the fact is stable or human-confirmed

Agent 2 reads:

- `shared/`
- `agent2-test-execution/`
- `exchange/`

Agent 2 writes:

- `agent2-test-execution/`
- `exchange/`
- `shared/` only when the fact is stable or human-confirmed

## Safety Rules

1. Do not store passwords, tokens, cookies, private keys, or raw customer data.
2. Store credential references only, such as `测试环境使用账号.md`.
3. New observations enter memory first. They do not directly modify skills or workflows.
4. A memory item may be proposed for skill/workflow promotion only after repeated validation and no known counterexample.
5. If a memory conflicts with current PRD, current PRD wins and the memory must be marked stale.

## Task Lifecycle

Before a task:

1. Identify the project and role.
2. Load relevant shared memory.
3. Load the role-specific memory.
4. Load exchange items if the task involves cross-agent handoff.

During a task:

1. Record reusable facts as candidates.
2. Keep speculative observations out of `shared/`.
3. Mark one-off environment failures as local execution history, not global truth.

After a task:

1. Append concise execution/design notes to the relevant memory file.
2. Add cross-agent findings to `exchange/`.
3. Add promotion candidates to `.agent/evolution/promotion_candidates.md` only when they are stable enough to review.

## 图示（Reflections → Memory → Evolution 流程）

矢量图（可无损放大）：

![Reflections→Memory→Evolution](.agent/assets/reflections_memory_evolution.svg)

高清位图备份：

[reflections_memory_evolution@2x.png](.agent/assets/reflections_memory_evolution@2x.png)

简化图（便于快速理解）：

![简化：Reflections→Memory→Evolution](.agent/assets/simple_reflections.svg)

简化图位图备份：

[simple_reflections@2x.png](.agent/assets/simple_reflections@2x.png)
