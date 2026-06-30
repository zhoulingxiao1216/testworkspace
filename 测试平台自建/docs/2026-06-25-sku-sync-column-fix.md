# SKU 批量同步 — 列识别修复

- 日期：2026-06-25
- 修改文件：`modules/sku_sync.py`、`pages/4_sku_bulk_sync.py`
- 修改类型：修改
- 描述：修复 Excel「贵社SKU」列误识别，并调整预览列含义

## 变更摘要

### 变更点 1：find_sku_column_index
- 变更原因：旧逻辑 `header in alias` 会把右侧「SKU」列或属性列「sku」误当作贵社SKU
- 变更方式：按优先级打分，仅接受「贵社SKU/貴社SKU」（≥80 分），「SKU」列降为低优先级

### 变更点 2：预览表列名
- 变更原因：「当前SKU / Excel贵社SKU」易与后台、Excel 值混淆
- 变更方式：改为「Excel贵社SKU」（文件目标值）与「后台当前SKU」（填主订单号后对比）
