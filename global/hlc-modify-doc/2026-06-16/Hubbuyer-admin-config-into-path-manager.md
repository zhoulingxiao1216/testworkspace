# 变更日志

- 日期：2026-06-16
- 修改文件：全球站巡检脚本/hubbuyer/core/path_manager.py、checker/api/purchase_order_*.py
- 修改类型：修改
- 描述：admin_config 逻辑并入 path_manager，避免服务器漏同步新模块

## 变更摘要

### 变更点 1：后台 URL 解析迁入 path_manager
- 变更原因：服务器未部署 core/admin_config.py 导致 ModuleNotFoundError
- 变更方式：实现放在始终存在的 path_manager.py；admin_config.py 仅作 re-export
