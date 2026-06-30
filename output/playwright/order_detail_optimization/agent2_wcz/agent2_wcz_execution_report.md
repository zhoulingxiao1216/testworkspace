# Agent2 WCZ 代购订单详情测试执行报告

执行时间：2026-05-23T03:25:42.995Z

## 环境声明

- 本轮目标后台固定为：`https://test-wcz-admin.hubbuyer.com`
- 上一轮 `wlz-admin-all-view.hubbuyer.com` 结果已被目标环境纠正，本轮不作为判定依据。
- 本报告不记录明文密码、Token、Cookie。

## 登录与路径

- 尝试入口：`https://test-wcz-admin.hubbuyer.com/login`
- 尝试路径：`https://test-wcz-admin.hubbuyer.com/b2b/order/agentBuy`、`https://test-wcz-admin.hubbuyer.com/b2b/order/agentBuy/detail`
- 本轮可登录账号标识：`admin` (account markdown)
- 本轮详情页识别订单号：`B2B-DD-KOR8-260520-122`

## 执行结果汇总

- Pass：4
- Fail：2
- Blocked：11

| 用例 | 状态 | 结论 |
| --- | --- | --- |
| TC-OD-FLT-001 | Pass | 订单详情页可见商品 ID、商品状态、采购状态、质检状态四类商品级筛选入口。 |
| TC-OD-FLT-002 | Pass | 商品状态、采购状态、质检状态下拉选项包含用例要求的全部选项。 |
| TC-OD-FLT-003 | Fail | 部分商品 ID/SKU DD-KOR8-2 查询后仍识别到完整商品 DD-KOR8-260520-122，疑似模糊命中。 |
| TC-OD-FLT-004 | Pass | 不存在商品 ID 与脚本字符输入后页面未白屏、未触发浏览器弹窗。 |
| TC-OD-FLT-005 | Blocked | 待入库筛选可操作并已留证，但当前自动化无法从页面稳定提取正品数量、已入库数量、发货数量完成规则级断言，需准备/标注覆盖数据后复核。 |
| TC-OD-FLT-006 | Blocked | 部分入库筛选可操作并已留证，但当前自动化无法从页面稳定提取正品数量、已入库数量、发货数量完成规则级断言，需准备/标注覆盖数据后复核。 |
| TC-OD-FLT-007 | Blocked | 已入库筛选可操作并已留证，但当前自动化无法从页面稳定提取正品数量、已入库数量、发货数量完成规则级断言，需准备/标注覆盖数据后复核。 |
| TC-OD-FLT-008 | Blocked | 采购状态三类筛选项可选择并已留证，但缺少可核对采购数/到货数/暂不购买状态的数据口径，无法完成规则级通过判定。 |
| TC-OD-FLT-009 | Blocked | 质检状态五类筛选项可选择并已留证，但缺少可核对不良/待定/退货/换货/待检数量的数据口径，无法完成规则级通过判定。 |
| TC-OD-FLT-010 | Blocked | 多条件组合筛选可执行并已留证，但缺少覆盖状态商品数据与接口字段映射，无法验证结果是否严格按交集过滤。 |
| TC-OD-FLT-011 | Pass | 清空/重置、刷新、返回列表并进入另一订单流程可完成，未观察到白屏或路由错误。 |
| TC-OD-FLT-012 | Blocked | 当前订单疑似包含多个店铺信息并已留证，但缺少可核对的多店铺状态覆盖数据，无法判定筛选准确性。 |
| TC-OD-AMT-005 | Fail | 进行中列表展开后未识别到“金额是否确认”筛选字段。 |
| TC-OD-LST-002 | Blocked | 进行中列表识别到购入数相关字段，但未能稳定识别排序按钮/图标，需要人工核对截图。 |
| TC-OD-CB-001 | Blocked | 详情页存在返现与确认相关文案，但未识别到明确二次确认按钮状态，且该需求本身标记为待版本确认，已留证待中控确认。 |
| TC-OD-SEC-003 | Blocked | 已按 1366/1440/1920 宽度采集详情页兼容性截图；由于核心筛选是否存在/状态数据前置未完全满足，本轮不做布局通过判定。 |
| TC-OD-SEC-001 | Blocked | 本轮按中控补充仅使用 admin 登录 WCZ；不同角色权限控制需另行提供采购员/无权限账号后执行。 |

## 发现的缺陷或疑点

- TC-OD-FLT-003：部分商品 ID/SKU DD-KOR8-2 查询后仍识别到完整商品 DD-KOR8-260520-122，疑似模糊命中。
- TC-OD-AMT-005：进行中列表展开后未识别到“金额是否确认”筛选字段。

## 需中控解决的问题

- 数据/版本阻塞：存在用例因筛选控件缺失、缺少覆盖状态数据、缺少采购员账号或需求待版本确认而无法完成规则级判定。

## 主要证据

- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\00_login_initial.png`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\login_attempt_1_admin_success.png`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\11_agent_buy_list_initial.png`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\20_detail_initial.png`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\20_detail_initial.png`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\20_detail_initial.txt`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\21_detail_dropdown_options.png`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\21_detail_dropdown_options.txt`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\23_detail_sku_partial.png`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\23_detail_sku_partial.txt`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\24_detail_sku_none.png`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\25_detail_sku_script.png`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\27_TC-OD-FLT-005__.png`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\27_TC-OD-FLT-005__.txt`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\27_TC-OD-FLT-006__.png`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\27_TC-OD-FLT-006__.txt`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\27_TC-OD-FLT-007__.png`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\27_TC-OD-FLT-007__.txt`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\28_purchase__.png`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\29_qc__.png`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\30_detail_combo_filter.png`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\30_detail_combo_filter.txt`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\26_detail_reset_after_sku.png`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\31_detail_after_reload.png`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\32_list_returned_after_detail.png`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\33_second_detail_after_return.png`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\40_list_expanded_optional.png`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\40_list_expanded_optional.txt`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\41_detail_optional_cashback.png`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\41_detail_optional_cashback.txt`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\50_compat_detail_1366x768.png`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\50_compat_detail_1440x900.png`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\50_compat_detail_1920x1080.png`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\execution_results.json`
- `D:\test_workspace\output\playwright\order_detail_optimization\agent2_wcz\agent2_wcz_execution_report.md`
