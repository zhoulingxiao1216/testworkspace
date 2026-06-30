# 变更日志

- 日期：2026-06-16
- 修改文件：全球站巡检脚本/hubbuyer/checker/api/backend_admin_checkpoint.py、config/data/backend_admin.json、config/rules/backend_admin.json、config/rules/exchange_rate.json、config/rules/purchase_order_ops.json、config/settings.py、core/batch_checker.py、core/runner.py、core/notifier.py
- 修改类型：重构
- 描述：按方案 A 合并纯后台检查点，汇率置于最后；联动审核独立分区

## 变更摘要

### 变更点 1：后台管理检查点 orchestrator
- 变更原因：汇率与代购仓配四步同属纯后台，需统一入口
- 变更方式：新增 backend_admin_checkpoint.py，顺序为代购仓配 → 汇率

### 变更点 2：执行顺序与报告三分区
- A 前台：web/login/图搜/关键词/加购/附加项/提交/支付
- B 联动：报价单审核、代购订单审核
- C 后台管理：代购仓配、汇率（最后）

### 变更点 3：下线独立 rules 任务
- exchange_rate.json、purchase_order_ops.json 不再单独注册巡检任务，改由 backend_admin 调度
