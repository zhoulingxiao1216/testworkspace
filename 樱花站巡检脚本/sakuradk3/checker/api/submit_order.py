# -*- coding: utf-8 -*-
# d:\sakuradk3\checker\api\submit_order.py
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

from config.settings import API_CONFIG
from core.rules.assertion import AssertionTool
from core.path_manager import TOKEN_DIR, DATA_DIR
from config.data.cookie import CookieManager
from config.data.headers import get_d2c_headers, get_b2b_headers

def run(task_config=None):
    """B2B&D2C自助报价单提交流程执行器"""
    msgs = []
    
    try:
        # 1. 加载配置
        payload_path = os.path.join(DATA_DIR, "submit_order.json")
        id_file = os.path.join(DATA_DIR, "D2C_Addon_id.json")
        
        if os.path.exists(payload_path):
            with open(payload_path, "r", encoding="utf-8") as f:
                submit_payloads = json.load(f)
        else:
            submit_payloads = {}
        
        all_rules = AssertionTool.get_rules_dynamically("submit_order", root_path)
        
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
            if all_rules and isinstance(all_rules.get("submit_order_task"), dict):
                target_mail = all_rules["submit_order_task"].get("login_account", "").strip()
        if not target_mail and task_config:
            target_mail = task_config.get("login_account", "").strip()
        if not target_mail:
            target_mail = "qa1tr@2200freefonts.com"
        
        # 3. 获取 Cookie 和 Token
        d2c_cookie = CookieManager.get_d2c_cookie(target_mail)
        b2b_cookie = CookieManager.get_b2b_cookie(target_mail)
        
        b2b_token = ""
        if os.path.exists(token_file):
            try:
                with open(token_file, "r", encoding="utf-8") as f:
                    tokens_data = json.load(f)
                    b2b_token = tokens_data.get(target_mail, "") or tokens_data.get(target_mail.lower(), "")
                    if not b2b_token:
                        for key, val in tokens_data.items():
                            if key.strip() == target_mail.strip():
                                b2b_token = val
                                break
            except:
                pass
        
        base_url = API_CONFIG.get("BASE_URL", "").rstrip('/')
        endpoints = API_CONFIG.get("ENDPOINTS", {})
        
        # D2C的submit_order接口使用base_url（因为endpoint路径是/api_user/d2c_shopping/...）
        # 这与D2C_Addon.py的处理方式一致
        d2c_base_url = base_url
        
        # 读取D2C购物车ID列表（在D2C流程之前读取）
        d2c_cart_ids = []
        if os.path.exists(id_file):
            try:
                with open(id_file, "r", encoding="utf-8") as f:
                    id_mapping = json.load(f)
                    d2c_cart_ids = id_mapping.get(target_mail, [])
            except:
                pass
        
        # 4. D2C流程：独立执行（借鉴add_cart.py的独立调用方式）
        try:
            # D2C步骤1：添加商品收货地址
            if not d2c_cookie:
                msgs.append("D2C添加收货地址:FAIL(缺失D2C Cookie)")
            else:
                save_address_url = f"{d2c_base_url}{endpoints.get('submit_order_saveAddress_D2C', '')}"
                save_address_headers = get_d2c_headers(d2c_cookie, d2c_base_url)
                save_address_headers['content-type'] = 'application/json'
                
                save_address_payload_base = submit_payloads.get("D2C_saveAddress", {}).copy()
                # 检查JSON中是否有传参的cart_id
                json_cart_id = save_address_payload_base.get("cart_id", "")
                
                if json_cart_id and str(json_cart_id).strip():  # 有传参，使用传参
                    # 使用JSON中配置的cart_id
                    try:
                        # 确保cart_id是数字类型（如果API需要）
                        cart_id_value = int(json_cart_id) if str(json_cart_id).isdigit() else json_cart_id
                        save_address_payload = save_address_payload_base.copy()
                        save_address_payload["cart_id"] = cart_id_value
                        
                        response = requests.post(save_address_url, json=save_address_payload, headers=save_address_headers, timeout=25, verify=False, proxies={'http': None, 'https': None})
                        check = AssertionTool.verify_api_common(response, rules=all_rules.get("D2C_saveAddress", {}))
                        if check["success"]:
                            msgs.append("D2C添加收货地址:OK")
                        else:
                            msgs.append(f"D2C添加收货地址:FAIL({check.get('message', '未知错误')})")
                    except Exception as e:
                        msgs.append(f"D2C添加收货地址:FAIL({str(e)})")
                elif d2c_cart_ids:  # 没有传参，走循环
                    success_count = 0
                    for cart_id in d2c_cart_ids:
                        try:
                            save_address_payload = save_address_payload_base.copy()
                            save_address_payload["cart_id"] = cart_id
                            
                            response = requests.post(save_address_url, json=save_address_payload, headers=save_address_headers, timeout=25, verify=False, proxies={'http': None, 'https': None})
                            check = AssertionTool.verify_api_common(response, rules=all_rules.get("D2C_saveAddress", {}))
                            if check["success"]:
                                success_count += 1
                        except:
                            pass
                    
                    if success_count == len(d2c_cart_ids):
                        msgs.append(f"D2C添加收货地址:OK(成功{success_count}个)")
                    else:
                        msgs.append(f"D2C添加收货地址:FAIL(成功{success_count}/{len(d2c_cart_ids)}个)")
                else:
                    msgs.append("D2C添加收货地址:FAIL(未找到购物车ID)")
            
            # D2C步骤2：提交自助报价单（使用与步骤1相同的cartIds）
            if not d2c_cookie:
                msgs.append("D2C提交自助报价单:FAIL(缺失D2C Cookie)")
            else:
                submit_d2c_url = f"{d2c_base_url}{endpoints.get('submit_order_D2C', '')}"
                submit_d2c_headers = get_d2c_headers(d2c_cookie, d2c_base_url)
                submit_d2c_headers['content-type'] = 'application/json'
                
                submit_d2c_payload = submit_payloads.get("D2C_submit", {}).copy()
                # 检查JSON中是否有传参的cartIds
                json_cart_ids = submit_d2c_payload.get("cartIds", [])
                
                if json_cart_ids and isinstance(json_cart_ids, list) and len(json_cart_ids) > 0:  # 有传参，使用传参
                    # 使用JSON中配置的cartIds
                    submit_d2c_payload["cartIds"] = json_cart_ids
                elif d2c_cart_ids:  # 没有传参，使用D2C_Addon_id.json中的所有id
                    submit_d2c_payload["cartIds"] = d2c_cart_ids
                else:
                    msgs.append("D2C提交自助报价单:FAIL(未找到购物车ID)")
                    return
                
                # 打印请求参数
                # print(f"[D2C提交自助报价单] URL: {submit_d2c_url}")
                # print(f"[D2C提交自助报价单] Payload: {json.dumps(submit_d2c_payload, ensure_ascii=False, indent=2)}")
                
                response = requests.post(submit_d2c_url, json=submit_d2c_payload, headers=submit_d2c_headers, timeout=25, verify=False, proxies={'http': None, 'https': None})
                check = AssertionTool.verify_api_common(response, rules=all_rules.get("D2C_submit", {}))
                if check["success"]:
                    msgs.append("D2C提交自助报价单:OK")
                else:
                    msgs.append(f"D2C提交自助报价单:FAIL({check.get('message', '未知错误')})")
        except Exception as e:
            msgs.append(f"D2C流程异常:FAIL({str(e)})")
        
        # 5. B2B流程：独立执行（借鉴add_cart.py的独立调用方式）
        try:
            if not b2b_token or not b2b_cookie:
                msgs.append("B2B提交自助报价单:FAIL(缺失B2B凭据)")
            else:
                submit_b2b_url = f"{base_url}{endpoints.get('submit_order_B2B', '')}"
                submit_b2b_headers = get_b2b_headers(base_url, b2b_token, b2b_cookie)
                submit_b2b_headers['content-type'] = 'application/json'
                
                submit_b2b_payload = submit_payloads.get("B2B_submit", {}).copy()
                
                # 打印请求参数
                # print(f"[B2B提交自助报价单] URL: {submit_b2b_url}")
                # print(f"[B2B提交自助报价单] Payload: {json.dumps(submit_b2b_payload, ensure_ascii=False, indent=2)}")
                
                response = requests.post(submit_b2b_url, json=submit_b2b_payload, headers=submit_b2b_headers, timeout=25, verify=False, proxies={'http': None, 'https': None})
                check = AssertionTool.verify_api_common(response, rules=all_rules.get("B2B_submit", {}))
                if check["success"]:
                    msgs.append("B2B提交自助报价单:OK")
                else:
                    msgs.append(f"B2B提交自助报价单:FAIL({check.get('message', '未知错误')})")
        except Exception as e:
            msgs.append(f"B2B流程异常:FAIL({str(e)})")
        
        # 7. 汇总结果
        all_success = all(":OK" in msg for msg in msgs)
        final_result = {
            "success": all_success,
            "message": " | ".join(msgs),
            "status_code": 200 if all_success else 500,
            "actual": f"自助报价单提交流程: {' | '.join(msgs)}"
        }
        
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
