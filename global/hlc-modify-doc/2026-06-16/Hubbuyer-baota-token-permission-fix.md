# 变更日志

- 日期：2026-06-16
- 修改文件：全球站巡检脚本/hubbuyer/run.sh、scripts/fix_permissions.sh、checker/api/login.py、core/token_store.py、core/path_manager.py
- 修改类型：修改 / 新增
- 描述：修复宝塔计划任务 token 目录 Permission denied

## 变更摘要

### 变更点 1：run.sh 启动前修复权限
- 变更原因：宝塔 cron 用户与 token 文件属主不一致导致写入失败
- 变更方式：启动前 mkdir/chmod/chown，设置 HUBBUYER_TOKEN_DIR，输出 cron_execution.log

### 变更点 2：login token 落盘容错
- 变更原因：避免 PermissionError 直接 Traceback 中断巡检
- 变更方式：token_store 原子写入 + login 捕获权限错误并写入 message
