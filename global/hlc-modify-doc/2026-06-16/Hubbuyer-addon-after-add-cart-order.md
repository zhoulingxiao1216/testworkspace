# 变更日志

- 日期：2026-06-16
- 修改文件：全球站巡检脚本/hubbuyer/core/batch_checker.py
- 修改类型：修改
- 描述：将 B2B 附加项检查移回加购之后，修复购物车为空

## 变更摘要

### 变更点 1：巡检执行顺序
- 变更原因：B2B 附加项依赖购物车已有商品，须在 add_cart 之后执行
- 变更方式：`add_cart.json` 排在 `B2B_Addon.json` 之前；保留 B2B_Addon 的 90s runner_timeout
