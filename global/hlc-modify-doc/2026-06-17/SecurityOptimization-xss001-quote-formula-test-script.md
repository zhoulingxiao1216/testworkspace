# 变更日志

- 日期：2026-06-17
- 修改文件：安全优化/测试文档/xss001_quote_formula_test.py
- 修改类型：新增
- 描述：新增 TC-SEC-XSS-001 报价公式注入 API 造数与 xlsx 校验脚本

## 变更摘要

### 变更点 1：xss001_quote_formula_test.py
- 变更原因：用户需基于 quote/create curl 串联 updateSkuNumberData 与 Excel 校验
- 变更方式：新增脚本，支持单 payload / 全量 payload 与 --check-xlsx 单元格类型检查
