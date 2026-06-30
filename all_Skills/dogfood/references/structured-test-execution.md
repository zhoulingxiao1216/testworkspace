# Structured Test Execution Notes

Use this when the user provides a formal test-case set, a handoff checklist, or a project-specific testing skill/spec instead of asking for open-ended exploratory QA.

## Key workflow

1. Load the project-specific execution instructions first if the user points to them, even if they are outside the Hermes skill library (for example `.agent/skills/test-execution/SKILL.md`). Treat them as the governing spec for the run.
2. Load report/defect format standards before generating deliverables. If standards live in the workspace, read them directly.
3. Prefer a structured manifest (`执行交接清单.yaml`, queue manifest, etc.) over parsing Markdown. If no manifest exists, parse Markdown test cases by stable anchors such as `#### TC-...`.
4. Run an environment gate before business test execution:
   - target URL reachability;
   - login/session verification;
   - required test data profile;
   - evidence screenshot or equivalent proof;
   - explicit gate decision.
5. If any mandatory gate fails, halt formal execution and create a blocking execution report. Do not mark business cases Pass/Fail from assumptions.
6. If cases are parsed successfully but not executable, record queue statistics and mark the suite blocked by the failed gate, not failed by product behavior.
7. When browser tooling or screenshots are unavailable, state that as an execution blocker and avoid fabricating screenshots, UI observations, or defect records.
8. For security-sensitive cases (API bypass, token reuse, privilege escalation, direct checkout calls), require clear authorization scope before performing live requests. It is still OK to inventory and queue those cases.

## Deliverable pattern for blocked runs

- Create the required output directory and report file if the spec asks for one.
- Include: source file, parsed case count, priority/module breakdown, E1 checks with actual evidence, blocking reason, and precise recovery conditions.
- Do not create a defect list for a pure pre-check blocker unless the environment itself is the product under test.

## Pitfalls

- Do not execute destructive or state-changing test cases before the queue is confirmed when the governing spec requires human confirmation.
- Do not confuse environment/tooling blockers with application defects.
- Do not report all cases as failed when none were actually run; use Blocked.
- In CLI sessions, reference created files by plain absolute path; do not emit `MEDIA:/path` tags unless the platform specifically renders them.
