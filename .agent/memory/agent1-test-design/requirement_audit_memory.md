# Agent 1 Requirement Audit Memory

This file stores recurring requirement-audit lessons for Agent 1.

| Date | Project | Audit Lesson | Reuse Condition | Status |
|---|---|---|---|---|
| 2026-05-22 | workspace | Always scan PRD/source directories fully before generating rules or cases. | PRD parsing, prototype audit, incremental update | Active |
| 2026-05-22 | 订单详情页优化 | Treat labels such as 暂缓、看开发评估、开发评估 as version-scope gates instead of confirmed implementation. | PRD contains uncertain scope markers | Active |
| 2026-05-22 | 消息提醒功能以及重要待办 | Treat ambiguous notification channels, real-time SLA, count scope, and external messaging channels as audit questions before execution; do not convert them into hard pass/fail criteria. | Notification, badge, SMS, navigation count requirements | Active |
| 2026-05-23 | 国内包裹签收处理功能 | Time-based status rules must ask for calendar semantics, boundary inclusiveness, rounding, weekend/holiday handling, and which records are excluded from statistics. | Timeout, SLA, sign/receive/process duration, operational dashboards | Active |
| 2026-05-23 | 黑白名单及采购账号 | Account and authorization requirements must ask for precedence, trust exemptions, token expiry, concurrent enablement, backend bypass protection, and failure fallback. | Access control, procurement accounts, OAuth/token, middleware auth | Active |
| 2026-05-23 | 全球站批量导入功能 | Screenshot-only template PRDs are incomplete until field mapping, row error strategy, external API fallback, duplicate/concurrent import behavior, and write scope are confirmed. | Batch import, Excel template, SKU/price compare, cart/order generation | Active |
| 2026-05-23 | 表单下载 | Export requirements must define source-of-truth fields, fixed layout baseline, dynamic field tolerance, image embedding expectation, multilingual labels, and template asset ownership. | Form download, invoice, label, delivery note, template regression | Active |
