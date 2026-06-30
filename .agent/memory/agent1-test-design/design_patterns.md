# Agent 1 Design Patterns

Reusable test-design patterns validated in this workspace.

## Current Baseline

- Use `00_全局测试规约库/superpowers-base.md` as the base rule layer.
- Generate project `superpowers.md` before test outline and test cases.
- Keep test points and test cases strictly separated.
- Do not promote examples from global specs into project content unless the project PRD supports them.

## Candidate Patterns

Add new patterns only after they are used successfully in a real project and do not conflict with the current PRD.

| Date | Project | Pattern | Reuse Condition | Status |
|---|---|---|---|---|
| 2026-05-22 | 订单详情页优化 | For PRD items marked 暂缓/开发评估, keep test cases but expose them as conditional execution groups in `执行交接清单.yaml`. | Incremental or uncertain-scope requirements | Candidate |
| 2026-05-22 | 消息提醒功能以及重要待办 | When Agent2 feedback is mostly execution prerequisites, keep design artifacts stable and move unresolved items into `blocking_risks` instead of inventing expected data or environment details. | Cross-agent review with missing environment/data/SMS/Mock inputs | Candidate |
| 2026-05-23 | 国内包裹签收处理功能 | For status/statistics pages, order the design by dependency chain: source data -> state judgment -> time rule -> statistics -> list rendering. | Warehouse, package, workflow, status board, operational statistics | Candidate |
| 2026-05-23 | 黑白名单及采购账号 | For auth/account features, design a three-way consistency suite: admin config, DB/cache/API truth, and frontend or middleware behavior must all agree. | Permission, blacklist/whitelist, token, procurement account, access control | Candidate |
| 2026-05-23 | 全球站批量导入功能 | For import features, design around template routing, row-level validation, external service degradation, partial success semantics, and final write atomicity. | Excel/CSV import, batch upload, 1688/SKU validation, cart/order write | Candidate |
| 2026-05-23 | 表单下载 | For export/template features, build a template-field matrix before writing cases; separate fixed structure assertions from dynamic data tolerance. | Excel/PDF/label/invoice export, field mapping, multilingual templates | Candidate |
| 2026-05-25 | message_reminder_important_todo | Run the target platform parser after generating test cases; `#### TC-` anchor count and parsed record count must match handoff `total_cases`. | Markdown test case deliverables intended for platform import | Candidate |
