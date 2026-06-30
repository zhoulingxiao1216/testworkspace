# 变更日志

- 日期：2026-06-16
- 修改文件：全球站巡检脚本/hubbuyer/config/data/purchase_order_ops.json
- 修改类型：修改
- 描述：启用一键到货 oneClickArrive 检查步骤

## 变更摘要

### 变更点 1：one_click_arrival
- 变更原因：用户提供一键到货 curl
- 变更方式：接入 `/admin_b2b/orderDetailUpdate/oneClickArrive`，payload 与一键采购一致；支持 code=40000 到货幂等
