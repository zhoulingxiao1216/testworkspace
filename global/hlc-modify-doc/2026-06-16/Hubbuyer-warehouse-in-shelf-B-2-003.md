# 变更日志

- 日期：2026-06-16
- 修改文件：全球站巡检脚本/hubbuyer/config/data/purchase_order_ops.json
- 修改类型：修改
- 描述：默认入库库位由 B-1-001(35) 改为 B-2-003(69)

## 变更摘要

### 变更点 1：ku_shelves_ku_id 默认值
- 变更原因：main 环境 B-1-001(id=35) 调用 putInStock 报 bcmul(null)，手动选 B-2-003 入库成功
- 变更方式：default_ku_shelves_ku_id 与 warehouse_in.ku_shelves_ku_id 改为 69(B-2-003)
