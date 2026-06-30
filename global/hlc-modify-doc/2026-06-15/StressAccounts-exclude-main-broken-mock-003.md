# 变更日志

- 日期：2026-06-15
- 修改文件：全球站压测脚本/Performance/config/data/stress_accounts.py
- 修改类型：修改
- 描述：将 main 环境登录稳定 500 的 mock 账号 performance_test_003 从压测账号池剔除，消除预热登录每轮固定 1 个失败。

## 背景（根因诊断）

压测时"登录 [预热]"每轮固定出现 1 个失败。逐账号实测定位：
- `performance_test_003@126.com` 在 main 环境登录接口稳定返回 HTTP 500：
  `ErrorException: strtotime(): Passing null to parameter #1 ($datetime) ... app/api/controller/LoginControll`
- 同账号在 test 正常；main 的其它 mock（004~050）与真实账号均正常。
- 该账号位于 main mock 池 `range(3, 51)` 中，round-robin 每轮都会被分配并执行预热登录，故每轮恰好 1 个失败。
- 属 main 后端 LoginController 对 NULL 日期字段的 `strtotime` 处理问题（脏数据/代码 bug），需后端根治。

## 变更摘要

### 变更点 1：MAIN_MOCK_ACCOUNTS 排除异常账号
- 变更原因：避免压测把流量打到 main 上登录必 500 的坏账号 003，导致每轮固定 1 个失败、干扰结果判读。
- 变更方式：新增 `MAIN_MOCK_EXCLUDE = {3}`，在生成 `MAIN_MOCK_ACCOUNTS` 时按 `index not in MAIN_MOCK_EXCLUDE` 过滤。仅影响 main 池（test 池保持不变，003 仍保留）。

## 校验
- main 前台池：49 → 48，已不含 performance_test_003@126.com。
- test 前台池：仍为 49，003 保留。
- 待后端修复 main LoginController 的 strtotime 空值处理 / 补全 003 日期字段后，可移除该排除项。
