# 变更日志

- 日期：2026-06-16
- 修改文件：全球站巡检脚本/hubbuyer/checker/api/order_audit.py、checker/api/purchase_order_audit.py
- 修改类型：修改
- 描述：后台登录/审核 URL 运行时解析，修复 prod 令牌解析失败

## 变更摘要

### 变更点 1：admin 会话头与登录域
- 变更原因：模块导入时冻结 BASE_URL，或登录域与审核 URL 不一致时返回 30001 令牌解析失败
- 变更方式：admin_api_base_url/build_admin_auth_headers 运行时读取 ENV；审核前校验 login/audit 域名一致
