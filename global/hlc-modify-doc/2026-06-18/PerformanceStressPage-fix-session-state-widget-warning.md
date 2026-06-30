# 变更日志

- 日期：2026-06-18
- 修改文件：测试平台自建/pages/3_性能压测.py
- 修改类型：修改
- 描述：修复 Streamlit 控件 Session State 与 value 参数冲突警告

## 变更摘要

### 变更点 1：统一 Session State 初始化
- 变更原因：`stress_real_users_main` 等控件同时通过 Session State 赋值与 `value=` 传默认值，触发 Streamlit 警告
- 变更方式：新增 `ensure_session_default` / `init_stress_form_defaults`，移除带 key 控件的 `value=` / `index=` 参数
