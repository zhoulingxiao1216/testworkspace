# 变更日志

- 日期：2026-06-24
- 修改文件：全球站巡检脚本/hubbuyer/core/notifier.py、core/batch_checker.py、checker/api/onebound_daily_stats.py
- 修改类型：修改
- 描述：微信推送追加万邦 API 各接口实际/总调用数明细

## 变更摘要

### 变更点 1：Notifier 万邦统计明细
- 变更原因：微信群推送仅显示 ✅，缺少各 API 实际调用数与总调用数
- 变更方式：新增 `_onebound_extra_lines`，在「外部 API 用量统计」区块下追加合计与各接口明细

### 变更点 2：BatchChecker 保留 stats
- 变更原因：结构化 stats 未传入 report_data，无法稳定渲染明细
- 变更方式：`_store_task_result` 透传 checker 返回的 `stats` 字段

### 变更点 3：onebound_daily_stats details 序列化
- 变更原因：`defaultdict` 不利于后续结构化读取
- 变更方式：返回 `dict(grouped)` 作为 stats.details
