# -*- coding: utf-8 -*-
# checker/api/keyword_search.py
import json
import requests
import os
import sys
import traceback
import urllib.parse

# --- 定位根目录 ---
current_file = os.path.abspath(__file__)
root_path = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from config.settings import API_CONFIG
from config.data.headers import get_auth_headers
from core.rules.assertion import AssertionTool
from core.path_manager import TOKEN_DIR

# ==========================================
# 任务配置
# ==========================================
TASKS = {
    "keyword_taobao": {
        "endpoint_key": "keyword_search_taobao",
        "currpath": "/Taobao/list/",
        "referer_path": "/web_view/Taobao/list/",
        "payload": {
            "page": 1, "limit": 20, "keyword": "", "Lang": "1",
            "img_url": "", "sort": "", "is_search": "1"
        }
    },
    "keyword_1688": {
        "endpoint_key": "keyword_search_1688",
        "currpath": "/Alibaba/list/",
        "referer_path": "/web_view/Alibaba/list/",
        "payload": {
            "page": 1, "limit": 50, "keyword": "", "Lang": "1",
            "img_url": "", "language": "ja", "price_order": "",
            "sole_order": "", "re_purchase_order": "",
            "price_start": "", "price_end": "", "is_search": "1",
            "jxhy": "", "regionOpp": "jpOpp", "filter": "isOnePsale"
        }
    }
}


def run_single_task(task_name, task_def, rules, base_url, token_val, endpoints):
    """执行单个关键字搜索任务，返回 (success, message)"""
    keyword = rules.get("keyword", "手机壳")
    encoded_keyword = urllib.parse.quote(keyword)

    endpoint = endpoints.get(task_def["endpoint_key"], "")
    url = f"{base_url}{endpoint}"

    headers = get_auth_headers(base_url, token_val)
    headers.update({
        "currpath": task_def["currpath"],
        "referer": f"{base_url}{task_def['referer_path']}?key={encoded_keyword}&imageUrl=&Lang=1"
    })

    payload = task_def["payload"].copy()
    payload["keyword"] = keyword

    response = requests.post(url, headers=headers, json=payload, timeout=25, proxies={'http': None, 'https': None})

    # 通用断言校验
    check = AssertionTool.verify_api_common(response, rules=rules)
    if not check["success"]:
        return False, check["message"]

    # 额外校验：搜索结果非空
    res_json = response.json()
    data = res_json.get("data", {})
    items = []
    if isinstance(data, dict):
        items = data.get("data", data.get("list", []))
    elif isinstance(data, list):
        items = data
    item_count = len(items) if items else 0

    if rules.get("data_not_empty") and item_count == 0:
        return False, f"搜索结果为空(keyword={keyword})"

    return True, f"keyword={keyword},结果数={item_count}"


def run(task_config=None):
    """B2B 关键字搜索接口校验（1688 + 淘宝）"""
    results_status = {}
    msgs = []

    try:
        # 1. 加载规则
        all_rules = AssertionTool.get_rules_dynamically("keyword_search", root_path)
        target_mail = (all_rules or {}).get("keyword_search_task", {}).get("login_account", "").strip()

        # 2. 获取 Token
        token_val = ""
        token_file = os.path.join(TOKEN_DIR, "current_tokens.json")
        if os.path.exists(token_file):
            with open(token_file, "r", encoding="utf-8") as f:
                tokens_data = json.load(f)
                token_val = tokens_data.get(target_mail, "") or tokens_data.get(target_mail.lower(), "")
                if not token_val:
                    for key, val in tokens_data.items():
                        if key.strip() == target_mail.strip():
                            token_val = val
                            break

        if not token_val:
            final_result = {"success": False, "message": "缺失B2B Token", "status_code": 0, "actual": ""}
            print(json.dumps(final_result, ensure_ascii=False))
            return final_result

        base_url = API_CONFIG.get("BASE_URL", "").rstrip('/')
        endpoints = API_CONFIG.get("ENDPOINTS", {})

        # 3. 循环执行任务
        for task_name, task_def in TASKS.items():
            try:
                rules = (all_rules or {}).get(task_name, {})
                success, detail = run_single_task(task_name, task_def, rules, base_url, token_val, endpoints)
                label = "淘宝" if "taobao" in task_name else "1688"
                results_status[task_name] = success
                msgs.append(f"{label}:{'OK' if success else 'FAIL'}({detail})")
            except Exception as e:
                results_status[task_name] = False
                label = "淘宝" if "taobao" in task_name else "1688"
                msgs.append(f"{label}:Error({str(e)})")

        # 4. 汇总结果
        final_result = {
            "success": all(results_status.values()) if results_status else False,
            "message": " | ".join(msgs),
            "status_code": 200 if all(results_status.values()) else 500,
            "actual": f"关键字搜索结果: {' | '.join(msgs)}"
        }
    except Exception as e:
        final_result = {"success": False, "message": str(e), "actual": traceback.format_exc()}

    print(json.dumps(final_result, ensure_ascii=False))
    return final_result


if __name__ == "__main__":
    run()
