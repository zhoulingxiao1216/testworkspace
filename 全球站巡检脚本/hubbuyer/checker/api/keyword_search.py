# -*- coding: utf-8 -*-
# d:\sakuradk3\checker\api\keyword_search.py
import json
import os
import sys
import requests
import traceback
import urllib3

# 禁用 InsecureRequestWarning 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 定位根目录 ---
current_file = os.path.abspath(__file__)
root_path = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from config.settings import API_CONFIG, REQUEST_TIMEOUT_API
from core.rules.assertion import AssertionTool
from core.path_manager import TOKEN_DIR, DATA_DIR
from config.data.cookie import CookieManager
from config.data.headers import get_b2b_img_search_headers

# ==========================================
# 辅助函数
# ==========================================

def load_default_payloads():
    """加载默认参数"""
    payload_path = os.path.join(DATA_DIR, "keyword_search.json")
    if not os.path.exists(payload_path):
        raise FileNotFoundError(f"未找到核心数据文件: {payload_path}")
    with open(payload_path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_payload(task_name, default_pool, rules):
    """构建请求参数"""
    task_data = default_pool.get(task_name, {})
    payload = task_data.copy()
    
    # 合并规则中的 params
    params = rules.get(task_name, {}).get("params", {})
    for k, v in params.items():
        payload[k] = v
    
    return payload

def build_url(task_name, endpoints, base_url):
    """构建 URL"""
    if task_name == "B2B_1688_keyword":
        endpoint = endpoints.get("keyword_search_B2B_1688", "")
    elif task_name == "B2B_taobao_keyword":
        endpoint = endpoints.get("keyword_search_B2B_taobao", "")
    else:
        endpoint = ""
    
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return endpoint
    return f"{base_url.rstrip('/')}{endpoint}"

# ==========================================
# 主运行逻辑
# ==========================================

def run(task_config=None):
    """关键词搜索执行器：1688和淘宝关键词搜索"""
    results_status, msgs = {}, []
    try:
        # 1. 加载配置与数据
        default_pool = load_default_payloads()
        all_rules = AssertionTool.get_rules_dynamically("keyword_search", root_path)
        target_mail = all_rules.get("keyword_search_task", {}).get("login_account", "").strip()

        # 2. 获取 Token 逻辑（参考 add_cart.py）
        token_file = os.path.join(TOKEN_DIR, "current_tokens.json")
        b2b_token = ""
        tokens_data = {}
        if os.path.exists(token_file):
            try:
                with open(token_file, "r", encoding="utf-8") as f:
                    tokens_data = json.load(f)
            except Exception as e:
                print(f"Token读取异常: {e}", file=sys.stderr)
        
        # 如果规则中没有指定账号，或者指定账号的token在current_tokens.json中不存在，则尝试使用current_tokens.json中的第一个账号
        if not target_mail and tokens_data:
            target_mail = list(tokens_data.keys())[0]
        
        # 如果 current_tokens.json 中没有账号，使用默认值
        if not target_mail:
            target_mail = "qa1tr@2200freefonts.com"  # 默认值
        
        # 从 tokens_data 中获取 token
        if tokens_data:
            b2b_token = tokens_data.get(target_mail, "") or tokens_data.get(target_mail.lower(), "")
            # 尝试去除空格匹配
            if not b2b_token:
                for key, val in tokens_data.items():
                    if key.strip() == target_mail.strip():
                        b2b_token = val
                        target_mail = key  # 更新为实际匹配到的账号
                        break
            
            # 如果配置的账号找不到 token，使用 current_tokens.json 中的第一个账号
            if not b2b_token and tokens_data:
                target_mail = list(tokens_data.keys())[0]
                b2b_token = tokens_data[target_mail]

        # 3. 获取 Cookie（从 cookie.py 获取）
        b2b_cookie = CookieManager.get_b2b_cookie(target_mail)

        base_url = API_CONFIG.get("BASE_URL", "").rstrip('/')
        endpoints = API_CONFIG.get("ENDPOINTS", {})

        # 4. 循环执行任务（1688和淘宝）
        for task_name in ["B2B_1688_keyword", "B2B_taobao_keyword"]:
            try:
                url = build_url(task_name, endpoints, base_url)
                payload = build_payload(task_name, default_pool, all_rules)

                # B2B 请求：使用 JSON
                if not b2b_token or not b2b_cookie:
                    results_status[task_name] = False
                    msgs.append(f"{task_name}:FAIL(缺失B2B凭据)")
                    continue
                
                # 从规则或默认值获取 headers 参数
                task_rules = all_rules.get(task_name, {})
                currency = task_rules.get("currency", "KRW")
                language = task_rules.get("language", "korean")
                nation = task_rules.get("nation", "Korea")
                rate = task_rules.get("rate", "220.68")
                logintype = task_rules.get("logintype", "user")
                
                req_headers = get_b2b_img_search_headers(
                    base_url, b2b_token, b2b_cookie,
                    currency=currency, language=language, nation=nation,
                    rate=rate, logintype=logintype
                )
                
                response = requests.post(
                    url, json=payload, headers=req_headers,
                    timeout=REQUEST_TIMEOUT_API, verify=False, proxies={'http': None, 'https': None}
                )

                # 5. 统一结果处理（独立断言逻辑）
                check = AssertionTool.verify_api_common(response, rules=all_rules.get(task_name, {}))
                results_status[task_name] = check["success"]
                msgs.append(f"{task_name}:{'OK' if check['success'] else 'FAIL(' + check.get('message', '未知错误') + ')'}")

            except Exception as e:
                results_status[task_name] = False
                msgs.append(f"{task_name}:Error({str(e)})")

        # 6. 汇总结果
        final_result = {
            "success": all(results_status.values()) if results_status else False,
            "message": " | ".join(msgs),
            "status_code": 200 if all(results_status.values()) else 500,
            "actual": f"关键词搜索任务结果: {' | '.join(msgs)}"
        }
    except Exception as e:
        final_result = {"success": False, "message": str(e), "actual": traceback.format_exc()}

    print(json.dumps(final_result, ensure_ascii=False))
    return final_result

if __name__ == "__main__":
    run()
