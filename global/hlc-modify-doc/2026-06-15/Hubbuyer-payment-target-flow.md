# 变更日志

- 日期：2026-06-15
- 修改文件：全球站巡检脚本/hubbuyer/checker/api/payment_target.py、config/data/payment_target.json、config/rules/payment_target.json、config/settings.py、core/batch_checker.py、core/notifier.py
- 修改类型：新增
- 描述：新增 B2B 指定报价单支付巡检流程（目标单号 B2B-BJ-KOR8-260615-392），待接入支付 curl

## 变更摘要

### 变更点 1：payment_target 流程
- 变更原因：需对指定报价单单独支付，不受常规 3 天间隔限制
- 变更方式：新增 `payment_target.py`，配置见 `payment_target.json`；Stripe/收银台步骤待 curl 填入后启用

### 变更点 2：quote/pay curl 对齐（2026-06-15 更新）
- 变更原因：用户提供了 `/api_b2b/quote/pay` 完整 curl
- 变更方式：新增 `get_b2b_pay_headers`；`payment_target.json` 写入 url/headers/json；token/cookie 仍从巡检登录态动态获取
