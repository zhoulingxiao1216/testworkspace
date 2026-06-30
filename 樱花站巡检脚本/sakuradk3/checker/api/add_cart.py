# -*- coding: utf-8 -*-
# d:\sakuradk3\checker\api\add_cart.py
import json
import os
import sys
import random
import re
import urllib.parse
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

from config.settings import API_CONFIG
from core.rules.assertion import AssertionTool
from core.path_manager import TOKEN_DIR, DATA_DIR
from config.data.cookie import CookieManager
# --- 核心修改：从 headers.py 导入分别拿取的逻辑 ---
from config.data.headers import get_b2b_headers, get_d2c_headers

# ==========================================
# 辅助函数
# ==========================================

def process_val(val):
    """处理随机数或空值补全"""
    if val == "" or val is None:
        return random.randint(1, 5)
    if isinstance(val, str):
        match = re.search(r"random_int\((\d+),\s*(\d+)\)", val)
        if match:
            try:
                return random.randint(int(match.group(1)), int(match.group(2)))
            except:
                return 1
    return val

def load_default_payloads():
    """加载默认参数"""
    payload_path = os.path.join(DATA_DIR, "add_cart_payloads.json")
    if not os.path.exists(payload_path):
        raise FileNotFoundError(f"未找到核心数据文件: {payload_path}")
    with open(payload_path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_payload(task_name, default_pool, rules):
    """构建请求参数"""
    payload = default_pool.get(task_name, {}).copy()
    
    # D2C 需要添加默认字段
    if "D2C" in task_name:
        d2c_defaults = {
            "id": payload.get("ItemID", ""),
            "buytype": "0",
            "iswholesale": "",
            "ExternalID": "",
            "CeilingPrice": ""
        }
        for k, v in d2c_defaults.items():
            if k not in payload:
                payload[k] = v
    
    # 合并规则中的 params
    params = rules.get(task_name, {}).get("params", {})
    for k, v in params.items():
        payload[k] = process_val(v)
    
    return payload

def build_url(task_name, endpoints, base_url):
    """构建 URL"""
    endpoint_key = "add_cart_D2C" if "D2C" in task_name else "add_cart_B2B"
    endpoint = endpoints.get(endpoint_key, "")
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return endpoint
    return f"{base_url.rstrip('/')}{endpoint}"

def get_d2c_base_url(endpoints):
    """
    从 API_CONFIG 的 add_cart_D2C endpoint 提取 D2C base URL
    如果 endpoint 是完整 URL，提取域名；否则返回 None（需要从其他地方获取）
    """
    from urllib.parse import urlparse
    d2c_endpoint = endpoints.get("add_cart_D2C", "")
    if d2c_endpoint.startswith("http://") or d2c_endpoint.startswith("https://"):
        parsed = urlparse(d2c_endpoint)
        return f"{parsed.scheme}://{parsed.netloc}"
    return None

def standardize_b2b_payload(payload):
    """标准化 B2B payload：保持原始类型"""
    return payload

def prepare_d2c_payload(payload):
    """
    准备 D2C payload：转换为 URL 编码的表单数据（完全匹配 postman 格式）
    关键点：
    1. 保留所有字段，包括空字符串（CeilingPrice=, ExternalID=）
    2. 列表/字典先转为 JSON 字符串
    3. 字符串类型的 JSON（如 alibabaPrice: "[{...}]"）保持原样，会被正确 URL 编码
    4. 确保 UTF-8 字符（如日文 PropID）正确 URL 编码
    """
    safe_payload = {}
    for k, v in payload.items():
        if v is None:
            safe_payload[k] = ""
        elif isinstance(v, (list, dict)):
            # 列表或字典：转为 JSON 字符串（ensure_ascii=False 保留非 ASCII 字符）
            safe_payload[k] = json.dumps(v, ensure_ascii=False)
        else:
            # 其他类型（字符串、数字等）：转为字符串
            # 注意：如果 v 已经是 JSON 字符串（如 alibabaPrice），这里会保持原样
            safe_payload[k] = str(v)
    
    # 使用 urllib.parse.urlencode 进行 URL 编码
    # doseq=True: 处理列表值（虽然我们已经转为字符串，但保留此参数）
    # quote_via=urllib.parse.quote: 确保 UTF-8 字符正确编码（如日文、中文）
    return urllib.parse.urlencode(safe_payload, doseq=True, quote_via=urllib.parse.quote)

# ==========================================
# 主运行逻辑
# ==========================================

def run(task_config=None):
    """协议执行器：翻译配置 -> 发送请求 -> 返回断言结果"""
    results_status, msgs = {}, []
    try:
        # 1. 加载配置与数据
        default_pool = load_default_payloads()
        all_rules = AssertionTool.get_rules_dynamically("add_cart", root_path)
        target_mail = all_rules.get("add_cart_task", {}).get("login_account", "").strip()

        # 2. 获取 Token 逻辑（参考 img_search.py）
        token_file = os.path.join(TOKEN_DIR, "current_tokens.json")
        b2b_token = ""
        if os.path.exists(token_file):
            try:
                with open(token_file, "r", encoding="utf-8") as f:
                    tokens_data = json.load(f)
                    b2b_token = tokens_data.get(target_mail, "") or tokens_data.get(target_mail.lower(), "")
                    # 尝试去除空格匹配
                    if not b2b_token:
                        for key, val in tokens_data.items():
                            if key.strip() == target_mail.strip():
                                b2b_token = val
                                break
            except Exception as e:
                print(f"Token读取异常: {e}", file=sys.stderr)

        # 3. 获取 Cookie（从 cookie.py 获取）
        d2c_cookie = CookieManager.get_d2c_cookie(target_mail)  # D2C Cookie 包含 loginToken
        b2b_cookie = CookieManager.get_b2b_cookie(target_mail)

        base_url = API_CONFIG.get("BASE_URL", "").rstrip('/')
        endpoints = API_CONFIG.get("ENDPOINTS", {})

        # 4. 循环执行任务（参考 img_search.py 的结构）
        for task_name in ["D2C_1688", "D2C_taobao", "B2B_1688", "B2B_taobao"]:
            try:
                is_d2c = "D2C" in task_name
                url = build_url(task_name, endpoints, base_url)
                payload = build_payload(task_name, default_pool, all_rules)

                if is_d2c:
                    # D2C 请求：使用表单数据
                    # D2C 只需要 Cookie 中的 loginToken（通过 get_d2c_cookie 获取）
                    if not d2c_cookie:
                        results_status[task_name] = False
                        msgs.append(f"{task_name}:FAIL(缺失D2C Cookie)")
                        continue
                    # 从 endpoint 提取 D2C base URL（动态获取，不写死）
                    d2c_base_url = get_d2c_base_url(endpoints)
                    if not d2c_base_url:
                        results_status[task_name] = False
                        msgs.append(f"{task_name}:FAIL(无法获取D2C Base URL)")
                        continue
                    # 获取商品 URL 用于动态生成 referer（支持 1688 和 taobao）
                    item_url = payload.get("ItemURL", "")
                    req_headers = get_d2c_headers(d2c_cookie, d2c_base_url, item_url=item_url)
                    data_str = prepare_d2c_payload(payload)
                    response = requests.post(url, data=data_str, headers=req_headers, timeout=25, verify=False, proxies={'http': None, 'https': None})
                else:
                    # B2B 请求：使用 JSON
                    if not b2b_token or not b2b_cookie:
                        results_status[task_name] = False
                        msgs.append(f"{task_name}:FAIL(缺失B2B凭据)")
                        continue
                    # 获取商品信息用于动态生成 referer 和 currpath
                    item_id = payload.get("ItemID", "")
                    item_url = payload.get("ItemURL", "")
                    req_headers = get_b2b_headers(base_url, b2b_token, b2b_cookie, item_id=item_id, item_url=item_url)
                    standard_payload = standardize_b2b_payload(payload)
                    response = requests.post(url, json=standard_payload, headers=req_headers, timeout=25, verify=False, proxies={'http': None, 'https': None})

                # 5. 统一结果处理
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
            "actual": f"加购任务结果: {' | '.join(msgs)}"
        }
    except Exception as e:
        final_result = {"success": False, "message": str(e), "actual": traceback.format_exc()}

    print(json.dumps(final_result, ensure_ascii=False))
    return final_result

if __name__ == "__main__":
    run()