# 快速参考卡 - 一页纸掌握架构

## 🏗️ 项目文件清单

```
my_automation_system/
│
├── main.py                 ← 入口 (TEMPLATE_main.py)
├── requirements.txt
│
├── config/
│   ├── settings.py         ← 核心配置 (TEMPLATE_settings.py)
│   └── rules/
│       └── task_rules.json  ← 规则定义 (TEMPLATE_rules.json)
│
├── core/
│   ├── batch_checker.py    ← 批量执行器 (TEMPLATE_batch_checker.py)
│   ├── runner.py           ← 子进程执行器
│   └── logger.py           ← 日志系统
│
├── checker/
│   └── {category}/
│       ├── check_1.py      ← 检查脚本 (TEMPLATE_checker_script.py)
│       ├── check_2.py
│       └── check_3.py
│
├── logs/
│   ├── all_execution/      ← 全量日志
│   └── error_summary/      ← 错误日志
│
└── reports/                ← 报告输出目录
```

---

## 🔄 执行流程 (5 个关键步骤)

```
① main.py              ② BatchChecker        ③ ScriptRunner
   初始化环境            遍历规则文件          启动子进程
        →                 对每个任务            执行检查脚本
        
④ Logger               ⑤ 输出结果
   记录日志              汇总打印
```

---

## 📝 4 个必须的文件

| 文件 | 职责 | 修改频率 |
|------|------|--------|
| `config/settings.py` | 集中配置（环境、开关、参数） | 🔴 常修改 |
| `config/rules/*.json` | 定义检查任务 | 🟡 偶尔修改 |
| `checker/*/check_*.py` | 实现具体检查逻辑 | 🟡 偶尔修改 |
| `core/batch_checker.py` | 批量执行器（一般不改） | 🟢 很少修改 |

---

## 🎯 添加新检查的 3 步流程

### ✅ 步骤 1: 创建检查脚本

文件: `checker/my_category/check_my_task.py`

```python
import json, sys, os
root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, root_path)
from config.settings import BASE_URL, TIMEOUT

def check_my_task(task_config=None):
    result = {"success": False, "message": "错误", "status_code": 500, "expected": "", "actual": ""}
    
    try:
        # 你的检查逻辑
        result["success"] = True
        result["message"] = "检查通过"
        result["status_code"] = 200
    except Exception as e:
        result["message"] = str(e)
    
    print(json.dumps(result, ensure_ascii=False))
    return result

if __name__ == "__main__":
    task_config = json.loads(sys.argv[1]) if len(sys.argv) > 1 else None
    check_my_task(task_config)
```

### ✅ 步骤 2: 在规则文件中定义任务

文件: `config/rules/tasks.json`

```json
{
  "my_task": {
    "key": "check_my_task",
    "desc": "我的检查 - 描述",
    "script": "checker/my_category/check_my_task.py",
    "rules": {
      "timeout_sec": 30,
      "expected_status": 200
    }
  }
}
```

### ✅ 步骤 3: 在配置中启用

文件: `config/settings.py`

```python
INSPECTION_SWITCHES = {
    "check_my_task": True,  # ← 添加这行
}
```

**完成！** 无需改其他代码，重启即可!

---

## 🔧 常见修改

### ❓ 改变任务执行间隔

```python
# config/settings.py
RETRY_INTERVAL = 5  # 改这个值
```

### ❓ 临时禁用某个检查

```python
# config/settings.py
INSPECTION_SWITCHES = {
    "check_task_1": True,
    "check_task_2": False,  # 改成 False
}
```

### ❓ 改变超时时间

```python
# config/settings.py
TIMEOUT = 15  # 从 30 改到 15
```

### ❓ 支持多个环境配置

```python
# config/settings.py
if ENV_TYPE == "prod":
    BASE_URL = "https://api.prod.com"
    WEBHOOK = "https://webhook.prod"
elif ENV_TYPE == "test":
    BASE_URL = "https://api.test.com"
    WEBHOOK = "https://webhook.test"
else:
    BASE_URL = "http://localhost:8000"
    WEBHOOK = "http://localhost:9000"
```

---

## 🐛 调试技巧

### 单独运行检查脚本

```bash
# 直接执行脚本，看输出
python checker/my_category/check_my_task.py

# 或带参数
python checker/my_category/check_my_task.py '{"target": "prod"}'
```

### 查看日志

```bash
# 查看全量日志
tail -f logs/all_execution/2026-03-20-10-15.log

# 查看错误日志
cat logs/error_summary/2026-03-20-10-15.log
```

### 部分执行（调试）

```python
# config/settings.py
INSPECTION_SWITCHES = {
    "check_task_1": False,   # 禁用
    "check_task_2": True,    # 只运行这个
}
```

---

## 📊 关键指标

| 指标 | 预期 | 检查项 |
|------|------|--------|
| 总耗时 | < 3 分钟 | 检查数量、超时时间 |
| 内存占用 | < 100MB | 是否有内存泄漏 |
| CPU 使用 | < 20% | I/O 阻塞时间 |
| 成功率 | > 95% | 网络稳定性 |

---

## ✅ 检查列表 - 制作新系统时

### 设计阶段
- [ ] 明确检查目标（要检查什么？）
- [ ] 确定检查指标（成功的定义是什么？）
- [ ] 规划目录结构

### 实现阶段
- [ ] 创建 `config/settings.py`
- [ ] 创建 `config/rules/*.json`
- [ ] 创建 `checker/` 下的检查脚本
- [ ] 创建 `main.py` 入口

### 测试阶段
- [ ] 单独测试每个检查脚本
- [ ] 测试开关启用/禁用
- [ ] 测试环境切换
- [ ] 测试异常处理（网络中断、超时等）

### 部署阶段
- [ ] 配置日志目录权限
- [ ] 配置报告目录权限
- [ ] 设置定时任务（cron/任务计划）
- [ ] 测试企业微信通知

---

## 🎓 学习路径

```
第 1 天: 理解架构     → 读 LEARNING_GUIDE.md
第 2 天: 看代码       → 浏览 hubbuyer/ 项目文件
第 3 天: 动手练习     → 基于模板创建简单系统
第 4 天: 完成功能     → 添加 3-5 个检查任务
第 5 天: 优化部署     → 配置日志、通知、定时任务
```

---

## 💾 代码模板文件

| 模板文件 | 用途 |
|---------|------|
| `TEMPLATE_settings.py` | 配置文件模板 |
| `TEMPLATE_batch_checker.py` | 批量执行器模板 |
| `TEMPLATE_checker_script.py` | 检查脚本模板 |
| `TEMPLATE_rules.json` | 规则文件模板 |
| `TEMPLATE_main.py` | 入口脚本模板 |

> 💡 **使用方法**：复制这些文件，修改说明部分的代码即可

---

## 📞 常见问题速查表

| 问题 | 解决方案 |
|------|--------|
| 脚本运行不了 | 检查路径、import、编码 |
| 结果没记录到日志 | 检查 JSON 输出格式 |
| 超时了 | 增加 TIMEOUT 值 |
| 任务被跳过 | 检查 INSPECTION_SWITCHES |
| 通知没发送 | 检查 Webhook URL |

---

**祝你成功！** 🎉

有问题就参考 LEARNING_GUIDE.md 的详细版本。
