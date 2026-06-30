# 变更日志

- 日期：2026-06-15
- 修改文件：测试平台自建/pages/3_性能压测.py
- 修改类型：修改
- 描述：测试平台性能压测页同步完整报价链路配置与说明

## 变更摘要

### 变更点 1：平台注入环境变量
- 变更原因：压测脚本新增完整报价链路开关与 quote/create 参数，平台未传递导致 UI 与脚本不一致
- 变更方式：新增 `build_stress_runtime_env`，统一注入 `STRESS_ENABLE_FULL_QUOTE_FLOW`、`STRESS_QUOTE_TYPE`、`STRESS_LOGISTICS_CONFIG_ID`

### 变更点 2：配置 UI 与执行预览
- 变更原因：用户无法在平台选择完整/简化下单，预览文案未反映 Step1/Step2 接口
- 变更方式：增加完整报价链路开关及 quote 参数输入；更新真实账号链路说明与执行预览摘要
