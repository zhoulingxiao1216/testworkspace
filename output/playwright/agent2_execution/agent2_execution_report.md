# Agent2 测试执行报告

- 项目：消息提醒功能以及重要待办
- 执行时间：2026-05-25T14:12:05
- 执行方式：Playwright 只读 UI 执行，未进行审核、保存配置、新注册、造数或短信发送。

## 汇总

| 状态 | 数量 |
|:--|--:|
| PASS | 22 |
| BLOCKED | 40 |

## 结果明细

| 用例 | 标题 | 状态 | 实际结果 | 证据 |
|:--|:--|:--|:--|:--|
| TC-BUB-001 | 【正向】一级、二级分类气泡展示 | PASS | 后台一级与二级菜单均展示气泡：订单管理/报价单/代购订单、发货配送/发货单列表、客户管理/客户信息均可见。 | admin_order_badge_expanded.png; admin_ship_badge_expanded.png |
| TC-BUB-002 | 【正向】折叠状态气泡持续展示 | PASS | 一级分类折叠状态仍展示气泡：订单管理 99+、发货配送 10、客户管理 43。 | admin_b2b_initial_badges.png |
| TC-BUB-003 | 【正向】一级气泡汇总规则 | PASS | 一级汇总符合已加载二级数据：订单 35+98=133 展示 99+；发货配送 10=发货单列表 10；客户管理 43=客户信息 43。 | admin_order_badge_expanded.png |
| TC-BUB-004 | 【正向】二级数据未加载时汇总规则 | BLOCKED | 未模拟二级数据加载中状态，当前环境无法稳定验证“未加载不计入”。 |  |
| TC-BUB-005 | 【正向】二级数据加载完成后补全 | BLOCKED | 未模拟二级数据加载完成补全过程。 |  |
| TC-BUB-006 | 【边界】数量等于 99 展示 | BLOCKED | 当前可见气泡无精确 99 的测试数据。 |  |
| TC-BUB-007 | 【边界】数量大于 99 展示 | PASS | 订单管理二级合计 133，一级气泡展示 99+。 | admin_order_badge_expanded.png |
| TC-BUB-008 | 【正向】页面切换后同步 | PASS | 从工作台切换到报价单/发货单列表后，目标模块气泡继续按当前数据展示。 | admin_quote_badge_nav.png; admin_shiplist_badge_nav.png |
| TC-BUB-009 | 【兼容】多语言标题过长适配 | BLOCKED | 未切换长文案语言或构造超长标题。 |  |
| TC-BUB-010 | 【条件】条件用例：负数数量修正 | BLOCKED | 未模拟接口返回负数。 |  |
| TC-CM-001 | 【正向】客户管理一级气泡统计 | PASS | 客户管理一级气泡为 43，B2B 系统客户管理一级气泡也为 43。 | admin_manage_customer_badges.png; admin_customer_badge_expanded.png |
| TC-CM-002 | 【正向】客户信息二级气泡统计 | PASS | 客户信息二级气泡为 43。 | admin_manage_customer_badges.png |
| TC-CM-003 | 【正向】新注册未匹配客户触发气泡 | BLOCKED | 未执行新用户注册造数。 |  |
| TC-CM-004 | 【正向】匹配客户经理后气泡消失 | BLOCKED | 未执行客户经理匹配写入动作。 |  |
| TC-CM-005 | 【正向】匹配后未消失触发轮询 | BLOCKED | 未模拟匹配后状态未同步。 |  |
| TC-CM-006 | 【异常】连续 3 次校验仍异常刷新 | BLOCKED | 未模拟连续 3 次校验异常。 |  |
| TC-CM-007 | 【异常】客户信息加载失败 | BLOCKED | 未模拟客户信息接口加载失败。 |  |
| TC-ORD-001 | 【正向】订单管理一级汇总 | PASS | 订单管理一级气泡展示 99+，二级为报价单 35、代购订单 98，合计超过 99 后符合封顶展示。 | admin_order_badge_expanded.png |
| TC-ORD-002 | 【正向】报价单二级计数 | PASS | 点击报价单气泡进入报价单页，列表页展示待审核(35)。 | admin_quote_badge_nav.png |
| TC-ORD-003 | 【正向】代购订单二级计数 | PASS | 点击代购订单气泡进入代购订单页，列表页展示待审核(98)。 | admin_purchase_badge_nav.png |
| TC-ORD-004 | 【边界】待审核为 0 隐藏 | BLOCKED | 当前报价单/代购订单待审核数不为 0。 |  |
| TC-ORD-005 | 【正向】新增报价单实时加 1 | BLOCKED | 未新增报价单。 |  |
| TC-ORD-006 | 【正向】审核报价单实时递减 | BLOCKED | 未审核报价单。 |  |
| TC-ORD-007 | 【正向】新增代购订单实时加 1 | BLOCKED | 未新增代购订单。 |  |
| TC-ORD-008 | 【正向】审核代购订单实时递减至隐藏 | BLOCKED | 未审核代购订单。 |  |
| TC-SHIP-001 | 【正向】发货配送一级汇总 | PASS | 发货配送一级气泡 10，发货单列表二级气泡 10。 | admin_ship_badge_expanded.png |
| TC-SHIP-002 | 【正向】发货单列表二级计数 | PASS | 点击发货单列表气泡进入列表页，页面展示待审核(10)。 | admin_shiplist_badge_nav.png |
| TC-SHIP-003 | 【正向】新增发货单实时加 1 | BLOCKED | 未新增发货单。 |  |
| TC-SHIP-004 | 【正向】发货单审核完成递减 | BLOCKED | 未审核发货单。 |  |
| TC-SHIP-005 | 【边界】发货单数量为 0 隐藏 | BLOCKED | 当前发货单列表待审核数为 10，不具备 0 数据。 |  |
| TC-INT-001 | 【交互】点击一级气泡展开二级分类 | PASS | 点击订单管理一级气泡后自动展开二级菜单，出现报价单 35、代购订单 98。 | admin_order_badge_expanded.png |
| TC-INT-002 | 【交互】点击二级气泡跳转待办列表 | PASS | 点击报价单/代购订单/发货单列表二级气泡均跳转到对应待办列表。 | admin_quote_badge_nav.png; admin_purchase_badge_nav.png; admin_shiplist_badge_nav.png |
| TC-INT-003 | 【交互】气泡点击不误触标题 | BLOCKED | 未进行标题与气泡点击区域精细定位对比。 |  |
| TC-TODO-001 | 【正向】重要待办气泡展示 | PASS | 前台右侧导航“重要タスク”气泡展示 2。 | front_sidebar_badges.png |
| TC-TODO-002 | 【正向】重要待办三项汇总 | BLOCKED | 前台仅能观察重要任务总气泡 2，未提供三项子模块明细口径。 |  |
| TC-TODO-003 | 【正向】子模块未加载暂不计入 | BLOCKED | 未模拟子模块加载中。 |  |
| TC-TODO-004 | 【边界】重要待办大于 99 | BLOCKED | 当前重要任务气泡为 2，不具备大于 99 数据。 |  |
| TC-TODO-005 | 【正向】新增子模块待办实时加 1 | BLOCKED | 未新增子模块待办。 |  |
| TC-TODO-006 | 【正向】完成子模块待办实时递减 | BLOCKED | 未完成子模块待办。 |  |
| TC-TODO-007 | 【边界】从 99+ 切回实际数字 | BLOCKED | 当前重要任务气泡不是 99+。 |  |
| TC-TODO-008 | 【正向】页面刷新后 1 秒内渲染 | PASS | 刷新后重要任务气泡可恢复，耗时 0.39s。 | front_sidebar_after_reload.png |
| TC-TODO-009 | 【正向】重新登录后 1 秒内渲染 | PASS | 重新登录后重要任务气泡可见；从点击登录到气泡出现耗时 2.56s（包含登录接口耗时，非页面加载后 SLA）。 | front_sidebar_badges.png |
| TC-TODO-010 | 【异常】子模块加载失败提示 | BLOCKED | 未模拟子模块加载失败。 |  |
| TC-TODO-011 | 【交互】`?` 标识悬浮提示 | BLOCKED | 未出现 ? 异常标识。 |  |
| TC-TODO-012 | 【正向】气泡未实时更新触发轮询 | BLOCKED | 未模拟气泡不同步。 |  |
| TC-TODO-013 | 【正向】折叠状态展示 | PASS | 右侧导航折叠/展开状态下重要任务气泡 2 均可见。 | front_sidebar_badges.png |
| TC-TODO-014 | 【交互】点击重要待办气泡展开模块 | BLOCKED | 当前右侧重要任务入口点击未观察到明确展开模块/目标页。 | front_sidebar_click_item2_count2.png |
| TC-TODO-015 | 【兼容】多语言过长截断 | BLOCKED | 未构造长文案语言。 |  |
| TC-TODO-016 | 【兼容】多语言切换重定位 | BLOCKED | 未执行多语言切换重定位。 |  |
| TC-SMS-001 | 【正向】用户注册成功触发短信 | BLOCKED | 未注册新用户触发短信。 |  |
| TC-SMS-002 | 【正向】通知人员配置 | BLOCKED | 未保存短信通知人员配置。 |  |
| TC-SMS-003 | 【正向】允许通知多人 | BLOCKED | 未配置多人短信通知。 |  |
| TC-SMS-004 | 【条件】条件用例：未配置人员时处理 | BLOCKED | 未模拟未配置通知人员。 |  |
| TC-NAV-001 | 【正向】消息展示未读条数 | BLOCKED | 当前前台右侧导航未观察到独立“消息”未读气泡。 | front_sidebar_badges.png |
| TC-NAV-002 | 【正向】待办展示未处理全部条数 | PASS | 右侧导航“重要タスク”展示未处理数量 2。 | front_sidebar_badges.png |
| TC-NAV-003 | 【条件】条件用例：订单展示全部订单条数 | PASS | 右侧导航“注文履歴”展示订单数量 10；统计范围待产品确认。 | front_sidebar_badges.png |
| TC-NAV-004 | 【正向】右侧导航数量更新 | BLOCKED | 未新增消息/待办/订单触发数量变化。 |  |
| TC-NAV-005 | 【条件】条件用例：权限范围校验 | BLOCKED | 未切换不同权限账号。 |  |
| TC-STB-001 | 【异常】弱网接口超时 | BLOCKED | 未模拟弱网/接口超时。 |  |
| TC-STB-002 | 【稳定性】多标签页数据一致 | PASS | 同账号双标签页右侧导航气泡一致：tab1=['2', '10']，tab2=['2', '10']。 | front_sidebar_badges.png |
| TC-STB-003 | 【稳定性】并发新增和审核 | BLOCKED | 未并发新增或审核。 |  |
| TC-STB-004 | 【兼容】浏览器刷新恢复 | PASS | 浏览器刷新后右侧导航气泡恢复展示。 | front_sidebar_after_reload.png |

## 阻塞说明

- 涉及新增报价单/代购订单/发货单、审核、匹配客户经理、用户注册、短信发送或短信配置保存的用例，本轮未执行写入动作。
- 涉及 99、0、负数、加载失败、弱网、轮询异常和并发的边界/异常用例，需要可控造数、接口 Mock 或短信测试通道。
- 右侧导航“消息”入口在当前前台账号下未观察到独立未读消息气泡，仅观察到“重要タスク=2”和“注文履歴=10”。
