# 变更日志

- 日期：2026-06-16
- 修改文件：安全优化/测试文档/accounts_main.yaml、Agent2_环境交接_main.yaml
- 修改类型：修改
- 描述：补充 main 环境管理员账号 admin

## 变更摘要

### 变更点 1：accounts_main.yaml
- 变更原因：增加后台鉴权测试用管理员账号
- 变更方式：新增 admin（123333），原 test-zhou 保留为 admin_patrol

### 变更点 2：Agent2_环境交接_main.yaml
- 变更原因：同步 admin.super 账号信息
- 变更方式：admin.super 指向 admin 账号，admin.patrol 保留 test-zhou
