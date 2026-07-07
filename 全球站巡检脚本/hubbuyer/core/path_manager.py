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
# 可通过环境变量 HUBBUYER_TOKEN_DIR 指向可写目录（解决部署目录权限问题）
TOKEN_DIR = os.environ.get("HUBBUYER_TOKEN_DIR", "").strip() or os.path.join(ROOT_DIR, "token")
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
        try:
            os.makedirs(d, mode=0o775, exist_ok=True)
        except OSError:
            pass

# 执行初始化
ensure_dirs()


# 5. 后台 API 地址解析（prod/main 共用，避免单独模块未同步导致导入失败）
def _api_config():
    from config.settings import API_CONFIG
    return API_CONFIG


def resolve_admin_api_url(url_or_path):
    text = (url_or_path or "").strip()
    if not text:
        return ""
    if text.startswith("http://") or text.startswith("https://"):
        return text
    api_config = _api_config()
    base = (api_config.get("BASE_URL") or "").rstrip("/")
    path = text if text.startswith("/") else f"/{text}"
    return f"{base}{path}"


def resolve_admin_site_origin(origin=None):
    text = (origin or "").strip()
    if text:
        return text.rstrip("/")
    api_config = _api_config()
    return (api_config.get("url_ADMIN") or "https://admin.hubbuyer.com/").rstrip("/")


def normalize_api_block(block):
    if not block or not isinstance(block, dict):
        return block
    out = dict(block)
    if out.get("url"):
        out["url"] = resolve_admin_api_url(out["url"])
    out["admin_site_origin"] = resolve_admin_site_origin(out.get("admin_site_origin"))
    return out


def normalize_purchase_order_audit_config(cfg):
    data = dict(cfg or {})
    if data.get("audit_api"):
        data["audit_api"] = normalize_api_block(data["audit_api"])
    return data


def normalize_purchase_order_ops_config(cfg):
    data = dict(cfg or {})
    if data.get("detail_api"):
        data["detail_api"] = normalize_api_block(data["detail_api"])
    steps = data.get("steps") or {}
    data["steps"] = {name: normalize_api_block(step) for name, step in steps.items()}
    return data


def normalize_purchase_order_shipping_config(cfg):
    data = dict(cfg or {})
    _shipping_api_keys = [
        "create_ship_order_api", "ship_order_detail_list_api",
        "distribute_api", "distribute_done_api",
        "box_insert_api", "box_done_api",
        "update_fjx_api", "complete_box_api",
        "remove_settling_api", "deduct_money_api",
        "update_waybill_no_api", "sure_ship_api",
        "ship_order_list_api", "ku_stock_in_log_list_api",
    ]
    for key in _shipping_api_keys:
        if data.get(key):
            data[key] = normalize_api_block(data[key])
    return data