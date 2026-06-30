# 变更日志

- 日期：2026-06-18
- 修改文件：全球站压测脚本/Performance/core_stress.py、全球站压测脚本/Performance/config/settings.py、全球站压测脚本/Performance/config/rules_loader.py、全球站压测脚本/Performance/locustfile.py、全球站压测脚本/Performance/locustfile_api.py、全球站压测脚本/Performance/config/data/quote_download_refs.py、全球站压测脚本/Performance/config/rules/down_quote.json
- 修改类型：新增 / 修改
- 描述：新增固定参考报价单下载检查点，绑定 performance_test_004@126.com（USA900004-test）

## 变更摘要

### 变更点 1：报价单下载检查点
- 变更原因：压测链路缺少 downQuote 接口校验，无法确认报价单文件可正常导出
- 变更方式：新增独立低频任务 `下载报价单`，仅当当前账号匹配参考配置时执行 GET `/api_b2b/quotedetail/downQuote`

### 变更点 2：配置与断言
- 变更原因：下载响应为文件流而非 JSON，需独立断言规则
- 变更方式：新增 `quote_download_refs.py`（main 环境绑定 `B2B-BJ-USA900004-260615-111`）、`down_quote.json` 与 `verify_download_response`

### 变更点 3：开关与任务权重
- 变更原因：需支持独立启停，避免与下单链路强耦合
- 变更方式：新增 `STRESS_ENABLE_QUOTE_DOWNLOAD` 开关与 `quote_download` 任务权重（默认 1）
