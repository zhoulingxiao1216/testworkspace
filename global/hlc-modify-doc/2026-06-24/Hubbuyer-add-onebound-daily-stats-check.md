# 变更日志

- 日期：2026-06-24
- 修改文件：全球站巡检脚本/hubbuyer/checker/api/onebound_daily_stats.py 等
- 修改类型：新增
- 描述：接入万邦控制台每日 API 调用统计巡检项

## 变更摘要

### 变更点 1：万邦 API 调用统计 checker
- 变更原因：需要在每日巡检中自动汇总万邦接口调用次数
- 变更方式：新增 `onebound_daily_stats.py`，调用万邦控制台 `api_log_use&do=browse` 并按日聚合

### 变更点 2：巡检框架注册
- 变更原因：将统计任务纳入 batch 调度、企微通知与开关控制
- 变更方式：新增 rules/data 配置，更新 `settings.py`、`batch_checker.py`、`notifier.py`
