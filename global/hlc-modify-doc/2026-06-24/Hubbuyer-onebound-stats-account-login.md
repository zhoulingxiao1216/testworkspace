# 变更日志

- 日期：2026-06-24
- 修改文件：全球站巡检脚本/hubbuyer/checker/api/onebound_daily_stats.py
- 修改类型：修改
- 描述：万邦调用统计支持账号密码自动登录

## 变更摘要

### 变更点 1：自动登录
- 变更原因：避免 PHPSESSID 频繁过期，改为优先使用万邦控制台账号登录
- 变更方式：新增 `_build_session()`，POST `go=login&do=login`，保留 Cookie 作为备用方案
