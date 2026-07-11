# Agent2 用例可执行性评审报告

| 项目 | 内容 |
|:--|:--|
| 项目 | 消息提醒功能以及重要待办 |
| Run ID | `2026-05-22_message_reminder_important_todo` |
| 评审角色 | `agent2-test-execution` |
| 评审模式 | 只读评审，不执行真实测试用例 |
| 评审结论 | `passed_with_external_blockers` |

## 一、评审总览

Agent2 已独立读取需求、旧版用例和 Agent1 标准化产物。整体判断：测试范围覆盖较完整，62 条用例已可作为后续执行基础；但真实执行前仍缺少环境、账号、权限、造数方式、短信通道、异常 Mock 授权等外部前置条件。

由于用户明确要求 Agent2 暂不执行测试用例，本轮不进入 E1 环境预检，也不执行任何 UI/API/DB 操作。

## 二、可执行范围

| 范围 | 状态 | 说明 |
|:--|:--|:--|
| 通用气泡基础展示、汇总、`99+` | 可执行，待环境 | 有环境和数据后可优先执行 |
| 客户管理主链路 | 可执行，待数据 | 需要未匹配客户经理客户和可匹配账号 |
| B2B 订单/发货主链路 | 可执行，待数据 | 需要报价单、代购订单、发货单待审核数据 |
| 点击交互 | 可执行，待气泡数据 | 需要对应气泡存在 |
| 重要待办基础汇总 | 可执行，待子模块口径 | UI 汇总可测，业务准确性依赖子模块定义 |
| 右侧导航基础数量 | 条件可执行 | 统计范围与权限范围需确认 |
| 短信提醒 | 条件可执行 | 需要短信配置入口和发送记录/Mock 通道 |
| 异常恢复、负数、弱网、并发 | 需 Mock/开发配合 | 不建议直接手工执行 |

## 三、反馈清单

| ID | 优先级 | 类型 | 关联范围 | 反馈内容 | 处理方式 | 状态 |
|:--|:--|:--|:--|:--|:--|:--|
| F-001 | High | environment | 全部 UI 用例 | 缺少测试环境 URL、系统入口、登录账号和角色权限矩阵 | 外部前置条件，写入 blocking_risks | open_external |
| F-002 | High | data_precondition | `BUB/CM/ORD/SHIP/TODO/NAV` | 缺少可控测试数据或造数方式 | 外部前置条件，后续需 API/UI/受控 DB mock seed | open_external |
| F-003 | High | environment | `SMS` | 缺少短信测试通道或可查询发送记录/Mock 通道，且相关人员范围未明确 | 外部前置条件，短信用例条件执行 | open_external |
| F-004 | High | db_mock | 异常恢复类用例 | 缺少 API/DB mock seed 或接口拦截授权，无法稳定模拟加载失败、负数、状态不同步 | 外部前置条件，执行前需授权 | open_external |
| F-005 | High | scope_confirmation | `TODO` | 重要待办三个子模块的待办定义、完成条件、权限过滤未明确 | 产品确认项，执行时仅能验证 UI 汇总 | open_external |
| F-006 | High | scope_confirmation | `NAV` | 右侧导航消息/待办/订单统计范围、权限范围、刷新口径未明确 | 产品确认项，相关用例条件执行 | open_external |
| F-007 | Medium | handoff_quality | 交接清单 | 需要交接清单明确环境、数据、短信、Mock 授权与 `execute_cases=false` | Agent1 已在交接清单中覆盖 | resolved |
| F-008 | Medium | traceability | P0/Smoke | Smoke 队列需要聚焦“看得到、数得对、点得通、变得动” | Agent1 已生成 40 条 Smoke 候选，后续可按环境压缩 | resolved_with_risk |

## 四、建议 Smoke 队列

后续真实执行时，建议首轮从以下范围中按环境可用性压缩选择：

| 模块 | 建议范围 |
|:--|:--|
| 通用气泡 | `TC-BUB-001`、`TC-BUB-003`、`TC-BUB-006`、`TC-BUB-007` |
| 客户管理 | `TC-CM-001`、`TC-CM-004` |
| 订单管理 | `TC-ORD-001`、`TC-ORD-004`、`TC-ORD-005`、`TC-ORD-006` |
| 发货配送 | `TC-SHIP-001`、`TC-SHIP-005` |
| 点击交互 | `TC-INT-001`、`TC-INT-002` |
| 重要待办 | `TC-TODO-001`、`TC-TODO-002`、`TC-TODO-008` |
| 右侧导航 | `TC-NAV-001`、`TC-NAV-002`、`TC-NAV-003` |
| 短信 | 短信通道可用时追加 `TC-SMS-001`、`TC-SMS-002` |

## 五、复审结论

Agent1 已补齐标准测试用例、执行交接清单和 run 输出记录。Agent2 的建议中，能由 Agent1 处理的“交接清单、条件用例、阻塞风险标注”已经覆盖；剩余 F-001 到 F-006 属于外部执行前置条件，不应由 Agent1 伪造解决。

本轮结论：设计产物可进入归档与 reflection；真实执行仍需等待环境、账号、数据、短信通道、Mock/DB seed 授权。
