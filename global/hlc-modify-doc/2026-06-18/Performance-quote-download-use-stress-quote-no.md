# 变更日志

- 日期：2026-06-18
- 修改文件：全球站压测脚本/Performance/core_stress.py、全球站压测脚本/Performance/config/settings.py、全球站压测脚本/Performance/locustfile.py、全球站压测脚本/Performance/locustfile_api.py、全球站压测脚本/Performance/config/rules/down_quote.json、全球站压测脚本/Performance/config/data/quote_download_refs.py
- 修改类型：修改 / 删除
- 描述：报价单下载检查点改为下单成功后使用当轮压测产生的 quote_no

## 变更摘要

### 变更点 1：下载时机
- 变更原因：报价单数据应来自压测当轮下单，而非固定历史单号
- 变更方式：`run_browse_add_cart_submit_order` 在 `quote/create` 成功后立即调用 `downQuote`，传入当轮返回的 `quote_no`

### 变更点 2：移除固定参考单
- 变更原因：固定单号与压测数据模型不一致
- 变更方式：删除 `quote_download_refs.py`、独立 `task_quote_download` 任务及账号绑定逻辑

### 变更点 3：开关联动
- 变更原因：下载检查点依附于下单链路
- 变更方式：`STRESS_ENABLE_QUOTE_DOWNLOAD` 默认跟随 `STRESS_ENABLE_SUBMIT_ORDER`；语言参数由 `STRESS_QUOTE_DOWNLOAD_LANGUAGE` 控制（默认 english）
