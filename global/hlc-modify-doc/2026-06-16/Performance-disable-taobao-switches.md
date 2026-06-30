# 变更日志

- 日期：2026-06-16
- 修改文件：`全球站压测脚本/Performance/config/settings.py`、`全球站压测脚本/Performance/core_stress.py`、`测试平台自建/pages/3_性能压测.py`
- 修改类型：修改
- 描述：新增淘宝关键词搜索与详情页接口压测开关，默认关闭

## 变更摘要

### 变更点 1：settings.py 环境变量开关
- 变更原因：taobao 关键字/详情接口不稳定（如 40000），需从压测中默认剔除
- 变更方式：新增 `STRESS_ENABLE_TAOBAO_KEYWORD`、`STRESS_ENABLE_TAOBAO_DETAIL`，默认 `False`

### 变更点 2：core_stress.py 链路过滤
- 变更原因：开关需作用于真实用户浏览、虚拟用户关键词、动态加购与详情请求
- 变更方式：按开关过滤来源列表；淘宝详情在开关关闭时直接跳过

### 变更点 3：测试平台性能压测页
- 变更原因：平台启动压测时需同步注入上述环境变量
- 变更方式：配置区增加两个 checkbox，并写入 `STRESS_ENABLE_TAOBAO_*`
