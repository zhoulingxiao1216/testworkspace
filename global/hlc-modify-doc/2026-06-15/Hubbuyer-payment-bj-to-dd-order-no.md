# 变更日志

- 日期：2026-06-15
- 修改文件：全球站巡检脚本/hubbuyer/checker/api/payment_target.py
- 修改类型：修改
- 描述：支付成功后按 BJ→DD 规则写入订单号并更新 payment_orderid.json

## 变更摘要

### 变更点 1：支付后订单号转换
- 变更原因：支付成功后报价单号 B2B-BJ 转为订单号 B2B-DD
- 变更方式：`payment_orderid.json` 列表首位写入 DD 号，并记录 `B2B_quote_latest` / `B2B_order_latest`；成功日志展示 `BJ→DD`
