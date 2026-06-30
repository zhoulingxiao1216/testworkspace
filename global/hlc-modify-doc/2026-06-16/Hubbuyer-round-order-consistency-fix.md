# 变更日志

- 日期：2026-06-16
- 修改文件：全球站巡检脚本/hubbuyer/checker/api/quote_order_store.py、checker/api/purchase_order_audit.py、core/batch_checker.py、core/runner.py、config/rules/B2B_Addon.json、config/data/purchase_order_audit.json
- 修改类型：修改
- 描述：修复代购订单号误用历史单号，并加强单号一致性与附加项执行配置

## 变更摘要

### 变更点 1：get_round_paid_order 去掉历史兜底
- 变更原因：上游报价审核/支付失败时，不应回退到 `B2B_order_latest` 误审旧单
- 变更方式：仅返回 `B2B_round_order`，为空则代购审核失败

### 变更点 2：代购订单审核单号一致性校验
- 变更原因：排除 BJ→DD 前缀差异后，仍须保证后缀与本轮提交报价单一致
- 变更方式：新增 `validate_round_order_matches_quote`；`auto_resolve_order_no` 模式下不再回退硬编码单号；请求体强制使用动态 `order_no`

### 变更点 3：B2B 附加项提前执行并延长超时
- 变更原因：附加项接口响应慢，且属于报价链路前置步骤
- 变更方式：执行顺序调整为 login 后第一时间检查；`runner_timeout` 设为 90s，runner 支持任务级超时
