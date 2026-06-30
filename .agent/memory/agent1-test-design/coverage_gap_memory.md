# Agent 1 Coverage Gap Memory

This file receives coverage gaps discovered during design review or Agent 2 execution.

| Date | Project | Gap | Source | Required Action | Status |
|---|---|---|---|---|---|
| 2026-05-23 | 国内包裹签收处理功能 | Scanner/PDA and cross-day package data are execution prerequisites that can invalidate otherwise complete design coverage. | Historical learning import | Require explicit hardware, signed/unprocessed, weekend, private-package, and multi-order fixture checklist. | Active |
| 2026-05-23 | 黑白名单及采购账号 | Token expiry, procurement failure, and concurrent account enablement are hard to cover without controlled data or service hooks. | Historical learning import | Mark as dev-assisted/manual/mocked scenarios unless controlled fixtures are available. | Active |
| 2026-05-23 | 全球站批量导入功能 | Import cases can look complete while lacking valid/invalid row fixtures, external-service failure controls, and post-write evidence. | Historical learning import | Require template fixture inventory, row-level expected errors, API/mock strategy, and cart/order write verification. | Active |
| 2026-05-23 | 表单下载 | Export cases are incomplete without original template assets, field source mapping, dynamic-tolerance rules, and downloaded-file comparison method. | Historical learning import | Require template-field matrix, artifact baseline, comparison script or manual review protocol, and image/multilingual assertions. | Active |
