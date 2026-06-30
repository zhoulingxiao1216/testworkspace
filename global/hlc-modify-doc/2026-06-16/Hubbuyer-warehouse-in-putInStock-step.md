# 变更日志

- 日期：2026-06-16
- 修改文件：全球站巡检脚本/hubbuyer/checker/api/purchase_order_ops.py、config/data/purchase_order_ops.json
- 修改类型：修改
- 描述：接入入库 putInStock，动态计算待入库数量

## 变更摘要

### 变更点 1：warehouse_in 独立 payload
- 变更原因：入库接口为 KuStockInLog/putInStock，结构与一键操作不同
- 变更方式：ku_stock_in_log_data 由 genuine_qty - store_qty 动态生成 quantity；ku_shelves_ku_id 默认 35(B-1-001)

### 变更点 2：待入库为 0 时幂等通过
- 变更原因：重复巡检时商品可能已全部入库
- 变更方式：待入库=0 记 OK(已入库|待入库=0)，不调用接口
