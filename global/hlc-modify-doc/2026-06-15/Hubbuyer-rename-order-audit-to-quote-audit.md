# 变更日志

- 日期：2026-06-15
- 修改文件：全球站巡检脚本/hubbuyer/config/settings.py、config/rules/order_audit.json、core/notifier.py、checker/api/order_audit.py、preview_wechat_msg.py
- 修改类型：修改
- 描述：检查点「订单审核」更名为「报价单审核」，与实际审核对象一致

## 变更摘要

### 变更点 1：检查点展示名称
- 变更原因：原「订单审核」实际审核的是报价单
- 变更方式：配置、通知模板、执行日志中的「订单审核/代购订单审核」统一改为「报价单审核」
