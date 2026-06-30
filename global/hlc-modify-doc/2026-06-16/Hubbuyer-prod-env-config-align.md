# 变更日志

- 日期：2026-06-16
- 修改文件：hubbuyer/config/url/prod.py、config/data/purchase_order_*.json、core/admin_config.py 等
- 修改类型：修改 / 新增
- 描述：补齐 prod 环境配置，后台联动 URL 按 ENV_TYPE 动态解析

## 变更摘要

### 变更点 1：prod URL 与后台 API 动态化
- 变更原因：purchase_order_audit/ops JSON 硬编码 main 域名，prod 无法正确执行
- 变更方式：新增 admin_config 解析相对路径；prod 补 ADMIN_url；allowed_envs 加入 prod
