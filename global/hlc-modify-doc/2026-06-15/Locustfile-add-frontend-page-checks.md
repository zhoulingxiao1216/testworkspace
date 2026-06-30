# 变更日志

- 日期：2026-06-15
- 修改文件：全球站压测脚本/Performance/locustfile.py、全球站压测脚本/Performance/config/settings.py
- 修改类型：新增 / 修改
- 描述：为压测脚本补充用户前台页面级检查项（SPA 文档级：状态码 + 标题关键字断言），覆盖免登录与需登录页面。

## 变更摘要

### 变更点 1：config/settings.py 新增前台页面级检查配置
- 变更原因：原脚本仅有 1 个首页页面访问项，且只校验 HTTP 状态码，缺少前台页面覆盖与防白屏断言。
- 变更方式：
  - 新增 `STRESS_ENABLE_PAGE_CHECK`（页面检查总开关，环境变量可控）。
  - 新增 `PAGE_TITLE_KEYWORD`（标题关键字断言，默认 `Hubbuyer | B2B Sourcing Platform`，环境变量可覆盖）。
  - 新增 `GUEST_PAGE_CHECKS`（免登录页面：B2B 首页、关键词搜索结果页）。
  - 新增 `AUTH_PAGE_CHECKS`（需登录页面：购物车、购物车附加项、订单提交确认）。
  - `PAGE_VISIT_URLS` 改为由 `GUEST_PAGE_CHECKS` 按当前环境 `B2B_SITE_URL` 拼接生成（test/main/prod 通用）。
  - `TASK_WEIGHTS` 新增 `member_page_visit` 权重，用于真实账号访问登录态页面。

### 变更点 2：locustfile.py 新增页面级检查能力
- 变更原因：需在 Locust 模型内对前台页面做可高并发的文档级检查，并区分免登录/登录态页面归属。
- 变更方式：
  - 新增模块级 `_perform_page_check()`：GET 页面 → 校验 2xx/3xx + 标题关键字（缺失判为疑似白屏/降级）。
  - 新增 `_PAGE_BROWSER_HEADERS` 浏览器请求头与 `_build_page_list()` 配置转换工具。
  - 虚拟访客 `HubbuyerGuestBrowseUser`：`task_page_visit` 改为按 `GUEST_PAGE_CHECKS` 加权随机访问，并加入标题断言；`_get_page` 改为委托给 `_perform_page_check`。
  - 真实账号 `HubbuyerStressUser`：新增 `member_pages`、`_visit_member_page()`（携带登录态 Cookie 访问）与 `task_member_page_visit` 任务。
- 备注：站点为 SPA，各前台路由 GET 返回同一 index.html 外壳，标题统一；页面级检查靠 URL 名称区分、靠标题关键字断言防白屏。已实地验证免登录页面返回 200 且命中标题关键字。
