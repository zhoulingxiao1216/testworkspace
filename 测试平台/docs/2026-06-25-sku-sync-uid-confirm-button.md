# SKU 批量同步 — 手动 UID 确认按钮

- 日期：2026-06-25
- 修改文件：`pages/4_sku_bulk_sync.py`
- 修改类型：修改
- 描述：手动填写客户 UID 时需点击「确认」后才生效

## 变更摘要

### 变更点 1：UID 确认流程
- 变更原因：输入框一改即生效，易误填 UID 后直接同步
- 变更方式：增加「确认」按钮，写入 `session_state.sku_sync_confirmed_uid`；修改 UID 后需再次确认

### 变更点 2：切换 UID 清理缓存
- 变更原因：避免沿用旧 Token 或旧预览计划
- 变更方式：确认新 UID 时清除 user_token 缓存及 sku_sync_plan
