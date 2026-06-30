# 变更日志

- 日期：2026-06-12
- 修改文件：全球站压测脚本/Performance/config/settings.py、全球站压测脚本/Performance/config/data/stress_accounts.py、测试平台自建/pages/3_性能压测.py
- 修改类型：修改
- 描述：为测试平台自建的性能压测增加 main 预发布环境支持，参照全球站巡检脚本的 main 环境配置方式

## 变更摘要

### 变更点 1：压测主配置 settings.py 增加 main 环境
- 变更原因：性能压测原仅支持 test / prod，需要新增 main 预发布环境
- 变更方式：
  - 将 `ENV_TYPE` 合法值集合由 `{"prod", "test"}` 扩展为 `{"prod", "main", "test"}`
  - `_ENV_DOMAINS` 新增 `main` 域名映射（api: `https://main-api.hubbuyer.com`，b2b: `https://main-b2b.hubbuyer.com`），与全球站巡检脚本 `config/url/main.py`、`config/api/main.py` 保持一致
  - `TOKEN_COOKIE_NAME` 判定由 `prod` 单独命中改为 `prod`/`main` 同时沿用 `pro_auth_token`（与巡检脚本 login.py 对 main 沿用 `pro_auth_token` 的行为一致）

### 变更点 2：压测账号池 stress_accounts.py 增加 main 环境
- 变更原因：main 环境压测需要独立的前台账号池
- 变更方式：在 `STRESS_ACCOUNTS_POOL` 中新增 `main` 键，配置前台账号（jump_url 指向 `https://main-b2b.hubbuyer.com/jump_common`），并保留多账号扩展注释

### 变更点 4：将 test 环境 mock 账号同步到 main 环境
- 变更原因：main 环境压测需要复用 test 环境同一批 mock 账号（`performance_test_003`~`050@126.com` 共 48 个）以支持批量并发
- 变更方式：
  - 抽取公共 `MOCK_ACCOUNT_RANGE = range(3, 51)`，新增 `MAIN_B2B_JUMP_URL` 与 `MAIN_MOCK_ACCOUNTS`（账号邮箱与 test 完全一致，仅 jump_url 切换为 `https://main-b2b.hubbuyer.com/jump_common`）
  - 在 `STRESS_ACCOUNTS_POOL["main"]["frontend"]` 后追加 `+ MAIN_MOCK_ACCOUNTS`
  - 校验结果：main 前台账号共 49 个（1 真实 + 48 mock），mock 邮箱列表与 test 完全一致，全部 mock 的 jump_url 指向 main 站点

### 变更点 3：性能压测页面 3_性能压测.py 支持选择 main
- 变更原因：页面环境下拉与状态回填需要识别 main 环境
- 变更方式：
  - 启动配置环境下拉 `env_options` 由 `["test", "prod"]` 改为 `["test", "main", "prod"]`
  - 历史任务状态回填的环境判定集合由 `{"test", "prod"}` 扩展为 `{"test", "main", "prod"}`，使 main 任务可正确回填账号与并发数
