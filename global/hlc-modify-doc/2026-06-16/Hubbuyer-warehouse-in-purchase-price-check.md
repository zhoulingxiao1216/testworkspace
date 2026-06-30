# 变更日志

- 日期：2026-06-16
- 修改文件：全球站巡检脚本/hubbuyer/checker/api/purchase_order_ops.py
- 修改类型：修改
- 描述：入库校验采购价字段并多明细重试，规避 bcmul(null)

## 变更摘要

### 变更点 1：入库采购价校验
- 变更原因：明细存在 price 但 change_price/purchase_price 为空时，putInStock 仍报 bcmul(null)
- 变更方式：仅认采购价字段；缺价时 SKIP；bcmul 失败时尝试其他明细/店铺
