# 变更日志

- 日期：2026-06-15
- 修改文件：全球站压测脚本/Performance/core_stress.py、全球站压测脚本/Performance/config/settings.py
- 修改类型：修改
- 描述：补全浏览加购下单链路的报价 Step1/Step2 与附加项接口

## 变更摘要

### 变更点 1：完整报价链路
- 变更原因：原压测下单链路跳过附加项与 cartQuoteStep1/Step2，与真实浏览器流程不一致
- 变更方式：在 `run_browse_add_cart_submit_order` 中于 `quote/create` 前串联 `getCheckFjxList`、`updateCheckFjx`、`getCheckFjxFeeTotal`、Step1/Step2 `cartDetailList` 及费用合计接口

### 变更点 2：环境与开关
- 变更原因：FJX 附加项接口使用独立站点与 `userlogintoken` 鉴权
- 变更方式：新增 `FJX_SITE_URL`、`STRESS_ENABLE_FULL_QUOTE_FLOW` 及 Step1/Step2 endpoint 映射；完整链路下 `quote/create` 默认 `quote_type=2`、`logistics_config_id=28`
