# Agent Run State

`.agent/runs/` stores the state and evidence for one multi-agent task run.

Use this layer when the user gives a compact instruction such as:

```text
agent1和agent2开始工作，新项目【项目名】，需求路径【路径】。
```

If the user does not explicitly allow or forbid real execution, `mode.real_execution` must be `pending_confirmation`.

## Directory Shape

Each run should use one stable directory:

```text
.agent/runs/{run_id}/
  run.yaml
  agent1_output.yaml
  agent2_review.yaml
  remediation.yaml
  final_summary.md
```

Recommended `run_id` format:

```text
YYYY-MM-DD_{project_slug}
```

## State Machine

| State | Owner | Meaning | Next |
|---|---|---|---|
| `CREATED` | Orchestrator | Run record created | `DESIGN_IN_PROGRESS` |
| `DESIGN_IN_PROGRESS` | Agent 1 | Agent 1 is reading requirements and producing design deliverables | `DESIGN_READY` |
| `DESIGN_READY` | Agent 1 | Design deliverables and handoff manifest are ready | `EXEC_REVIEW_REQUESTED` |
| `EXEC_REVIEW_REQUESTED` | Agent 2 | Agent 2 should review executability before E1 | `EXEC_REVIEW_FEEDBACK` or `EXECUTION_READY` |
| `ORCHESTRATOR_TRIAGE` | Orchestrator | Agent 2 feedback is being classified before assignment | `EXEC_REVIEW_FEEDBACK`, `EXTERNAL_BLOCKED`, `EXECUTION_READY`, or `REFLECTION_READY` |
| `EXEC_REVIEW_FEEDBACK` | Agent 2 | Agent 2 found issues that Agent 1 must remediate | `DESIGN_REMEDIATION_IN_PROGRESS` |
| `EXTERNAL_BLOCKED` | Orchestrator | Execution is blocked by environment, account, data, SMS, mock authorization, or product confirmation | `REFLECTION_READY` or `EXECUTION_READY` after external inputs are resolved |
| `DESIGN_REMEDIATION_IN_PROGRESS` | Agent 1 | Agent 1 is resolving feedback items | `DESIGN_REMEDIATED` |
| `DESIGN_REMEDIATED` | Agent 1 | Feedback items have remediation records | `EXEC_REVIEW_REQUESTED` |
| `EXECUTION_READY` | Agent 2 | The test set is executable, but real execution has not necessarily started | `EXECUTION_IN_PROGRESS` or `REFLECTION_READY` |
| `EXECUTION_CONFIRMATION_REQUIRED` | Orchestrator | Agent 2 has asked whether to execute real tests and is waiting for user Y/N | `EXECUTION_IN_PROGRESS`, `EXTERNAL_BLOCKED`, or `REFLECTION_READY` |
| `EXECUTION_IN_PROGRESS` | Agent 2 | Agent 2 is running tests | `EXECUTION_DONE` |
| `EXECUTION_DONE` | Agent 2 | Execution report and defect records are complete | `REFLECTION_READY` |
| `REFLECTION_READY` | Orchestrator | Run can be reflected on | `REFLECTION_DONE` |
| `REFLECTION_DONE` | Orchestrator | Reflection has been written | `EVOLUTION_CANDIDATE_CREATED` or `CLOSED` |
| `EVOLUTION_CANDIDATE_CREATED` | Orchestrator | Stable lessons proposed for promotion | `CLOSED` |
| `CLOSED` | Orchestrator | Run complete | None |

## run.yaml Template

```yaml
run_id: "2026-05-22_order_detail_optimization"
project:
  name: "订单详情页优化"
  slug: "order_detail_optimization"
  root: "订单详情页优化"
  requirement_path: "订单详情页优化"
mode:
  design: true
  executability_review: true
  real_execution: "pending_confirmation"
state: "CREATED"
current_owner: "orchestrator"
next_agent: "agent1_test_design"
execution_confirmation:
  required: true
  asked_by: "agent2_test_execution"
  question: "是否执行真实测试？请输入 Y/N。"
  user_answer: null
artifacts:
  agent1:
    test_docs_dir: null
    handoff_manifest: null
    test_cases: null
  agent2:
    review_report: null
    feedback_file: null
    execution_report: null
gates:
  design_ready: false
  executability_review_passed: false
  execution_allowed_by_user: null
reflection:
  required: true
  path: null
evolution:
  promotion_candidate_required: false
  path: ".agent/evolution/promotion_candidates.md"
```

## Operating Rules

1. The orchestrator is the only role that changes `state`.
2. Agent 1 owns design deliverables; Agent 2 must not directly edit them.
3. Agent 2 sends feedback through exchange files and run artifacts.
4. The orchestrator must classify Agent 2 feedback before Agent 1 receives remediation work.
5. Only feedback classified as `assign_to_agent1` becomes Agent 1 work.
6. Environment, account, permission, data, SMS channel, API, and DB mock authorization gaps remain external blockers or human confirmations.
7. Agent 2 must ask `是否执行真实测试？请输入 Y/N。` after executability review if the user has not already decided.
8. Agent 2 must not execute tests while `mode.real_execution` is `pending_confirmation`.
9. A `Y` answer only permits execution after external blockers and human confirmations are resolved.
10. Reflection happens after the user answers `N`, after execution blockers stop the run, or after `EXECUTION_DONE` when real execution is requested.
11. Evolution is optional and only records promotion candidates, not direct workflow rewrites.
