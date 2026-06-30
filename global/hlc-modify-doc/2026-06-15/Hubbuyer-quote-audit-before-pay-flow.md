# 变更日志

- 日期：2026-06-15
- 修改文件：全球站巡检脚本/hubbuyer/core/batch_checker.py、checker/api/order_audit.py、checker/api/payment.py、checker/api/purchase_order_audit.py、checker/api/quote_order_store.py
- 修改类型：修改
- 描述：调整链路为报价单审核→前台支付→代购订单审核

## 变更摘要

### 变更点 1：巡检执行顺序
- 变更原因：报价单须先后台审核，用户前台支付后，才能代购订单审核
- 变更方式：`submit_order` → `order_audit` → `payment` → `purchase_order_audit`

### 变更点 2：单号联动
- 报价单审核：本轮新提交 BJ 号，审核通过后写入 `B2B_quote_pending_pay`
- 前台支付：仅支付待支付报价单，成功后 BJ→DD 写入 `B2B_round_order`
- 代购订单审核：仅审核本轮已支付 DD 号
