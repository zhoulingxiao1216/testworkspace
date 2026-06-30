# 变更日志

- 日期：2026-06-15
- 修改文件：全球站巡检脚本/hubbuyer/checker/api/purchase_order_audit.py、config/data/purchase_order_audit.json、config/rules/purchase_order_audit.json、config/settings.py、core/batch_checker.py、core/notifier.py
- 修改类型：新增
- 描述：新增「后台代购订单审核」检查点骨架，待接入 curl

## 变更摘要

### 变更点 2：purchaseStatusUpdate curl 接入（2026-06-15）
- 变更原因：用户提供 B2B-DD-KOR8-260615-392 代购订单审核 curl
- 变更方式：`purchase_order_audit.json` 启用 `audit_api`；authorization 仍由后台登录动态获取

