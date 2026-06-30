# 变更日志

- 日期：2026-06-15
- 修改文件：全球站压测脚本/Performance/core_stress.py、测试文档/2026-06-15/性能压测结果汇总报告_2026-06-15.md、性能压测结果报告（10min）_2026-06-15.md
- 修改类型：修改
- 描述：定位并写入商品加购_1688 code=500 根因（SKU 缺 price），脚本侧跳过无 price 的 1688 SKU。

## 变更摘要

### 变更点 1：core_stress.py 加购 payload 构建过滤
- 变更原因：部分 1688 商品详情 SKU 无 `price`，后端 `DetailService::getBuyPriceSkuInfo()` 读空 key 返回 code=500。
- 变更方式：`_build_add_cart_payload_from_detail` 对 1688 跳过 `price` 为空的 SKU，尝试下一 SKU/商品。

### 变更点 2：压测报告写入 500 根因
- 变更原因：失败接口需在报告中体现具体错误与责任方。
- 变更方式：汇总报告 v2.2、10min 报告 v1.2 补充根因链、失败样例、后端/脚本修复建议。

## 根因摘要

- 接口：`POST /api_b2b/cart/add1688`
- 错误：`code=500`, `msg=Undefined array key "price"`
- 堆栈：`DetailService.php:234` → `CartController::add1688()`
