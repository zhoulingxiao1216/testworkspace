# 变更日志

- 日期：2026-06-16
- 修改文件：`全球站压测脚本/Performance/config/settings.py`、`全球站压测脚本/Performance/core_stress.py`、`测试平台自建/pages/3_性能压测.py`
- 修改类型：修改
- 描述：新增淘宝商品加购独立开关，默认关闭

## 变更摘要

### 变更点 1：settings.py
- 变更原因：商品加购_taobao 需与关键词、详情分开控制
- 变更方式：新增 `STRESS_ENABLE_TAOBAO_ADD_CART`，默认 `False`

### 变更点 2：core_stress.py
- 变更原因：静态加购与动态加购对淘宝链路的依赖不同
- 变更方式：`_post_add_cart` 校验加购开关；动态加购需关键词+详情+加购三者均开启才走淘宝，静态 fallback 仅依赖加购开关

### 变更点 3：测试平台
- 变更原因：平台启动压测需同步注入环境变量
- 变更方式：新增「启用淘宝商品加购」checkbox
