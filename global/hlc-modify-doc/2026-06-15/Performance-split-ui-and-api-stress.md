# 变更日志

- 日期：2026-06-15
- 修改文件：全球站压测脚本/Performance/core_stress.py（新增）、locustfile.py（重构）、locustfile_api.py（新增）、locustfile_ui.py（新增）、测试平台自建/pages/3_性能压测.py（修改）
- 修改类型：重构 / 新增 / 修改
- 描述：将压测脚本物理拆分为「接口压测」与「UI 压测」两套独立入口，业务逻辑统一沉淀到共享核心 core_stress.py，并在测试平台增加「压测类型」选择。

## 变更摘要

### 变更点 1：新增 core_stress.py（共享核心）
- 变更原因：原 locustfile.py 把接口任务与 UI 页面任务混在同两个用户类里，无法分别运行。
- 变更方式：
  - 迁移全部 helper、业务方法、事件上报、页面检查（`_perform_page_check` 等）到 core_stress.py。
  - 将两个用户类改为 `abstract = True` 基类：`RealUserBase`（真实账号全部业务方法）、`GuestUserBase`（虚拟访客方法）；Locust 不会实例化抽象基类。
  - 原 `task_*`（带 @task/@tag）方法改为无装饰器的 `run_*` 行为单元，供各入口子类挂载。
  - 新增 `make_split_load_shape(real_user_cls, guest_user_cls)` 工厂，按真实/虚拟用户分层加载，可只传一类用户类（供单套使用）。

### 变更点 2：locustfile_api.py（接口压测入口，新增）
- 变更原因：需要一套只跑接口检查项的脚本。
- 变更方式：定义 `ApiRealUser`（登录刷新/浏览/加购/购物车/提交报价单）+ `ApiGuestUser`（关键词搜索接口）；不含任何页面任务；启用 `ApiLoadShape`。

### 变更点 3：locustfile_ui.py（UI 压测入口，新增）
- 变更原因：需要一套只跑前台页面检查项的脚本。
- 变更方式：定义 `UiMemberUser`（登录态页面：购物车/附加项/订单确认，on_start 仅登录取 token）+ `UiGuestUser`（免登录页面：首页/搜索结果）；不含加购/下单/关键词等接口任务；启用 `UiLoadShape`。

### 变更点 4：locustfile.py（全部入口，重构）
- 变更原因：保持向后兼容（平台旧调用、全量回归）。
- 变更方式：改为薄入口，从 core_stress 导入基类，定义 `HubbuyerStressUser`/`HubbuyerGuestBrowseUser` 挂载全部任务（接口 + UI），启用 `SplitUserLoadShape`，行为与重构前一致。

### 变更点 5：测试平台 3_性能压测.py（修改）
- 变更原因：让平台可直接选择跑接口/UI/全部。
- 变更方式：
  - 新增 `SCRIPT_TYPE_OPTIONS` 映射与 `resolve_locustfile()`；启动配置区新增「压测类型」下拉（接口压测/UI 压测/全部）。
  - `start_locust_run` 按所选类型决定 `locust -f` 的入口文件；`draft_config` 增加 `script_type` 字段。
  - 进程识别由匹配 `locustfile.py` 改为正则 `locustfile(_\w+)?\.py`，兼容新增入口文件（命令检测、PowerShell 进程枚举、ps 解析三处）。
  - 执行预览命令、参数预览与历史表新增压测类型展示。

## 校验
- 四个脚本 AST/导入均通过；通过 Locust 用户类与任务列表反射校验：
  - locustfile_api.py：仅接口任务（无 page/member_page）。
  - locustfile_ui.py：仅页面任务（member_page_visit / page_visit）。
  - locustfile.py：接口 + UI 全量任务。
  - core_stress.py：不暴露具体用户类与 LoadShape（抽象基类未被拾取）。
- 平台页面 3_性能压测.py AST 通过，无 lint 错误。
