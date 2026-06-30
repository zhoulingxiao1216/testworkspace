# -*- coding: utf-8 -*-
# d:\sakuradk3\core\path_manager.py
import os
import sys

# 1. 核心定位：无论在哪个目录下运行，都能准确锁定根目录
current_file_path = os.path.abspath(__file__)
ROOT_DIR = os.path.dirname(os.path.dirname(current_file_path))

# 2. 自动初始化环境：这一步做了，其他脚本就不用再写 sys.path.insert 了
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# 3. 定义标准目录常量 (供其他模块直接引用)
CONFIG_DIR = os.path.join(ROOT_DIR, "config")
DATA_DIR = os.path.join(CONFIG_DIR, "data")
RULES_DIR = os.path.join(CONFIG_DIR, "rules") # 新增：规则目录
LOGS_DIR = os.path.join(ROOT_DIR, "logs")     # 新增：日志目录
TOKEN_DIR = os.path.join(ROOT_DIR, "token")   # 新增：Token目录
CHECKER_DIR = os.path.join(ROOT_DIR, "checker")

# 4. 路径助手函数 (增强复用性的关键)
def get_absolute_path(*relative_paths):
    """
    通用路径转换：输入 ("config", "rules", "login.json") 
    返回系统的绝对路径，防止 Windows/Linux 路径斜杠不一致
    """
    return os.path.join(ROOT_DIR, *relative_paths)

def ensure_dirs():
    """一键创建所有必要的文件夹，防止因找不到文件夹报错"""
    for d in [LOGS_DIR, TOKEN_DIR, os.path.join(LOGS_DIR, "error_summary")]:
        os.makedirs(d, exist_ok=True)

# 执行初始化
ensure_dirs()