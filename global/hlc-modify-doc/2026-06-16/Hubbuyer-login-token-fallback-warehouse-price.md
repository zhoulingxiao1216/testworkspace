# 变更日志

- 日期：2026-06-16
- 修改文件：hubbuyer/checker/api/login.py、purchase_order_ops.py、config/data/purchase_order_ops.json
- 修改类型：修改
- 描述：修复登录 token_store 缺失与入库 bcmul 异常

## 变更摘要

### 变更点 1：login 兼容未部署 token_store
- 变更原因：服务器缺少 core/token_store.py 导致 ModuleNotFoundError
- 变更方式：ImportError 时内联 fallback 写入逻辑

### 变更点 2：入库前校验单价并优先 1688 店铺
- 变更原因：淘宝明细缺单价触发后端 bcmul(null) 返回 40000
- 变更方式：跳过无单价明细、入库前跨店铺重选、sample_mode 改为 first_by_platform
