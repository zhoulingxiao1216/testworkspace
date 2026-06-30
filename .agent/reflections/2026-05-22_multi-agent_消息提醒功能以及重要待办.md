# Reflection - 消息提醒功能以及重要待办

## Run Summary

| 项目 | 内容 |
|:--|:--|
| Run ID | `2026-05-22_message_reminder_important_todo` |
| 模式 | `agent1-test-design` + `agent2-test-execution` 并行 |
| Agent2 执行状态 | 暂不执行真实测试用例 |
| 最终状态 | `REFLECTION_READY` |

## What Happened

Agent1 子任务负责标准化测试设计产物，输出 62 条标准用例、40 条 Smoke 候选、5 条条件用例和执行交接清单。

Agent2 子任务以只读方式并行评审需求、旧用例和已生成文档，输出 8 条反馈。其中 F-001 到 F-006 属于外部执行前置条件，F-007 和 F-008 已由 Agent1 的交接清单与 Smoke 候选覆盖。

## What Worked

| 事项 | 结果 |
|:--|:--|
| 并行处理 | Agent1 和 Agent2 通过独立 subagent 同时工作，避免了单 Agent 串行假扮两个角色 |
| 角色边界 | Agent2 未修改设计产物，只输出评审建议 |
| 反馈分级 | 外部阻塞项保留为 `open_external`，没有让 Agent1 伪造环境、账号或数据 |
| 运行记录 | run 下已生成 `agent1_output.yaml`、`agent2_review.yaml`、`remediation.yaml` |

## What Needs Improvement

| 问题 | 后续改进 |
|:--|:--|
| runtime subagent 名称显示为系统昵称 | run 记录中必须映射到 `agent1-test-design` / `agent2-test-execution` |
| Agent2 早于 Agent1 完成 | Orchestrator 需要支持“预评审 + 产物完成后复审”的两阶段模式 |
| Smoke 数量偏多 | 真实执行前 Agent2 应按环境可用性压缩首轮 Smoke |
| 外部前置条件多 | 后续需要统一的环境、账号、数据、短信、Mock 授权模板 |

## Reusable Learning

当 Agent2 的建议主要是环境、账号、数据、短信通道、Mock 授权等执行前置条件时，不应要求 Agent1 硬改用例“解决”这些问题；应将其写入 `blocking_risks`、`exchange feedback` 和 run artifact，等待人工或执行环境补齐。

## Evolution Decision

本次经验先保留为 memory candidate，不直接修改 skill/workflow。若后续第二个项目也出现“Agent2 外部阻塞项被误当作 Agent1 设计缺陷”的情况，再考虑提升为 workflow 规则。
