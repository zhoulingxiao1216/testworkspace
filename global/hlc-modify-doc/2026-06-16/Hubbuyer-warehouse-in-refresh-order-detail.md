# 变更日志

- 日期：2026-06-16
- 修改文件：全球站巡检脚本/hubbuyer/checker/api/purchase_order_ops.py
- 修改类型：修复
- 描述：入库前刷新订单明细，修复待入库数误判为 0 导致未调用 putInStock

## 变更摘要

### 变更点 1：入库前重新拉取 orderDetail/list
- 变更原因：一键正品后 genuine_qty 已更新，但入库仍使用流程开始时缓存的 seller 数据
- 变更方式：warehouse_in 执行前调用 `_refresh_sample_seller` 获取最新 genuine/store

### 变更点 2：待入库=0 时的判定
- 变更原因：未调用 API 却报 OK(已入库) 与后台入库数仍为 0 不一致
- 变更方式：若 `is_store_incomplete=1` 且待入库=0 则 FAIL；真正无待入库则 OK(已全部入库)
