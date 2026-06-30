# 🌐 全球站自动化巡检系统

> **Sakuradk2 Automated Inspection System**  
> 面向全球站（B2B / D2C）的接口与页面自动化巡检工具，支持多环境切换、企业微信告警通知及可视化巡检报告。

---

## 📋 功能概览

| 功能模块 | 说明 |
|---|---|
| 页面访问巡检 | 检测 B2B-PC、B2B-H5、D2C-PC、AboutUs-PC/H5 等页面可用性 |
| 登录接口巡检 | 验证账号登录接口是否正常响应 |
| 图搜接口巡检 | 检测 B2B 图片搜索接口 |
| 关键词搜索巡检 | 检测 B2B（1688 & 淘宝）关键词搜索接口 |
| 加购接口巡检 | 检测商品加入购物车接口（1688 & 淘宝） |
| 附加项选择巡检 | 检测 B2B / D2C 商品附加项选择接口 |
| 提交报价单巡检 | 检测 B2B 自助报价单提交接口 |
| 支付接口巡检 | 检测 B2B 报价单支付接口 |
| 插件加购巡检 | 检测 B2B & D2C 插件加购接口（可选） |
| 报告生成 | 自动生成可视化 HTML 巡检报告并保存至 `reports/` |
| 企业微信通知 | 巡检完成后推送结果至指定企业微信群，异常时触发报警 |

---

## 🗂️ 项目结构

```
hubbuyer/
├── main.py                  # 主入口，启动巡检任务
├── requirements.txt         # Python 依赖包
├── run.sh                   # Linux/Mac 启动脚本
│
├── config/                  # 配置模块
│   ├── settings.py          # 核心配置（环境开关、巡检开关、通知配置）
│   ├── api/                 # 各环境 API 地址配置（prod/test/dev）
│   ├── url/                 # 各环境页面 URL 配置（prod/test/dev）
│   ├── data/                # 测试账号数据池
│   └── rules/               # 巡检规则定义
│
├── core/                    # 核心执行模块
│   ├── batch_checker.py     # 批量巡检调度器（按开关控制任务执行）
│   ├── logger.py            # 日志记录器
│   ├── notifier.py          # 企业微信通知推送
│   ├── report_generator.py  # HTML 报告生成器
│   ├── runner.py            # 单任务执行器
│   └── path_manager.py      # 路径管理
│
├── checker/                 # 巡检脚本集合
│   ├── api/                 # API 接口巡检脚本
│   │   ├── login.py         # 登录接口
│   │   ├── img_search.py    # 图搜接口
│   │   ├── keyword_search.py# 关键词搜索
│   │   ├── add_cart.py      # 加购接口
│   │   ├── B2B_Addon.py     # B2B 附加项
│   │   ├── D2C_Addon.py     # D2C 附加项
│   │   ├── submit_order.py  # 提交报价单
│   │   ├── payment.py       # 支付接口
│   │   └── plugin.py        # 插件加购
│   └── web/                 # 页面访问巡检脚本
│       ├── url_B2B_pc.py
│       ├── url_B2B_h5.py
│       ├── url_D2C_pc.py
│       ├── url_AboutUs_pc.py
│       └── url_AboutUs_h5.py
│
├── logs/                    # 运行日志目录（自动生成）
├── reports/                 # HTML 巡检报告目录（自动生成）
└── token/                   # Token 缓存目录
```

---

## ⚙️ 配置说明

所有配置集中在 `config/settings.py`，**切换环境只需修改一个变量**：

```python
# 可选值：'prod'（生产）| 'test'（测试）| 'dev'（开发）
ENV_TYPE = "prod"
```

### 巡检开关

在 `INSPECTION_SWITCHES` 中按需开启或关闭各项巡检任务：

```python
INSPECTION_SWITCHES = {
    "check_web_url_B2B_pc":    True,   # B2B-PC 页面巡检
    "check_api_login":         True,   # 登录接口巡检
    "check_api_img_search":    True,   # 图搜接口巡检
    # ... 其他开关见 settings.py
}
```

### 通知配置

```python
ENABLE_NORMAL_NOTIFIER = False  # 全通过报告推送开关
ENABLE_ALARM_NOTIFIER  = False  # 故障报警推送开关
WEBHOOK_URL_NORMAL = "..."      # 正常报告群 Webhook
WEBHOOK_URL_ALARM  = "..."      # 报警通知群 Webhook
```

### 超时配置

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `REQUEST_TIMEOUT_WEB` | 30s | 页面请求超时 |
| `REQUEST_TIMEOUT_API` | 25s | API 请求超时 |
| `REQUEST_TIMEOUT_NOTIFIER` | 10s | 通知推送超时 |
| `SCRIPT_RUNNER_TIMEOUT` | 45s | 单任务执行超时 |
| `INSPECTION_INTERVAL` | 10s | 任务间隔时间 |

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

> 要求 Python 3.7+

### 2. 配置环境

编辑 `config/settings.py`，设置目标环境和账号信息：

```python
ENV_TYPE = "prod"   # 切换为目标环境
```

在 `config/data/login_data.py` 中配置对应环境的测试账号。

### 3. 启动巡检

```bash
python main.py
```

### 4. 查看报告

- 巡检完成后，HTML 报告自动保存至 `reports/` 目录  
- 如已配置企业微信 Webhook，结果将自动推送至对应群组

---

## 📊 巡检流程

```
启动 main.py
    │
    ├─ 初始化环境（编码、路径、日志）
    │
    ├─ BatchChecker 根据 INSPECTION_SWITCHES 调度巡检任务
    │       │
    │       ├─ 页面巡检（web/）
    │       └─ 接口巡检（api/）
    │
    ├─ 汇总结果（成功 / 失败 统计）
    │
    ├─ ReportGenerator 生成 HTML 报告
    │
    └─ Notifier 推送企业微信通知
```

---

## 📁 模板文件说明

项目根目录下的 `TEMPLATE_*.py` 文件为新增巡检脚本的参考模板：

| 文件 | 用途 |
|---|---|
| `TEMPLATE_main.py` | 主入口模板 |
| `TEMPLATE_checker_script.py` | 单个巡检脚本模板 |
| `TEMPLATE_batch_checker.py` | 批量调度器模板 |
| `TEMPLATE_settings.py` | 配置文件模板 |
| `TEMPLATE_rules.json` | 巡检规则 JSON 模板 |

---

## 📖 更多文档

| 文档 | 说明 |
|---|---|
| [LEARNING_GUIDE.md](./LEARNING_GUIDE.md) | 脚本学习与开发指南 |
| [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) | 快速参考手册 |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | 部署与运维说明 |

---

## 🔧 依赖环境

- **Python** 3.7+
- **requests** >= 2.25.1
- **urllib3** >= 1.26.0

---

*负责人：周凌虓 | 项目：hubbuyer 自动化巡检系统*
