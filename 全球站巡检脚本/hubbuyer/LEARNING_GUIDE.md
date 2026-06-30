# 🎓 自动化巡检系统 - 完整学习指南

> 帮助你理解架构，并制作出类似的监控/巡检脚本

---

## 📚 目录结构

```
1. 核心架构设计
2. 系统运行流程
3. 五大核心模块详解
4. 从零开始的实现步骤
5. 代码示例和最佳实践
6. 常见扩展场景
```

---

## 🏗️ 第一部分：核心架构设计

### 系统设计理念

```
配置驱动 + 规则引擎 + 子进程隔离
         ↓
    高度可扩展、低耦合
```

**三个关键设计决策：**

1. **配置集中化**
   - 单一 `settings.py` 控制全局
   - 环境无缝切换 (prod/test/dev)
   - 每个任务通过开关启用/禁用

2. **规则外置化**
   - 检查规则放在 JSON 配置文件中，不写死在代码里
   - 添加新检查时，只需创建脚本 + 修改 JSON
   - 避免反复修改主逻辑

3. **子进程隔离**
   - 每个检查脚本独立运行，互不影响
   - 一个脚本崩溃不会影响整体流程
   - 便于调试和模式化

---

## 🔄 第二部分：系统运行流程

### 完整执行流程图

```
main.py (入口)
    ↓
初始化环境 & 编码
    ↓
logger.log_session_start()  ← 记录开始时间
    ↓
BatchChecker.run_all_checks()
    |
    ├→ 读取 config/rules/*.json (批量获取任务定义)
    |
    ├→ 对每个任务：
    |    ├ 检查 INSPECTION_SWITCHES 开关
    |    ├ 若开启，调用 ScriptRunner.run(脚本路径, 任务配置)
    |    |
    |    ├→ ScriptRunner (子进程)
    |    |    ├ 执行检查脚本（如 checker/api/login.py）
    |    |    ├ 脚本返回 JSON: {"success": true/false, "message": "..."}
    |    |    └ Runner 捕获并解析 JSON
    |    |
    |    └→ logger.log_task() (记录结果)
    |
    ├→ 等待 INSPECTION_INTERVAL 秒
    |
    └→ 返回汇总结果 {"巡检汇总报告": {...}}
    ↓
ReportGenerator.generate_report()
    ├ 将结果转换为 Markdown 格式
    └ 生成报告文件到 reports/ 目录
    ↓
Notifier.send_wechat_report()
    ├ 全通过 → 发送到 "IT部-每日巡检汇报群"
    └ 有故障 → 发送到 "测试和报错通知群"
    ↓
✅ 完成
```

### 关键时间点

| 阶段 | 时间 |
|------|------|
| 脚本加载 | ~1s |
| 单个检查 | 平均 3-10s |
| 任务间隔 | 10s (默认) |
| 全量检查 | ~100-200s (20+ 任务) |

---

## 🔧 第三部分：五大核心模块详解

### 1️⃣ 配置模块 (`config/settings.py`)

**职责**：中央大脑，所有配置都走这里

```python
# 环境切换
ENV_TYPE = "prod"  # 改这一个词就切换环境

# 任务开关（true/false 控制执行）
INSPECTION_SWITCHES = {
    "check_web_url_B2B_pc": True,   # 启用
    "check_api_login": False,       # 禁用（临时跳过）
}

# 超时配置
REQUEST_TIMEOUT_WEB = 30
REQUEST_TIMEOUT_API = 25

# 通知配置
WEBHOOK_URL_NORMAL = "..."  # 成功报告地址
WEBHOOK_URL_ALARM = "..."   # 故障报警地址
```

**关键要点**：
- 修改这个文件后，重启脚本即可生效
- 无需改业务代码

---

### 2️⃣ 规则模块 (`config/rules/*.json`)

**职责**：定义每个检查任务

**规则文件格式：**

```json
{
  "api_login": {
    "key": "check_api_login",                    // 唯一标识
    "desc": "登录接口校验",                     // 描述
    "script": "checker/api/login.py",            // 执行脚本路径
    "rules": {                                   // 验证规则
      "status_code": 200,
      "json_match": {
        "code": 200,
        "msg": "success"
      },
      "extract_keys": ["data.token"]             // 要提取的字段
    }
  }
}
```

**对应的开关：**

```python
INSPECTION_SWITCHES = {
    "check_api_login": True  # key 值对应这里
}
```

---

### 3️⃣ 批量执行器 (`core/batch_checker.py`)

**职责**：遍历所有规则，按顺序执行

```python
class BatchChecker:
    def run_all_checks(self):
        # 1. 读取所有 JSON 规则文件
        json_files = [f for f in os.listdir(self.rules_dir) if f.endswith('.json')]
        
        # 2. 按优先级排序（web → login → search → ...）
        priority = ["web_rules.json", "login_rules.json", ...]
        
        # 3. 对每个任务
        for each_task:
            if 任务开关enabled:
                result = ScriptRunner.run(脚本, 配置)
                logger.log_task(result)
                time.sleep(INSPECTION_INTERVAL)
```

**核心逻辑**：
- ✅ 配置驱动（不改代码就能改行为）
- ✅ 自动遍历（添加新任务只需新增 JSON 和脚本）

---

### 4️⃣ 子进程执行器 (`core/runner.py`)

**职责**：启动检查脚本，捕获并解析返回值

```python
class ScriptRunner:
    @staticmethod
    def run(script_path, project_root, task_config):
        # 1. 将配置转成 JSON 字符串，通过命令行参数传给脚本
        config_json_str = json.dumps(task_config, ensure_ascii=False)
        
        # 2. 启动子进程
        process = subprocess.run(
            [sys.executable, script_path, config_json_str],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=45  # 超时保护
        )
        
        # 3. 捕获输出，解析最后一行的 JSON
        last_line = process.stdout.split('\n')[-1]
        result = json.loads(last_line)
        
        # 4. 验证结果格式
        return {
            "success": result.get("success"),
            "message": result.get("message"),
            "status_code": result.get("status_code")
        }
```

**关键点**：
- 脚本必须输出 JSON 格式结果
- 支持超时保护
- 子进程独立运行，不影响主进程

---

### 5️⃣ 日志系统 (`core/logger.py`)

**职责**：记录执行过程和错误

```python
class InspectorLogger:
    def log_session_start(self, env):
        """记录巡检开始"""
        self.logger.info(f"--- 巡检开始 | 环境: {env} ---")
    
    def log_task(self, name, success, message, url=None):
        """记录单个任务结果"""
        status = "PASS" if success else "FAIL"
        self.logger.info(f"[{status}] {name}: {message}")
        
        if not success:
            # 错误详情单独记录到 error_summary 日志
            self.logger.error(f"详细错误: ...")
    
    def log_error(self, message):
        """记录系统错误"""
        self.logger.error(message)
```

**日志输出**：
- `logs/all_execution/{timestamp}.log` - 全量执行日志
- `logs/error_summary/{timestamp}.log` - 仅错误汇总

---

## 📝 第四部分：从零开始的实现步骤

### 👉 场景：创建监控"数据库健康检查"系统

#### 步骤 1: 创建项目结构

```bash
db_monitor/
├── main.py                      # 入口
├── requirements.txt
├── config/
│   ├── settings.py             # 配置中心
│   └── rules/
│       └── db_rules.json        # 规则定义
├── core/
│   ├── batch_checker.py         # 批量执行器
│   ├── runner.py                # 子进程执行器
│   └── logger.py                # 日志系统
├── checker/
│   └── db/
│       ├── check_mysql.py       # MySQL 检查
│       ├── check_redis.py       # Redis 检查
│       └── check_mongo.py       # MongoDB 检查
├── logs/
├── reports/
└── README.md
```

#### 步骤 2: 创建配置文件 (`config/settings.py`)

```python
# -*- coding: utf-8 -*-
import os

# 1. 环境切换
ENV_TYPE = "prod"  # prod/test/dev

# 2. 检查开关
INSPECTION_SWITCHES = {
    "check_mysql": True,
    "check_redis": True,
    "check_mongo": True,
}

# 3. 数据库配置
DB_CONFIG = {
    "prod": {
        "mysql": {"host": "db1.prod.com", "port": 3306},
        "redis": {"host": "cache.prod.com", "port": 6379},
        "mongo": {"host": "mongo.prod.com", "port": 27017},
    },
    "test": {
        "mysql": {"host": "localhost", "port": 3306},
        "redis": {"host": "localhost", "port": 6379},
        "mongo": {"host": "localhost", "port": 27017},
    }
}

# 4. 检查参数
DB_TIMEOUT = 10
DB_INTERVAL = 5

# 5. 通知配置
WEBHOOK_URL = "https://..."
```

#### 步骤 3: 定义规则文件 (`config/rules/db_rules.json`)

```json
{
  "mysql_check": {
    "key": "check_mysql",
    "desc": "MySQL 数据库连接检查",
    "script": "checker/db/check_mysql.py",
    "rules": {
      "connection_time_ms": 100,
      "replication_lag_seconds": 5,
      "disk_usage_percent": 80
    }
  },
  "redis_check": {
    "key": "check_redis",
    "desc": "Redis 缓存健康检查",
    "script": "checker/db/check_redis.py",
    "rules": {
      "memory_percent": 90,
      "evictions_rate": 0.1
    }
  },
  "mongo_check": {
    "key": "check_mongo",
    "desc": "MongoDB 连接和性能检查",
    "script": "checker/db/check_mongo.py",
    "rules": {
      "connection_pool_size": 100
    }
  }
}
```

#### 步骤 4: 实现检查脚本 (`checker/db/check_mysql.py`)

```python
# -*- coding: utf-8 -*-
import json
import sys
import os
import pymysql

# 初始化路径
root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, root_path)

from config.settings import DB_CONFIG, ENV_TYPE, DB_TIMEOUT

def check_mysql(task_config=None):
    """检查 MySQL 数据库健康状态"""
    
    result = {
        "success": False,
        "message": "未知错误",
        "status_code": 500,
        "expected": "连接成功且响应 < 100ms",
        "actual": ""
    }
    
    try:
        # 1. 获取数据库配置
        db_info = DB_CONFIG.get(ENV_TYPE, {}).get("mysql")
        if not db_info:
            result["message"] = "数据库配置不存在"
            return result
        
        # 2. 尝试连接
        conn = pymysql.connect(
            host=db_info["host"],
            port=db_info["port"],
            user="root",
            password="password",
            database="test",
            timeout=DB_TIMEOUT
        )
        
        # 3. 执行测试查询
        cursor = conn.cursor()
        import time
        start_time = time.time()
        cursor.execute("SELECT 1")
        elapsed_ms = (time.time() - start_time) * 1000
        cursor.close()
        conn.close()
        
        # 4. 验证结果
        if elapsed_ms < 100:
            result["success"] = True
            result["message"] = f"连接成功，响应时间: {elapsed_ms:.2f}ms"
            result["actual"] = f"响应时间: {elapsed_ms:.2f}ms"
            result["status_code"] = 200
        else:
            result["message"] = f"响应缓慢: {elapsed_ms:.2f}ms > 100ms"
            result["actual"] = f"响应时间: {elapsed_ms:.2f}ms"
        
    except pymysql.OperationalError as e:
        result["message"] = f"连接失败: {str(e)}"
        result["actual"] = str(e)
    except Exception as e:
        result["message"] = f"检查异常: {str(e)}"
        result["actual"] = str(e)
    
    # 5. 输出 JSON（必须是最后一行）
    print(json.dumps(result, ensure_ascii=False))
    return result

if __name__ == "__main__":
    # 支持从命令行接收任务配置（由 runner.py 传入）
    task_config = None
    if len(sys.argv) > 1:
        try:
            task_config = json.loads(sys.argv[1])
        except:
            pass
    
    check_mysql(task_config)
```

#### 步骤 5: 实现批量执行器 (`core/batch_checker.py`)

```python
# -*- coding: utf-8 -*-
import os
import json
import time
from core.runner import ScriptRunner
from config.settings import INSPECTION_SWITCHES, ENV_TYPE, DB_INTERVAL
from core.logger import InspectorLogger

class BatchChecker:
    def __init__(self, logger_instance=None):
        self.results = {}
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.rules_dir = os.path.join(self.project_root, "config", "rules")
        self.logger = logger_instance if logger_instance else InspectorLogger()
    
    def run_all_checks(self):
        print(f"\n🚀 启动数据库巡检 | 环境: {ENV_TYPE}")
        
        if not os.path.exists(self.rules_dir):
            print(f"❌ 错误: 找不到配置目录 {self.rules_dir}")
            return {}
        
        batch_results = {}
        processed_keys = set()
        
        # 读取所有规则文件
        json_files = [f for f in os.listdir(self.rules_dir) if f.endswith('.json')]
        
        for file_name in json_files:
            with open(os.path.join(self.rules_dir, file_name), 'r', encoding='utf-8') as f:
                task_group = json.load(f)
            
            for site_id, task_config in task_group.items():
                task_key = task_config.get("key")
                task_desc = task_config.get("desc")
                
                if not task_key or not task_desc:
                    continue
                
                # 防止重复执行
                if task_key in processed_keys:
                    continue
                processed_keys.add(task_key)
                
                # 检查开关
                if INSPECTION_SWITCHES.get(task_key, False):
                    script_path = task_config.get("script")
                    print(f"正在检查: {task_desc}...")
                    
                    try:
                        # 执行检查
                        result = ScriptRunner.run(script_path, self.project_root, task_config)
                        
                        # 记录日志
                        self.logger.log_task(
                            name=task_desc,
                            success=result.get("success"),
                            message=result.get("message")
                        )
                        
                        # 保存结果
                        status_icon = "✅" if result.get("success") else "❌"
                        print(f"   {status_icon} {result.get('message')}")
                        
                        batch_results[task_desc] = result
                    
                    except Exception as e:
                        self.logger.log_error(f"{task_desc} 崩溃: {str(e)}")
                        print(f"   ❌ 执行异常")
                    
                    # 任务间隔
                    if DB_INTERVAL > 0:
                        time.sleep(DB_INTERVAL)
        
        return {"巡检汇总报告": batch_results}
```

#### 步骤 6: 实现入口 (`main.py`)

```python
# -*- coding: utf-8 -*-
import os
import sys
from datetime import datetime
from config.settings import ENV_TYPE
from core.logger import InspectorLogger
from core.batch_checker import BatchChecker

def initialize_environment():
    """初始化环境"""
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    current_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_dir)
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

def main():
    initialize_environment()
    
    logger = InspectorLogger()
    logger.log_session_start(ENV_TYPE)
    
    print("=" * 60)
    print(f"🚀 数据库巡检系统 | 环境: {ENV_TYPE} | 启动: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)
    
    try:
        # 执行检查
        checker = BatchChecker(logger_instance=logger)
        results = checker.run_all_checks()
        
        # 统计结果
        report_data = results.get("巡检汇总报告", {})
        all_results = list(report_data.values())
        
        total = len(all_results)
        success = sum(1 for r in all_results if r.get("success"))
        failed = total - success
        
        # 输出汇总
        logger.log_info(f"汇总: 共计 {total} | ✅ 成功 {success} | ❌ 失败 {failed}")
        print(f"📊 汇总: 共计 {total} | ✅ 成功 {success} | ❌ 失败 {failed}")
        
    except Exception as e:
        print(f"\n❌ 系统错误: {str(e)}")
        logger.log_error(f"系统执行崩溃: {str(e)}")

if __name__ == "__main__":
    main()
```

---

## 💡 第五部分：最佳实践

### ✅ DO（应该做的）

| 做法 | 原因 |
|------|------|
| 使用 JSON 外置规则 | 改配置无需改代码，版本管理更清晰 |
| 每个脚本独立执行 | 故障隔离，一个脚本崩溃不影响整体 |
| 输出 JSON 格式结果 | 易于解析和扩展 |
| 超时保护 | 防止检查脚本卡住 |
| 详细的错误记录 | 便于故障排查 |

### ❌ DON'T（不应该做的）

| 现象 | 问题 |
|------|------|
| 检查配置写死在代码里 | 修改配置需要改代码、打包、部署 |
| 所有检查串行执行 | 一个卡住就卡住全部 |
| 检查脚本直接调用（不用子进程） | 脚本崩溃会导致主进程崩溃 |
| 混合业务逻辑和检查逻辑 | 难以维护和扩展 |

---

## 🎯 第六部分：常见扩展场景

### 场景 1: 添加新的检查类型

**需求**：新增一个"磁盘空间"检查

**操作步骤**：

1. 创建脚本 `checker/system/check_disk.py`
2. 在 `config/rules/system_rules.json` 中添加条目
3. 在 `INSPECTION_SWITCHES` 中添加开关

**无需修改其他代码！**

---

### 场景 2: 支持多个检查目标

```json
{
  "redis_check_prod": {
    "key": "check_redis_prod",
    "desc": "Redis 生产环境检查",
    "script": "checker/db/check_redis.py",
    "target": "prod_redis_host"
  },
  "redis_check_test": {
    "key": "check_redis_test",
    "desc": "Redis 测试环境检查",
    "script": "checker/db/check_redis.py",
    "target": "test_redis_host"
  }
}
```

脚本通过 `task_config["target"]` 获得具体目标。

---

### 场景 3: 条件执行（A 成功才执行 B）

```python
# 在 batch_checker.py 中修改
if task_key == "check_b":
    # 查看 check_a 的结果
    if not batch_results.get("A 的描述", {}).get("success"):
        print(f"⏭️  跳过 {task_desc}（前置任务失败）")
        continue
```

---

## 📊 架构对比

### 传统方式 vs 本架构

| 维度 | 传统 | 本架构 |
|------|------|--------|
| 改检查内容 | 改代码 → 编译 → 部署 | 改 JSON 配置 → 重启即可 |
| 添加新检查 | 修改主逻辑 | 新建脚本 → 新增 JSON 条目 |
| 故障隔离 | 一个脚本崩溃影响全部 | 脚本独立执行，互不影响 |
| 并发扩展 | 困难 | 容易（可改成并发执行） |

---

## 🚀 快速总结

本架构的四个核心要素：

```
1. 配置集中化    (settings.py)       → 无需改代码修改行为
2. 规则外置化    (config/rules/)     → 易于扩展
3. 子进程隔离    (runner.py)         → 故障隔离
4. 日志系统      (logger.py)         → 便于排查
```

**学习路径**：
1. 理解这 4 个要素 📚
2. 实现一个简单系统 💻
3. 逐步扩展功能 🚀

---

## 📞 常见问题

**Q: 为什么要用子进程而不是直接调用函数?**
A: 隔离崩溃、独立超时管理、便于版本更新。

**Q: 为什么规则用 JSON 而不是 Python dict?**
A: JSON 是标准化格式，易于版本控制、易于给非技术人员编辑。

**Q: 怎么实现并发执行?**
A: 在 `batch_checker.py` 中用 `ThreadPoolExecutor` 或 `ProcessPoolExecutor`。

---

希望这份指南能帮助你掌握这个架构！
