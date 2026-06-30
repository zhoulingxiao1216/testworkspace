# API 端点登记表

> Agent 2 在 Layer 3 探索阶段或通过浏览器 Network 面板发现 API 后，需登记到此文件。
> 此表为 Layer 1 (API Direct) 执行的基础依赖。

## 认证信息

| 环境 | 登录 URL | 认证方式 | 获取方法 |
|------|---------|---------|---------|
| Admin 后台 | `https://lying-admin.hubbuyer.com` | Cookie (PHPSESSID) | 通过 Layer 2 Playwright 登录后提取 |
| B2B 前端 | `https://lying-b2b.hubbuyer.com` | Cookie | 通过 Layer 2 Playwright 登录后提取 |
| WWW 前台 | `https://lying-www.hubbuyer.com` | Cookie | 通过 Layer 2 Playwright 登录后提取 |

## 端点登记

| 模块 | 端点 | 方法 | 用途 | 请求参数 | 认证方式 | 发现日期 |
|------|------|------|------|---------|---------|---------|
| *待发现* | | | | | | |

> **发现流程**：
> 1. Layer 3 (browser_subagent) 打开目标页面
> 2. 观察浏览器 Network 面板中的 XHR/Fetch 请求
> 3. 记录端点 URL、方法、请求体结构
> 4. 填入本表并标注发现日期
> 
> 或者通过后端 Swagger 文档（如有）直接批量导入。
