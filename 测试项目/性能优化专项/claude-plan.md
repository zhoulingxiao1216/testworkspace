# 全球站上线整改三组分工计划（claude-plan）

> 生成日期：2026-06-03
> 整改内容基准：[docs/architecture/97-全球站上线风险与性能扫描记录.md](../docs/architecture/97-全球站上线风险与性能扫描记录.md)（17 轮扫描，基准日 2026-04-27/28）
> 交叉核验来源：`plan/claude最终版.md`、`plan/codex最终版.md`、`plan/cursor最终版.md`、`plan/hermes最终版.md`
> 本文做法：先把四份最终版声明的「已完成」逐项 `Read` 真实代码复验（确认后**移除**，见 §1）；再把「部分完成 + 未完成 + 需环境确认」按**功能为主**收敛为修复单元，并按**工时权重打散**为三组——三组工时和与 P0 硬骨头数量都尽量持平，**不把重点工作堆在一组**；**FJX/附加项整条结算链路保持在同一组、不拆分**。每条都给①97 文档原文索引（章节+行号）②当前代码位置；原文行号/描述漂移处按当前代码补正。

---

## 0. 本轮代码确认说明（不猜测，已读真实代码）

本会话独立重读并确认的关键代码（用于「移除已完成」与「锚定 P0」两个决定）：

- 已完成项全部复验：[app.php:18](../api-all/config/app.php:18)、[log.php:23/40](../api-all/config/log.php:23)、[PasswordService.php](../api-all/app/service/PasswordService.php)、[LoginController.php:76-82](../api-all/app/api/controller/LoginController.php:76)、[RegisterController.php:137-140](../api-all/app/api/controller/RegisterController.php:137)、[ProductController.php:49-59](../api-all/app/api_ali/controller/ProductController.php:49)、[CartController.php:437-444](../api-all/app/api_b2b/controller/CartController.php:437)。
- P0 锚点全部复验：[StripePayment.php:344-393](../api-all/app/service/payment/driver/StripePayment.php:344)、[ShipOrderService.php:306](../api-all/app/admin_b2b/service/ShipOrderService.php:306)、[QuoteService.php:355](../api-all/app/service/b2b/QuoteService.php:355)、[DbService.php:19](../api-all/app/service/DbService.php:19)、[ProductDetail.php:97-127](../api-all/app/model/ProductDetail.php:97)、[CorsMiddleware.php:17-18](../api-all/app/middleware/CorsMiddleware.php:17)、[B2bIndexCacheService.php:100](../api-all/app/api_b2b/service/B2bIndexCacheService.php:100)、[BaseController.php:9-17](../api-all/app/admin/controller/BaseController.php:9)、[helper.php:89-162/272-290](../api-all/app/helper.php:89)。
- 其余条目沿用四份最终版四方交叉的代码引用（均为 `Read`/`rg` 复验所得，非注释/commit 推断）。

> **纠错记录**：`plan/claude最终版.md` 曾把 `decodeOptionalJson` 标为「未能证实」。经复验确实存在于 [CartController.php:437-444](../api-all/app/api_b2b/controller/CartController.php:437) 并在 :466 调用 —— 计入**已完成**，本文据此移除。

---

## 1. ✅ 已完成（7 项，已移除，不再分工）

| # | 事项 | 97 文档索引 | 当前代码证据（已复验） |
|:--:|------|------|------|
| F1 | `api-all` 生产 debug 关闭 | §2.1 行133 | [app.php:18](../api-all/config/app.php:18) `'debug' => false` |
| F2 | 默认 + payment 日志级别 ERROR | §2.1 行133 / §4.8 行574 | [log.php:23](../api-all/config/log.php:23) 与 :40 `Monolog\Logger::ERROR` |
| F3 | 用户端密码 `password_hash` + 登录渐进升级 | §2.8 行318 / §9.3 行1582 | [PasswordService.php](../api-all/app/service/PasswordService.php) + [LoginController.php:76-82](../api-all/app/api/controller/LoginController.php:76)、[RegisterController.php:140](../api-all/app/api/controller/RegisterController.php:140) |
| F4 | 注册邮箱验证码校验恢复 | §9.3 行1582 | [RegisterController.php:137-139](../api-all/app/api/controller/RegisterController.php:137) |
| F5 | `keyword` 缓存 key 纳入完整筛选/排序 hash | §17.3 行3059 | [ProductController.php:50-59](../api-all/app/api_ali/controller/ProductController.php:50) |
| F6 | 商品列表主动搜索可禁用首页缓存 | §17.3 行3059 | [ProductController.php:49/54](../api-all/app/api_ali/controller/ProductController.php:49) + [Alibaba/list.vue:419](../user-b2b-view/src/views/Alibaba/list.vue:419) |
| F7 | 购物车导入可空 JSON 安全解码 | （97 未单列） | [CartController.php:437-444](../api-all/app/api_b2b/controller/CartController.php:437) |

> 注：F3/F4/F5/F6 仅覆盖用户端；管理员密码、商品详情写库等同源问题仍未修，已分别落入下面三组。

---

## 2. 分组总览与工作量平衡

切分逻辑：每个修复单元打 1～4 个同源条目，并按**工时权重**估值（1=改配置/单点；2=中等改造；3=事务/重构/批量化/IDOR 收口）。再把 P0 硬骨头**按功能分散**到三组，使「工时和」「P0 数量」「单元数」都尽量持平，避免重点全压一组；**FJX/附加项整条结算链路集中在第二组、不拆分**。

| 组 | 功能主题 | 单元 | **P0 硬骨头** | 工时权重和 | 各组锚定的重点 |
|:--:|------|:--:|:--:|:--:|------|
| **第一组** | 资金交易与数据一致性 | 12 | **4** | ≈23 | 支付幂等、余额原子化、运费 bug、迁移兼容 |
| **第二组** | 购物结算链路与接入安全 | 13 | **4** | ≈25 | 越权删购物车、IDOR 归属、**FJX 全链路（算费/iframe）**、CORS、开放接口鉴权 |
| **第三组** | 数据与性能基础设施 | 12 | **3** | ≈25 | 运行时 DDL、聊天分表 bug、仓储入库 |

**两点关键安排**：①11 个 P0 按功能拆成 4/4/3 分别落到三组，每组都有自己的「必须修的硬骨头」，三组工时权重 23/25/25 基本拉平。②**购物车/报价/FJX/附加项是一条结算链路，全部放第二组**（越权删购物车、明细归属、FJX 后端算费、FJX iframe 边界），不再把「算费」与「iframe/归属」拆到不同组。每个单元保留原模块编号（A=资金链路 / B=安全接入 / C=数据基础设施）便于回溯来源。

---

## 3. 第一组 · 资金交易与数据一致性

> 功能主题：支付回调与幂等、余额与流水、订单/单号、队列补偿，以及支撑交易的**密钥配置、支付日志脱敏、财务导出、数据迁移兼容**。P0 锚点：支付幂等、余额原子化、运费赋值 bug、樱花站迁移兼容。

| 单元（原编号） | 权重 | 风险要点（修复边界） | 97 文档索引 | 当前代码位置 |
|:--:|:--:|------|------|------|
| **1.1 支付回调幂等与已收款补偿**（A1·P0） | 3 | `commit()` 后才 `createOrderFlow()`，提交后失败留「已付款/报价已支付/订单未生成」断点；重试因 `status=paid` 跳过主流程。改原子状态迁移（`paid_received`→`business_done`）+ 已收款未建单补偿。 | §4.3 行442 / §7.1 行1116 | [StripePayment.php:344-393](../api-all/app/service/payment/driver/StripePayment.php:344)（:392 `commit`/:393 `createOrderFlow`）、[BasePayment.php](../api-all/app/service/payment/BasePayment.php) |
| **1.2 支付入口归属 + 重复支付单 + 唯一约束**（A2·P0·⏸） | 2 | 报价支付仅按 `quote_no` 查、不带 `user_main_uuid`；`request_id=quote_no+4位随机` 易并发产生多条 pending；Workerman `Context` 与 `support\Context` 不一致需复核。按 `quote_no+user_main_uuid` 查、同渠道单活、`request_id` 全局唯一。**⏸ 唯一索引以线上 `SHOW INDEX FROM payment_orders` 为准**（[payment.sql](../api-all/app/sql_log/payment.sql) 未体现）。 | §4.4 行467 / §14.3 行2490 / §7.10 行1317 | [PaymentController.php:121-127](../api-all/app/pay/controller/PaymentController.php:121)、[StripePayment.php:375-378](../api-all/app/service/payment/driver/StripePayment.php:375) |
| **1.3 Stripe 充值分支补全入账**（A3） | 2 | `TYPE_RECHARGE` 命中后是空实现（`;`），Stripe 充值未真正入账。补余额入账 + 资金流水，纳入 1.1 的原子状态/补偿。 | §7.2 行1144 | [StripePayment.php:368-372](../api-all/app/service/payment/driver/StripePayment.php:368) |
| **1.4 统一 BalanceService 余额原子化**（A4·P0） | 3 | 充值/提现/调账/结算/运费/会员支付多处「读余额→PHP 计算→覆盖写回」，流水号 `totalData+1`；并发下余额覆盖、流水号重复。统一 `BalanceService`：事务 + `lockForUpdate` 或 `where balance>=amount`，流水号业务单号+UUID/雪花加唯一索引。会员充值终审已加锁可作样板（[MemberRechargeAuditService.php:61](../api-all/app/admin_b2b/service/MemberRechargeAuditService.php:61)）。 | §4.5 行491 / §7.3 行1163 / §9.4 行1618 / §17.1 行2981 | [FinanceController.php:100-139/224-270](../api-all/app/admin_b2b/controller/FinanceController.php:100)、[UserService.php:345-382](../api-all/app/admin_b2b/service/UserService.php:345)、[UserRechargeService.php:37-88](../api-all/app/admin_b2b/service/UserRechargeService.php:37)、[MemberPaymentController.php:402-435](../api-all/app/api_b2b/controller/MemberPaymentController.php:402) |
| **1.5 发货运费条件赋值 bug**（A5·P0） | 1 | `elseif` 条件里写成赋值 `$ship_order_data->total_fee = $ship_order_data->before_total_fee`（应 `==`/`bccomp`），补缴/退款/相等判断失真并波及余额、通知、流水。改严格比较 + `bccomp`，补单测。**原文 §4.6 标行272，已漂移到 :306。** | §4.6 行525 / §17.5 行3129 | [ShipOrderService.php:306](../api-all/app/admin_b2b/service/ShipOrderService.php:306) |
| **1.6 业务单号唯一化**（A6） | 2 | 单号/UUID 依赖 `count+1` 或 `date('YmdHi').rand(1000,9999)`，并发碰撞。改业务单号 + UUID/雪花，去 `count`。**原文笼统写 helper.php，实为 `api-all/app/helper.php`：生成函数 :89-162，时间+随机段 :272-290。** | §4.4 行467 / §8.7 行1482 / §14.4 行2531 | [helper.php:89-162](../api-all/app/helper.php:89)、[helper.php:272-290](../api-all/app/helper.php:272) |
| **1.7 队列失败重试/失败覆盖/快慢隔离/连接环境化**（A11·⏸） | 2 | `RetryQueueTask` 重试体全注释（无补偿）；`ProductDetailQueue` 失败后仍把状态写成成功（掩盖失败）；消费者不分快慢；redis-queue host 硬编码 + 默认密码。恢复批量补偿、修失败分支、快慢隔离、连接环境化。**⏸ 失败堆积/死信需看线上。** | §4.7 行541 / §7.5 行1206 / §7.6 行1233 | [RetryQueueTask.php:15-22](../api-all/app/task/RetryQueueTask.php:15)、[ProductDetailQueue.php:27-39](../api-all/app/queue/redis/ProductDetailQueue.php:27)、[redis-queue/process.php](../api-all/config/plugin/webman/redis-queue/process.php)、[redis-queue/redis.php:5-7](../api-all/config/plugin/webman/redis-queue/redis.php:5) |
| **1.8 生产配置与默认密钥环境化**（B1） | 1 | `api-open` debug 仍 true；`max_package_size` 仍 500MB（注释写 10M）；docker 开发态（默认 root 密码/DEBUG/api.insecure）；`CACHE_FLUSH_TOKEN` 有默认兜底。全部环境化，生产缺失即启动失败。 | §2.1 行133 / §6.9 行1067 / §12.4 行2260 | [api-open/config/app.php:18](../api-open/config/app.php:18)、[server.php:32](../api-all/config/server.php:32)、[CacheController.php:28](../api-all/app/index/controller/CacheController.php:28)、`docker/docker-compose.yml` |
| **1.9 日志与异常脱敏统一**（B9） | 2 | 请求日志全量落 header/param/response 无脱敏；`api-open` 日志仅排除 password；`HttpService` 落第三方 header/param 且无 `connect_timeout`；多处异常 `file/line/message/trace` 直出。统一字段级脱敏（token/password/pay_password/signature/authorization/cookie）+ 异常不外泄。 | §2.2 行160 / §4.8 行574 / §5.4 行704 / §5.8 行816 / §9.8 行1745 / §10.1 行1771 | [RequestLogMiddleware.php:27-50](../api-all/app/middleware/RequestLogMiddleware.php:27)、[ApiLogMiddleware.php:15](../api-open/app/middleware/ApiLogMiddleware.php:15)、[HttpService.php:29](../api-all/app/service/HttpService.php:29)、[PaymentNotifyController.php:31-65](../api-all/app/pay/controller/PaymentNotifyController.php:31)、`FinanceController:144/271`、`QuoteController:189` |
| **1.10 财务/订单导出远程拉图收口 + 异步化**（B12） | 2 | 订单/报价/发货导出：新 `FormExcelService` 已加 URL 校验+5s 超时+md5 临时名（局部缓解），但 `CURLOPT_SSL_VERIFYPEER=false` 仍在、无内网拦截；旧三个 Excel trait 仍裸 `file_get_contents` 同步拉图、临时路径拼接缺 `/`。统一短超时+占位图+内网拦截，大导出转异步任务。 | §5.3 行681 / §11.3 行2027 | [FormExcelService.php:1095/1284-1307](../api-all/app/admin_b2b/service/FormExcelService.php:1095)、[OrderExcelTrait.php:528-548](../api-all/app/api_b2b/trait/OrderExcelTrait.php:528)、[QuoteExcelTrait.php:222](../api-all/app/api_b2b/trait/QuoteExcelTrait.php:222)、[ShipOrderExcelTrait.php:180](../api-all/app/api_b2b/trait/ShipOrderExcelTrait.php:180) |
| **1.11 迁移资产统一 + dump 出库**（C7） | 1 | 大 dump 虽已移出 git，但 `database/backups/` 仍跟踪多份 SQL，`database/migrations` 与 `api-all/database/migrations` 并存。统一迁移资产目录 + `.gitignore` 大 dump。 | §7.10 行1317 / §12.2 行2207 | `database/backups/`、`database/migrations/`、[.gitignore](../.gitignore) |
| **1.12 双库 strict/字符集与樱花站迁移兼容**（C6·⏸） | 2 | 默认库 `utf8mb4_general_ci`+`strict=false`，sakura 库 `utf8_unicode_ci`+`strict=true`；`select id,page groupBy page`、`groupBy(id)` 在 `only_full_group_by` 下可能报错；utf8 不支持部分 emoji。出迁移兼容清单 + 回归脚本。**⏸ 需目标库 `SHOW VARIABLES`/`SHOW CREATE TABLE` 实测。** | §2.7 行288 / §5.7 行784 | [database.php:22/44](../api-all/config/database.php:22)、[LanguageConfigController.php:21](../api-all/app/admin_b2b/controller/LanguageConfigController.php:21)、[admin_pda/ShipOrderController.php:93/393](../api-all/app/admin_pda/controller/ShipOrderController.php:93) |

---

## 4. 第二组 · 购物结算链路与接入安全

> 功能主题：**购物车/报价/FJX/附加项整条结算链路**（越权删购物车、明细归属 IDOR、FJX 后端算费 N+1、FJX iframe 边界），以及平台接入安全（CORS/Origin、账号哈希与会话、Token 与白名单粒度、动作级 RBAC、开放接口、下载 token、分页上限）。P0 锚点：越权删购物车、IDOR 归属收口、CORS 反射、开放接口鉴权。**附加项相关全部集中在本组，不拆分。**

| 单元（原编号） | 权重 | 风险要点（修复边界） | 97 文档索引 | 当前代码位置 |
|:--:|:--:|------|------|------|
| **2.1 报价回调越权删购物车 + 报价支付归属/行锁/整体事务**（A7·P0） | 3 | 报价成功回调 `CartDetail::batchDelData("id", $cart_detail_id_arr, …)` 按裸 ID 删除、无 `user_main_uuid`（**P0 越权**）；`getPayQuoteFee($quote_no_arr)` 算款不带用户；扣减缺整体事务与行锁。删除/扣款补归属 + 行锁 + 单一事务。 | §14.1 行2419 / §14.3 行2490 / §17.1 行2981 | [QuoteService.php:355](../api-all/app/service/b2b/QuoteService.php:355)、[QuoteController.php:223](../api-all/app/api_b2b/controller/QuoteController.php:223) |
| **2.2 购物车/FJX 明细 + 订单/报价/发货归属收口**（A8·P0） | 3 | 部分列表/详情已带 `user_main_uuid`（如 [ShipOrderDetailController.php:62-87](../api-all/app/api_b2b/controller/ShipOrderDetailController.php:62)），但 `cartDetailListTotalFee`、`checkFjxDetail`、`DesignFjx*`、`downShipOrder`、`Preset::detail` 仍按裸 ID/单号。统一 `OwnershipGuard`，所有 `cart_detail_id/quote_detail_id/order_detail_id/preset_id` 补归属。 | §6.1 行866 / §14.2 行2453 / §14.5 行2550 / §10.3 行1826 | [CartQuoteStep2Controller.php:330/505](../api-all/app/api_b2b/controller/CartQuoteStep2Controller.php:330)、[DesignFjxController.php:40-50/260-305](../api-all/app/api_b2b/controller/DesignFjxController.php:40)、[PresetCheckFjxController.php:179](../api-all/app/api_b2b/controller/PresetCheckFjxController.php:179)、[ShipOrderDetailController.php:285-310](../api-all/app/api_b2b/controller/ShipOrderDetailController.php:285) |
| **2.3 FJX 费用后端批量化 + 请求级缓存**（A9） | 3 | 前端已加 300ms debounce（**已完成局部，不再列**），但后端 `getCheckFjxFeeTotal` 按 `cart_detail × check × fjx × user_fjx` 多层循环逐行查库；价格解析无请求级缓存/批量预取。批量取数据、按参数 hash 短 TTL 缓存、加输入数量上限。 | §1.2 行60 / §10.4 行1854 / §18.1 行3181 / §18.2 行3229 | [CartQuoteStep1Controller.php:1174-1297](../api-all/app/api_b2b/controller/CartQuoteStep1Controller.php:1174)、[ServicePricingResolverService.php:188-258](../api-all/app/service/b2b/ServicePricingResolverService.php:188) |
| **2.4 FJX iframe 边界 + 逗号字段 + 控制器全量逻辑剥离**（A10） | 2 | iframe URL 仍带 `userLoginToken`、语言变化 `reload()`、`postMessage` 不校验 `origin`/用 `'*'`；`user_main_uuids like '%..%'` 不走索引；全量修复/迁移逻辑写在用户 Controller。改一次性短 token + 校验 origin、关联表替代逗号 like、迁移逻辑移出用户 API。 | §4.1 行380 / §4.2 行413 / §18.4 行3306 / §18.6 行3374 / §10.3 行1826 | [additionalServices.vue:86/106/168](../user-b2b-view/src/views/user/cart/index/additionalServices.vue:86)、[b2b/index.vue:536/634](../design-fjx-view/src/views/b2b/index.vue:536)、[CartQuoteStep1Controller.php:95](../api-all/app/api_b2b/controller/CartQuoteStep1Controller.php:95) |
| **2.5 CORS / Origin 白名单收口**（B2·P0） | 1 | `Access-Control-Allow-Credentials:true` + `Allow-Origin` 直接回显请求 Origin（api-all/api-open 同）；`OriginMiddleware` 校验仍注释、等于放行。改环境化白名单，凭证态禁止 `*`/反射。 | §2.1 行133 / §9.1 行1527 / §11.6 行2100 | [CorsMiddleware.php:17-18](../api-all/app/middleware/CorsMiddleware.php:17)、[OriginMiddleware.php:13](../api-all/app/middleware/OriginMiddleware.php:13) |
| **2.6 开放接口鉴权与测试入口下线**（B7·P0） | 2 | `api_pub` 无 JWT/签名/防重放、硬编码 token；`/task/test/match-data` 公网测试路由；`api_wms/OpenController` 迁移代码挂白名单。补标准签名(nonce/timestamp/防重放)、下线测试路由、迁移入口收口。 | §6.7 行1014 / §10.6 行1902 / §12.1 行2177 / §12.8 行2370 | [api-open/config/route.php:18](../api-open/config/route.php:18)、`api-open/app/api_pub/controller/*`、[api-open/config/middleware.php:33](../api-open/config/middleware.php:33) |
| **2.7 Token 边界与白名单粒度**（B5） | 2 | `UserAdminMiddleware`/`UserTokenMiddleware` 仍接受 query/body token；白名单仍 controller 级（新增方法易漏）。token 收回 header、白名单细到 action 级。 | §4.2 行413 / §6.2 行895 / §10.2 行1794 | [UserAdminMiddleware.php:23](../api-all/app/middleware/UserAdminMiddleware.php:23)、[UserTokenMiddleware.php:19-31/127](../api-all/app/middleware/UserTokenMiddleware.php:19) |
| **2.8 动作级 RBAC 服务端拦截**（B6） | 3 | 后台权限更像「前端菜单控制」，缺服务端动作级拦截。补统一权限中间件，按 action 校验。 | §9.2 行1554 | （缺失中间件，新增 `admin_b2b` 权限拦截层） |
| **2.9 账号哈希与会话策略**（B3） | 2 | 管理员密码仍 md5；JWT 默认 ~1 年；cookie `httponly=false`。管理员改 `password_hash`+渐进升级，JWT 缩短+刷新，cookie `httponly/secure/samesite`。 | §2.8 行318 / §9.3 行1582 | [admin/LoginController.php:37](../api-all/app/admin/controller/LoginController.php:37)、[JwtService.php:10/74](../api-all/app/service/JwtService.php:10)、[api/LoginController.php:178/250](../api-all/app/api/controller/LoginController.php:178) |
| **2.10 验证码硬化**（B4） | 1 | 万能验证码 `666888` 仅靠 `!=prod` 判定；限流仅 account 维度 180s。去万能码（或严格环境隔离）+ 加 IP/设备维度限流。 | §9.3 行1582 | [VerifyCodeService.php:17/32/56/79](../api-all/app/service/VerifyCodeService.php:17) |
| **2.11 BarCode Context 键统一**（B8） | 1 | 控制器读 `user_main_uuid`，中间件写 `user_login_main_uuid`，键名不一致致用户条码配置大概率失效。统一 Context 键。 | §6.5 行964 | [BarCodeController.php:36](../api-all/app/api_b2b/controller/BarCodeController.php:36) |
| **2.12 下载 token 改 header / 一次性票据**（B13） | 1 | 后台用户导出、订单/报价/发货/质检报告下载把 `token=` 拼进 URL（进历史/代理日志/referer）。改 `Authorization` header 下 blob 或后端短时一次性 download token，旧 query token 灰度期日志即时脱敏。 | §5.5 行729 / §9.5 行1648 | [admin/user/list/index.vue:427-432](../admin-all-view/src/views/admin/user/list/index.vue:427)、[order/detail.vue:2073-2097](../user-b2b-view/src/views/user/purchasing/order/detail.vue:2073)、[quote/detail.vue:1454-1459](../user-b2b-view/src/views/user/purchasing/quote/detail.vue:1454)、[logistics/detail.vue:2508-2514](../user-b2b-view/src/views/user/shipment/logistics/detail.vue:2508) |
| **2.13 分页全局上限 clamp**（C12） | 1 | `executePage()` 只设下限、无最大上限，前端 `limit:99999999/99999/999` 直接放大全表查询；上游 1688/淘宝 `pageSize` 透传无限制（滥用/DoS 面）。后端统一 clamp（后台≤200、前台≤50、上游≤20/40），下拉改专用轻量 options 接口。 | §2.3 行182 / §5.6 行755 / §7.9 行1295 / §10.5 行1879 / §16.7 行2933 | [admin/BaseController.php:9-17](../api-all/app/admin/controller/BaseController.php:9)、[billOfParcels/index.vue:420](../admin-all-view/src/views/b2b/logistics/billOfParcels/index.vue:420)、[api_ali/BaseService.php:33-43](../api-all/app/api_ali/service/BaseService.php:33) |

---

## 5. 第三组 · 数据与性能基础设施

> 功能主题：日期分表与运行时 DDL、月表治理、Redis 清理与首页缓存、商品详情写库、仓储入库/发货 N+1，以及上传策略、外部抓取（SSRF/IO）、前端构建瘦身。P0 锚点：运行时建表 DDL、聊天分表月份 bug、仓储入库全量取数。

| 单元（原编号） | 权重 | 风险要点（修复边界） | 97 文档索引 | 当前代码位置 |
|:--:|:--:|------|------|------|
| **3.1 移除运行时建表（ProductDetail 写路径 DDL）**（C1·P0） | 3 | `ProductDetail` 的 `insertData/insertDataGetId/updateData` 每次都 `ensureTableExists()`（`CREATE TABLE LIKE`），业务请求链路内跑 DDL。改部署期/定时建表 + registry，写路径不再 DDL。 | §15.2 行2653 / §19.1 行3437 | [ProductDetail.php:26-45](../api-all/app/model/ProductDetail.php:26)、[ProductDetail.php:97/111/126](../api-all/app/model/ProductDetail.php:97) |
| **3.2 聊天分表月份后缀 bug + 请求内 hasTable 循环**（C3·P0） | 2 | `DbService::suffixYearMonth` 用整数递减（`for $i=202506;$i>=202410;$i--`），生成 `202500/202499/202413` 等无效月份；`receive/top/delete/read` 仍循环后缀并反复 `hasTable()`。改正确按月回溯（`date('Ym',strtotime(-N month))`）+ registry 去 `hasTable`。 | §15.1 行2615 / §19.2 行3475 | [DbService.php:18-22](../api-all/app/service/DbService.php:18)、[MessageController.php:196-238](../api-all/app/chat/controller/MessageController.php:196) |
| **3.3 仓储入库分页/批量/CAST/截断 + 后台与 PDA 共用服务**（C10·P0） | 3 | 入库列表 `limit:99999999` 全量 `->get()`、不分页；大箱/小箱 `limit(100)` 截断；`CAST(send_qty AS UNSIGNED)<CAST(...)` 索引失效；循环逐行查库；后台(688 行)与 PDA(2021 行)重复实现。抽箱树/库存聚合共用服务，分页+批量聚合，数量字段改数值或加冗余可索引列。 | §1.3 行97 / §2.5 行233 / §16.1 行2757 / §16.2 行2794 | [admin_b2b/KuStockInLogController.php:93](../api-all/app/admin_b2b/controller/KuStockInLogController.php:93)(CAST)、:219(全量`->get()`)、:501(`limit(100)`)；[KuStockInLogService.php](../api-all/app/admin_b2b/service/KuStockInLogService.php)、[admin_pda/KuStockInLogController.php:484/815](../api-all/app/admin_pda/controller/KuStockInLogController.php:484)、[bePutInStorage/index.vue:364](../admin-all-view/src/views/b2b/depository/bePutInStorage/index.vue:364) |
| **3.4 仓储两级箱模型 + 发货列表 N+1 + PDA 正品子查询**（C11） | 3 | 箱/包裹固定两级字段，超两级持续复杂；发货列表逐单查箱数/物流/会员等级（N+1），用户端发货详情一次拉 10000 箱并逐箱查破箱；PDA 正品列表用相关子查询取 `MAX(created_at)` 排序筛选。聚合 count + 批量取物流/会员，箱列表分页/懒加载，正品改连表/冗余列。 | §2.6 行263 / §6.3 行920 / §16.3 行2818 / §16.5 行2879 | [admin_b2b/ShipOrderService.php:36](../api-all/app/admin_b2b/service/ShipOrderService.php:36)、[ShipOrderDetailController.php:164](../api-all/app/api_b2b/controller/ShipOrderDetailController.php:164)、[OperationalGenuineController.php:211/231-242](../api-all/app/admin_pda/controller/OperationalGenuineController.php:211) |
| **3.5 商品详情每次写库治理**（C2） | 2 | 1688/淘宝商品详情每次访问都写 `product_detail_YYYYMM` 和 `product_index`；前端 `cache:'0'` 强制不走缓存反而放大每次写库。改写库去重/异步、去掉强制刷新。 | §8.1 行1340 / §17.2 行3025 | [api_ali/ProductController.php:195-268](../api-all/app/api_ali/controller/ProductController.php:195)、[Alibaba/detail/index.vue:1375](../user-b2b-view/src/views/Alibaba/detail/index.vue:1375) |
| **3.6 Redis 清理全面 SCAN/UNLINK + 版本化**（C8） | 2 | 仅 `listKeys()`（调试用）改了 SCAN；生产 `flush()` 仍 `Redis::keys()`；`MemberIntroCacheService/SiteLocaleCacheService/IndexCacheTask` 同。全部改 SCAN/UNLINK 或 key 版本切换 + 后台异步清旧 key。 | §2.4 行207 / §8.5 行1436 | [B2bIndexCacheService.php:100](../api-all/app/api_b2b/service/B2bIndexCacheService.php:100)、[MemberIntroCacheService.php:104-118](../api-all/app/api_b2b/service/MemberIntroCacheService.php:104)、[SiteLocaleCacheService.php:380-390](../api-all/app/service/SiteLocaleCacheService.php:380)、[IndexCacheTask.php:55-62](../api-all/app/task/IndexCacheTask.php:55) |
| **3.7 首页冷窗口 + 首屏串行 + 预热并发/多实例锁**（C9） | 2 | 6:00 flush / 6:05 预热的「先删后建」冷窗口；首屏仍 `await getConfig()→moduleHotSale()` 串行；预热串行 HTTP 回打自身、无并发上限/多实例互斥/版本化。改先建后切、首屏并行、预热并发受控 + 分布式锁。 | §1.1 行27 / §7.7 行1252 / §11.1 行1974 / §12.6 行2318 / §17.4 行3103 | [index/index.vue:1204-1208](../user-b2b-view/src/views/index/index.vue:1204)、[B2bIndexCacheTask.php:29-76](../api-all/app/task/B2bIndexCacheTask.php:29)、[process/Task.php:90-95](../api-all/process/Task.php:90) |
| **3.8 月表索引补齐 + DDL 收敛**（C4） | 1 | 日志/商品详情月表仅主键、无常用查询索引；月表 DDL 手写在应用代码、多处漂移。补查询索引 + 统一迁移脚本。 | §8.8 行1505 / §12.3 行2238 / §19.3 行3519 | [CreateTableTask.php:37/67/97/129/182](../api-all/app/task/CreateTableTask.php:37) |
| **3.9 动态表名合法性校验**（C5） | 1 | 动态表名后缀来自请求、缺统一合法性校验。加白名单/正则校验，拒非法后缀。 | §16.4 行2853 | [KuStockInLogController.php](../api-all/app/admin_b2b/controller/KuStockInLogController.php)、[DbService.php:18](../api-all/app/service/DbService.php:18) |
| **3.10 上传统一策略 UploadPolicy**（B10） | 2 | 仅用户端 `api/UploadController` 有扩展名+MIME+魔数校验（已完成局部）；admin/chat/index/api-open 仍主要限大小、按上传扩展名落文件；`UploadService::filePathDir` 路径未规范化（`..`/反斜杠）。建统一 `UploadPolicy`（大小/扩展名/MIME/local 开关），服务层二次校验，公开上传加验证码/频控。 | §5.1 行621 / §10.2 行1794 | [admin/UploadController.php:22-43](../api-all/app/admin/controller/UploadController.php:22)、[chat/UploadController.php:30-44](../api-all/app/chat/controller/UploadController.php:30)、[index/UploadController.php](../api-all/app/index/controller/UploadController.php)、[UploadService.php:21](../api-all/app/service/UploadService.php:21) |
| **3.11 外部抓取 SSRF / TLS 收口**（B11） | 2 | `imageSearch`/`getImageId`/洗水唛对用户可控 URL 直接 `file_get_contents`+base64 常驻内存；OCR `file_get_contents` 任意 URL；汇率/支付 cURL 关闭 SSL 校验。建统一 `RemoteFetcher`（仅 http/https、拒内网 IP、限 Content-Length/总字节、connect/read 超时），恢复 TLS 校验。 | §5.2 行654 / §6.8 行1043 / §10.7 行1929 | [api_ali/ProductController.php:119-145](../api-all/app/api_ali/controller/ProductController.php:119)、[tb/ProductService.php:47-65](../api-all/app/service/tb/ProductService.php:47)、[WashLabelTrait.php:351](../api-all/app/api_b2b/trait/WashLabelTrait.php:351)、[ocr_handler.php:43](../api-open/app/api_wms/view/ocr_handler.php:43)、[SmbcRateFetcher.php:167-178](../api-all/app/service/SmbcRateFetcher.php:167) |
| **3.12 前端构建瘦身 + WMS 收口**（C13） | 2 | 各前端无统一 `drop_console/drop_debugger`、生产残留 `console.log`；全量引入 ElementPlus/图标；`pxtoviewport` 对字体也转 `vw`（布局不稳）；WMS 统一 30s 超时、manifest 权限过宽、`apiSecret:'123'` 硬编码。统一构建瘦身 + WMS 超时分级 + 权限最小化 + 移除硬编码 secret。 | §4.9 行592 / §5.9 行841 / §6.6 行983 / §6.10 行1091 / §9.7 行1723 / §12.5 行2290 | [user-b2b-view/vite.config.js:122](../user-b2b-view/vite.config.js:122)、[design-fjx-view/vite.config.ts:95-114](../design-fjx-view/vite.config.ts:95)、[intrduce/nuxt.config.ts:89-90](../frontend-all-view/apps/intrduce/nuxt.config.ts:89)、`global-wms/utils/request.js:28`、`global-wms/manifest.json:32-51` |

---

## 6. 需环境/数据库确认（已折入各组单元，集中提示）

| # | 事项 | 所属单元 | 需确认方式 |
|:--:|------|:--:|------|
| Z1 | `payment_orders.request_id` 唯一索引是否真实存在 | 1.2 | 线上/迁移库 `SHOW INDEX FROM payment_orders`（迁移资产未体现） |
| Z2 | 樱花站迁移兼容（sql_mode/字符集/JSON/CAST） | 1.12 | 目标库 `SHOW VARIABLES`、`SHOW CREATE TABLE`、JSON/groupBy 回归 |
| Z3 | 队列失败重试运行态 | 1.7 | 死信表、失败堆积量、重试日志 |

---

## 7. 建议执行顺序（每组先啃自己的 P0）

三组可并行，各自先做组内 P0，再做支撑项：

- **第一组**：1.5 运费 bug → 1.1 支付幂等 + 1.4 BalanceService → 1.2/1.3 支付归属与充值入账 → 1.7 队列补偿；再 1.8/1.9 配置与脱敏、1.10/1.11/1.12 导出与迁移。
- **第二组**：2.1 越权删购物车 → 2.2 IDOR 归属收口 → 2.5 CORS + 2.6 开放接口鉴权（含测试路由/OCR）→ 2.3 FJX 后端算费 + 2.4 FJX iframe 边界 → 2.7 token / 2.8 RBAC；再 2.9~2.13。
- **第三组**：3.1 运行时 DDL + 3.2 聊天分表 bug（避免请求链路 DDL/无效月表）→ 3.3 仓储入库共用服务 → 3.6 Redis SCAN → 3.7 首页；再 3.4/3.5/3.8~3.12。

> 跨组依赖少；若人手紧张，先做三组各自的「P0 行」（共 11 条），即可覆盖资金一致性、越权/鉴权、运行时 DDL 三大上线阻塞面。

---

## 8. 范围与口径

- 三组覆盖「部分完成 + 未完成 + 需环境确认」全部条目；§1 的 7 项已完成项已移除，不重复分工。所有单元保留原模块编号（A/B/C）以回溯来源。
- **FJX/附加项整条结算链路（越权删购物车 2.1、明细归属 2.2、后端算费 2.3、iframe 边界 2.4）集中在第二组，不拆分。**
- 每条给①97 文档章节+行号 ②当前代码 `路径:行号`。原文行号漂移处（运费 bug §4.6 标 :272 实为 :306、单号 helper 实为 `api-all/app/helper.php`、入库全量 `->get()` 实为 :219、`limit` 实为 :364）已按当前代码补正。
- 工时权重为相对估值（1/2/3），用于三组横向比对，非精确工时；三组权重和 23/25/25、P0 数 4/4/3，已尽量拉平。
- ⏸ 三项标注需连库/线上环境，分别折入 1.2/1.7/1.12，不以代码强行定论。
- 子项目 `api-all / api-open / admin-all-view / user-b2b-view / design-fjx-view / global-wms / docker / database` 均存在于工作区；引用即真实代码。
