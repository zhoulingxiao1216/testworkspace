# 变更日志

- 日期：2026-06-23
- 修改文件：全球站压测脚本/Performance/config/rules_loader.py、全球站压测脚本/Performance/core_stress.py、测试平台自建/pages/3_性能压测.py
- 修改类型：修改
- 描述：压测失败上报增加测试账号、响应详情及逐条失败明细日志

## 变更摘要

### 变更点 1：rules_loader.verify_response
- 变更原因：失败仅显示 code 不匹配，缺少后端 msg 等业务详情
- 变更方式：新增 extract_response_detail，校验失败时附加 msg/message 等字段

### 变更点 2：core_stress 失败事件
- 变更原因：Locust failures.csv 无法定位是哪个账号、具体响应内容
- 变更方式：_fire_event 统一格式化 `[账号:xxx]` 与详情，并写入 STRESS_FAILURE_DETAIL_PATH JSONL

### 变更点 3：测试平台失败页签
- 变更原因：UI 未展示账号与详细错误
- 变更方式：解析 failures.csv 新增账号/详情列，并展示 failure_details.jsonl 样本明细
