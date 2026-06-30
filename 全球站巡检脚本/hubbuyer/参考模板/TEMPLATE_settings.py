# -*- coding: utf-8 -*-
"""
通用模板：配置中心

使用场景：任何需要集中配置的系统（监控、巡检、爬虫等）
"""

import os
import sys

# ========== 环境切换（这一个词控制全局行为）==========
ENV_TYPE = "prod"  # 改这里: "prod" / "test" / "dev"

# ========== 任务开关（true/false 控制执行）==========
INSPECTION_SWITCHES = {
    "check_task_1": True,
    "check_task_2": True,
    "check_task_3": False,  # 禁用某个检查
}

# ========== 这是模板，复制修改以下部分 ==========

# 1. 根据环境加载配置
if ENV_TYPE == "prod":
    BASE_URL = "https://api.prod.com"
    WEBHOOK_URL = "https://hooks.prod.com/xxx"
elif ENV_TYPE == "test":
    BASE_URL = "https://api.test.com"
    WEBHOOK_URL = "https://hooks.test.com/xxx"
else:  # dev
    BASE_URL = "http://localhost:8000"
    WEBHOOK_URL = "http://localhost:9000/xx"

# 2. 核心参数
TIMEOUT = 10
RETRY_INTERVAL = 5
MAX_RETRIES = 3

# 3. 路径配置
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES_DIR = os.path.join(PROJECT_ROOT, "config", "rules")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")

print(f"[配置] 环境={ENV_TYPE}, 基址={BASE_URL}")
