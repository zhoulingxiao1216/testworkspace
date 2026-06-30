# -*- coding: utf-8 -*-
# d:\sakuradk3\checker\api\D2C_Addon.py
import json
import os
import sys
import random
import requests
import traceback
import urllib3
import time

# 禁用 InsecureRequestWarning 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 初始化随机数生成器
random.seed(int(time.time() * 1000000) + os.getpid())

# --- 定位根目录 ---
current_file = os.path.abspath(__file__)
root_path = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from config.settings import API_CONFIG, REQUEST_TIMEOUT_API
from core.rules.assertion import AssertionTool
from core.path_manager import TOKEN_DIR, DATA_DIR
from config.data.cookie import CookieManager
from config.data.headers import get_d2c_headers

def run(task_config=None):
    """D2C购物车附加项流程执行器（2步）"""
    msgs = []
    
    try:
        # 1. 加载配置
        payload_path = os.path.join(DATA_DIR, "D2C_Addon.json")
        fjx_path = os.path.join(DATA_DIR, "D2C_Addon_fjxid.json")
        id_file = os.path.join(DATA_DIR, "D2C_Addon_id.json")
        
        with open(payload_path, "r", encoding="utf-8") as f:
            addon_payloads = json.load(f)
        with open(fjx_path, "r", encoding="utf-8") as f:
            fjx_config = json.load(f)
        
        all_rules = AssertionTool.get_rules_dynamically("D2C_Addon", root_path)
        
        # 2. 获取登录账号
        target_mail = ""
        token_file = os.path.join(TOKEN_DIR, "current_tokens.json")
        if os.path.exists(token_file):
            try:
                with open(token_file, "r", encoding="utf-8") as f:
                    tokens_data = json.load(f)
                    if tokens_data:
                        target_mail = list(tokens_data.keys())[0]
            except:
                pass
        
        if not target_mail:
            if all_rules and isinstance(all_rules.get("D2C_Addon_task"), dict):
                target_mail = all_rules["D2C_Addon_task"].get("login_account", "").strip()
        if not target_mail and task_config:
            target_mail = task_config.get("login_account", "").strip()
        if not target_mail:
            target_mail = "qa1tr@2200freefonts.com"
        
        # 3. 获取 Cookie 和 base URL
        d2c_cookie = CookieManager.get_d2c_cookie(target_mail)
        if not d2c_cookie:
            return {"success": False, "message": "缺失D2C Cookie", "status_code": 500, "actual": "缺失D2C Cookie"}
        
        base_url = API_CONFIG.get("BASE_URL", "").rstrip('/')
        endpoints = API_CONFIG.get("ENDPOINTS", {})
        
        # 4. 步骤1：D2C购物车列表调用
        shopping_list_url = f"{base_url}{endpoints.get('D2C_Addon_shoppinglist', '')}"
        shopping_list_payload = addon_payloads.get("D2C_Addon_shoppinglist", {"page": 1})
        shopping_list_headers = get_d2c_headers(d2c_cookie, base_url)
        shopping_list_headers['content-type'] = 'application/json'
        
        response = requests.post(shopping_list_url, json=shopping_list_payload, headers=shopping_list_headers, timeout=REQUEST_TIMEOUT_API, verify=False, proxies={'http': None, 'https': None})
        check = AssertionTool.verify_api_common(response, rules=all_rules.get("D2C_Addon_shoppinglist", {}))
        
        if not check["success"]:
            return {"success": False, "message": f"购物车列表获取失败: {check.get('message', '未知错误')}", "status_code": response.status_code, "actual": check.get('message', '未知错误')}
        
        # 提取 items 中的 id
        res_data = response.json()
        data = res_data.get("data", {})
        items = data.get("items", [])
        cart_ids = [item.get("id") for item in items if item.get("id") and item.get("showtype") != "shop"]
        
        if not cart_ids:
            check_items = data.get("checkItems", []) or res_data.get("checkItems", [])
            cart_ids = [item.get("id") for item in check_items if item.get("id")]
        
        if not cart_ids:
            return {"success": False, "message": "购物车列表为空，无可用ID", "status_code": response.status_code, "actual": "购物车列表为空"}
        
        # 存储ID映射
        id_mapping = {}
        if os.path.exists(id_file):
            try:
                with open(id_file, "r", encoding="utf-8") as f:
                    id_mapping = json.load(f)
            except:
                pass
        id_mapping[target_mail] = cart_ids
        with open(id_file, "w", encoding="utf-8") as f:
            json.dump(id_mapping, f, ensure_ascii=False, indent=2)
        
        msgs.append(f"购物车列表:OK(获取到{len(cart_ids)}个ID)")
        
        # 5. 步骤2：D2C添加附加项
        cart_id = cart_ids[0]
        addon_url = f"{base_url}{endpoints.get('D2C_Addon_add', '')}"
        addon_payload = addon_payloads.get("D2C_Addon_fjxid", {}).copy()
        
        # 动态填充字段
        d2c_items = fjx_config.get("D2C_fjxid", [])
        if d2c_items:
            num_items = random.randint(2, min(10, len(d2c_items)))
            selected_items = random.sample(d2c_items, num_items)
            addon_payload["AdditionalItem"] = ",".join(map(str, selected_items))
        else:
            addon_payload["AdditionalItem"] = ""
        
        addon_payload["cartId"] = cart_id
        
        addon_headers = get_d2c_headers(d2c_cookie, base_url)
        addon_headers['content-type'] = 'application/json'
        
        response = requests.post(addon_url, json=addon_payload, headers=addon_headers, timeout=REQUEST_TIMEOUT_API, verify=False, proxies={'http': None, 'https': None})
        check = AssertionTool.verify_api_common(response, rules=all_rules.get("D2C_Addon_fjxid", {}))
        
        if not check["success"]:
            return {"success": False, "message": f"D2C添加附加项失败: {check.get('message', '未知错误')}", "status_code": response.status_code, "actual": check.get('message', '未知错误')}
        
        msgs.append("D2C添加附加项:OK")
        
        final_result = {"success": True, "message": " | ".join(msgs), "status_code": 200, "actual": f"D2C附加项流程: {' | '.join(msgs)}"}
        
    except Exception as e:
        final_result = {"success": False, "message": str(e), "status_code": 500, "actual": traceback.format_exc()}
    
    print(json.dumps(final_result, ensure_ascii=False))
    return final_result

if __name__ == "__main__":
    task_config = None
    if len(sys.argv) > 1:
        try:
            task_config = json.loads(sys.argv[1])
        except:
            task_config = {}
    run(task_config)
