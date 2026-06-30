# SKU 批量同步 — 自动预览后台当前 SKU

- 日期：2026-06-25
- 修改文件：`modules/sku_sync.py`、`modules/sakura_client.py`、`pages/4_sku_bulk_sync.py`
- 修改类型：修改
- 描述：从 Excel 注文番号列自动拉取后台 SKU 用于预览对比

## 变更摘要

### 变更点 1：解析注文番号列
- 变更原因：未手动填主订单号时不会请求订单详情，后台当前 SKU 始终为 —
- 变更方式：识别「注文番号」列写入 `main_order_id`，预览时自动拉取

### 变更点 2：订单详情 API 校验
- 变更原因：API 返回非 200 时仍当作成功，导致 mapping 为空
- 变更方式：`fetch_order_items` 校验 `status==200` 并返回错误信息

### 变更点 3：商品番号匹配
- 变更原因：API 返回数字型 order_id 与 Excel 字符串不一致
- 变更方式：统一用 `_normalize_cell` 规范化后再匹配
