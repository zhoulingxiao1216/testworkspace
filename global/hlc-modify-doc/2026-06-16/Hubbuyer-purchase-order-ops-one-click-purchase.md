# 变更日志

- 日期：2026-06-16
- 修改文件：全球站巡检脚本/hubbuyer/checker/api/purchase_order_ops.py、config/data/purchase_order_ops.json、config/rules/purchase_order_ops.json、config/settings.py、core/batch_checker.py、core/notifier.py
- 修改类型：新增
- 描述：新增后台代购订单操作检查点，接入一键采购 curl

## 变更摘要

### 变更点 1：purchase_order_ops 检查点
- 变更原因：代购订单审核后需继续验证一键采购等后台操作
- 变更方式：动态读取本轮 DD 单号；调用 orderDetail/list 解析 seller_open_id 与 order_detail_ids；按首店抽样执行 oneClickPurchase

### 变更点 2：幂等与后续步骤占位
- 变更原因：重复巡检时商品行可能已采购
- 变更方式：code=40000 且 message 含「已采购」记为 OK；一键到货/正品/入库待补 curl 后启用
