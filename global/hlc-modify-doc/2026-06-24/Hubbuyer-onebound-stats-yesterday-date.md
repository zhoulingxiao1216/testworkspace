# 变更日志

- 日期：2026-06-24
- 修改文件：全球站巡检脚本/hubbuyer/checker/api/onebound_daily_stats.py、config/data/onebound_daily_stats.json、config/rules/onebound_daily_stats.json、core/notifier.py、config/settings.py
- 修改类型：修改
- 描述：万邦 API 统计改为默认拉取前一日数据，适配早上 8 点巡检场景

## 变更摘要

### 变更点 1：统计日期偏移
- 变更原因：巡检脚本早上 8 点执行，当日数据不完整，应统计前一日（如 24 日跑则取 23 日）
- 变更方式：新增 `stats_date_offset_days: -1` 配置，默认取前一天；分页逻辑跳过当日记录后继续翻页

### 变更点 2：任务与推送文案
- 变更原因：「今日调用统计」与业务口径不符
- 变更方式：任务描述与微信推送键名改为「万邦 API 前日调用统计」
