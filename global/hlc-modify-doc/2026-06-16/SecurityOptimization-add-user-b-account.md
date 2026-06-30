# 变更日志

- 日期：2026-06-16
- 修改文件：安全优化/测试文档/accounts_main.yaml、Agent2_环境交接_main.yaml
- 修改类型：新增 / 修改
- 描述：补充 main 环境用户 B 测试账号 zhoulingxiao1216@proton.me

## 变更摘要

### 变更点 1：accounts_main.yaml
- 变更原因：集中管理安全优化 main 环境双用户与管理员账号
- 变更方式：新增账号文件，user_a + user_b + admin

### 变更点 2：Agent2_环境交接_main.yaml
- 变更原因：同步用户 B 凭证，解除 IDOR 类用例账号阻塞
- 变更方式：更新 accounts 段与 agent2_instruction
