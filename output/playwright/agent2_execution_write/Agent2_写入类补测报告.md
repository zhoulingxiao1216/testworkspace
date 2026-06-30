# Agent2 写入类补测报告

- 执行时间：2026-05-25T14:36:10
- 范围：报价单审核、代购订单允许采购、发货单开始审核

| 用例 | 状态 | 记录 | 实际结果 | 备注 |
|:--|:--|:--|:--|:--|
| TC-ORD-006 | BLOCKED | B2B-BJ-JPN34-260423-083 | quote: pending 35 -> 35 | Action executed or attempted, but the pending count did not show the expected decrement. |
| TC-ORD-008 | BLOCKED | B2B-DD-JPN12-260525-009 | agent_buy: pending 98 -> 98 | Action executed or attempted, but the pending count did not show the expected decrement. |
| TC-SHIP-004 | PASS | WL-CHN6-251222-003 | ship: pending 10 -> 9 |  |
