# -*- coding: utf-8 -*-
"""
压测数据管理器
直接读取巡检系统 (hubbuyer/config/data/) 的 JSON 数据文件
"""
import os
import json

# 巡检系统数据目录
_HUBBUYER_DATA_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..",
    "全球站巡检脚本", "hubbuyer", "config", "data"
))


def _load_json(filename):
    """从巡检系统加载 JSON 数据文件"""
    path = os.path.join(_HUBBUYER_DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ==========================================
# 预加载所有数据文件（启动时一次性加载, 避免运行时 I/O）
# ==========================================
IMG_SEARCH_DATA = _load_json("img_search.json")
KEYWORD_SEARCH_DATA = _load_json("keyword_search.json")
ADD_CART_DATA = _load_json("add_cart_payloads.json")
SUBMIT_ORDER_DATA = _load_json("submit_order.json")
B2B_ADDON_ID_DATA = _load_json("B2B_Addon_id.json")
B2B_ADDON_DATA = _load_json("B2B_Addon.json")
