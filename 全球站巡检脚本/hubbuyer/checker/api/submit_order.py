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

from config.settings import API_CONFIG, REQUEST_TIMEOUT_API
from core.rules.assertion import AssertionTool
from core.path_manager import TOKEN_DIR, DATA_DIR
from config.data.cookie import CookieManager
from config.data.headers import get_b2b_headers
# from config.data.headers import get_d2c_headers  # D2C流程已注释，不再需要

def run(task_config=None):
    """B2B委托报价提交流程执行器"""
    msgs = []
    
    try:
        # 1. 加载配置
        payload_path = os.path.join(DATA_DIR, "submit_order.json")
        b2b_id_file = os.path.join(DATA_DIR, "B2B_Addon_id.json")
        
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
        
        # 读取B2B购物车ID列表（从B2B_Addon_id.json读取）
        b2b_cart_detail_ids = []
        if os.path.exists(b2b_id_file):
            try:
                with open(b2b_id_file, "r", encoding="utf-8") as f:
                    id_mapping = json.load(f)
                    id_list = id_mapping.get(target_mail, [])
                    # 提取所有id值组成数组
                    if isinstance(id_list, list):
                        b2b_cart_detail_ids = [item.get("id") for item in id_list if isinstance(item, dict) and item.get("id")]
            except:
                pass
        
        # ========== D2C流程已注释 ==========
        # # D2C的submit_order接口使用base_url（因为endpoint路径是/api_user/d2c_shopping/...）
        # # 这与D2C_Addon.py的处理方式一致
        # d2c_base_url = base_url
        # 
        # # 读取D2C购物车ID列表（在D2C流程之前读取）
        # d2c_cart_ids = []
        # id_file = os.path.join(DATA_DIR, "D2C_Addon_id.json")
        # if os.path.exists(id_file):
        #     try:
        #         with open(id_file, "r", encoding="utf-8") as f:
        #             id_mapping = json.load(f)
        #             d2c_cart_ids = id_mapping.get(target_mail, [])
        #     except:
        #         pass
        # 
        # # 4. D2C流程：独立执行（借鉴add_cart.py的独立调用方式）
        # try:
        #     # D2C步骤1：添加商品收货地址
        #     if not d2c_cookie:
        #         msgs.append("D2C添加收货地址:FAIL(缺失D2C Cookie)")
        #     else:
        #         save_address_url = f"{d2c_base_url}{endpoints.get('submit_order_saveAddress_D2C', '')}"
        #         save_address_headers = get_d2c_headers(d2c_cookie, d2c_base_url)
        #         save_address_headers['content-type'] = 'application/json'
        #         
        #         save_address_payload_base = submit_payloads.get("D2C_saveAddress", {}).copy()
        #         # 检查JSON中是否有传参的cart_id
        #         json_cart_id = save_address_payload_base.get("cart_id", "")
        #         
        #         if json_cart_id and str(json_cart_id).strip():  # 有传参，使用传参
        #             # 使用JSON中配置的cart_id
        #             try:
        #                 # 确保cart_id是数字类型（如果API需要）
        #                 cart_id_value = int(json_cart_id) if str(json_cart_id).isdigit() else json_cart_id
        #                 save_address_payload = save_address_payload_base.copy()
        #                 save_address_payload["cart_id"] = cart_id_value
        #                 
        #                 response = requests.post(save_address_url, json=save_address_payload, headers=save_address_headers, timeout=REQUEST_TIMEOUT_API, verify=False, proxies={'http': None, 'https': None})
        #                 check = AssertionTool.verify_api_common(response, rules=all_rules.get("D2C_saveAddress", {}))
        #                 if check["success"]:
        #                     msgs.append("D2C添加收货地址:OK")
        #                 else:
        #                     msgs.append(f"D2C添加收货地址:FAIL({check.get('message', '未知错误')})")
        #             except Exception as e:
        #                 msgs.append(f"D2C添加收货地址:FAIL({str(e)})")
        #         elif d2c_cart_ids:  # 没有传参，走循环
        #             success_count = 0
        #             for cart_id in d2c_cart_ids:
        #                 try:
        #                     save_address_payload = save_address_payload_base.copy()
        #                     save_address_payload["cart_id"] = cart_id
        #                     
        #                     response = requests.post(save_address_url, json=save_address_payload, headers=save_address_headers, timeout=REQUEST_TIMEOUT_API, verify=False, proxies={'http': None, 'https': None})
        #                     check = AssertionTool.verify_api_common(response, rules=all_rules.get("D2C_saveAddress", {}))
        #                     if check["success"]:
        #                         success_count += 1
        #                 except:
        #                     pass
        #             
        #             if success_count == len(d2c_cart_ids):
        #                 msgs.append(f"D2C添加收货地址:OK(成功{success_count}个)")
        #             else:
        #                 msgs.append(f"D2C添加收货地址:FAIL(成功{success_count}/{len(d2c_cart_ids)}个)")
        #         else:
        #             msgs.append("D2C添加收货地址:FAIL(未找到购物车ID)")
        #     
        #     # D2C步骤2：提交自助报价单（使用与步骤1相同的cartIds）
        #     if not d2c_cookie:
        #         msgs.append("D2C提交自助报价单:FAIL(缺失D2C Cookie)")
        #     else:
        #         submit_d2c_url = f"{d2c_base_url}{endpoints.get('submit_order_D2C', '')}"
        #         submit_d2c_headers = get_d2c_headers(d2c_cookie, d2c_base_url)
        #         submit_d2c_headers['content-type'] = 'application/json'
        #         
        #         submit_d2c_payload = submit_payloads.get("D2C_submit", {}).copy()
        #         # 检查JSON中是否有传参的cartIds
        #         json_cart_ids = submit_d2c_payload.get("cartIds", [])
        #         
        #         if json_cart_ids and isinstance(json_cart_ids, list) and len(json_cart_ids) > 0:  # 有传参，使用传参
        #             # 使用JSON中配置的cartIds
        #             submit_d2c_payload["cartIds"] = json_cart_ids
        #         elif d2c_cart_ids:  # 没有传参，使用D2C_Addon_id.json中的所有id
        #             submit_d2c_payload["cartIds"] = d2c_cart_ids
        #         else:
        #             msgs.append("D2C提交自助报价单:FAIL(未找到购物车ID)")
        #             return
        #         
        #         # 打印请求参数
        #         # print(f"[D2C提交自助报价单] URL: {submit_d2c_url}")
        #         # print(f"[D2C提交自助报价单] Payload: {json.dumps(submit_d2c_payload, ensure_ascii=False, indent=2)}")
        #         
        #         response = requests.post(submit_d2c_url, json=submit_d2c_payload, headers=submit_d2c_headers, timeout=REQUEST_TIMEOUT_API, verify=False, proxies={'http': None, 'https': None})
        #         check = AssertionTool.verify_api_common(response, rules=all_rules.get("D2C_submit", {}))
        #         if check["success"]:
        #             msgs.append("D2C提交自助报价单:OK")
        #         else:
        #             msgs.append(f"D2C提交自助报价单:FAIL({check.get('message', '未知错误')})")
        # except Exception as e:
        #     msgs.append(f"D2C流程异常:FAIL({str(e)})")
        
        # 4. B2B流程：独立执行
        try:
            if not b2b_token or not b2b_cookie:
                msgs.append("B2B提交委托报价:FAIL(缺失B2B凭据)")
            else:
                submit_b2b_url = f"{base_url}{endpoints.get('submit_order_B2B', '')}"
                submit_b2b_headers = get_b2b_headers(base_url, b2b_token, b2b_cookie)
                submit_b2b_headers['content-type'] = 'application/json'
                
                # 构建B2B提交请求参数
                # 委托报价格式：{"quote_type":2,"logistics_config_id":26,"cart_detail_id_arr":[2467]}
                submit_b2b_payload = {}
                
                # 从JSON配置中读取基础参数
                b2b_submit_config = submit_payloads.get("B2B_submit", {})
                
                # 设置quote_type（委托报价固定为2，防止误提交为自助报价）
                quote_type = b2b_submit_config.get("quote_type", b2b_submit_config.get("quoteType", 2))
                try:
                    quote_type = int(quote_type)
                except (TypeError, ValueError):
                    msgs.append(f"B2B提交委托报价:FAIL(quote_type配置无效:{quote_type})")
                    submit_b2b_payload = None

                if submit_b2b_payload is not None and quote_type != 2:
                    msgs.append(f"B2B提交委托报价:FAIL(quote_type应为2，实际{quote_type})")
                    submit_b2b_payload = None

                if submit_b2b_payload is not None:
                    submit_b2b_payload["quote_type"] = quote_type
                
                # 设置logistics_config_id（优先使用配置，默认26）
                if submit_b2b_payload is not None:
                    submit_b2b_payload["logistics_config_id"] = b2b_submit_config.get("logistics_config_id", b2b_submit_config.get("ExpressID", 26))
                
                # 设置cart_detail_id_arr
                # 优先使用JSON配置中的cart_detail_id_arr
                if submit_b2b_payload is not None:
                    json_cart_detail_id_arr = b2b_submit_config.get("cart_detail_id_arr", [])
                    if json_cart_detail_id_arr and isinstance(json_cart_detail_id_arr, list) and len(json_cart_detail_id_arr) > 0:
                        # 使用JSON中配置的cart_detail_id_arr
                        submit_b2b_payload["cart_detail_id_arr"] = json_cart_detail_id_arr
                    elif b2b_cart_detail_ids:
                        # 使用B2B_Addon_id.json中的所有id
                        submit_b2b_payload["cart_detail_id_arr"] = b2b_cart_detail_ids
                    else:
                        msgs.append("B2B提交委托报价:FAIL(未找到购物车ID)")
                        # 未找到购物车ID，不执行请求
                        submit_b2b_payload = None
                
                # 只有在有有效payload时才执行请求
                if submit_b2b_payload:
                    # 打印请求参数（调试用）
                    # print(f"[B2B提交委托报价] URL: {submit_b2b_url}")
                    # print(f"[B2B提交委托报价] Payload: {json.dumps(submit_b2b_payload, ensure_ascii=False, indent=2)}")
                    
                    response = requests.post(submit_b2b_url, json=submit_b2b_payload, headers=submit_b2b_headers, timeout=REQUEST_TIMEOUT_API, verify=False, proxies={'http': None, 'https': None})
                    check = AssertionTool.verify_api_common(response, rules=all_rules.get("B2B_submit", {}))
                    if check["success"]:
                        # 提取订单号（quote_no）并记录
                        quote_no = ""
                        try:
                            resp_data = response.json()
                            # 尝试多种响应结构提取 quote_no
                            data_field = resp_data.get("data", {})
                            if isinstance(data_field, dict):
                                quote_no = data_field.get("quote_no", "") or data_field.get("quoteNo", "") or data_field.get("order_no", "")
                            
                            if quote_no:
                                # 保存到 submit_order_record.json
                                record_file = os.path.join(DATA_DIR, "submit_order_record.json")
                                record_data = {}
                                if os.path.exists(record_file):
                                    try:
                                        with open(record_file, "r", encoding="utf-8") as f:
                                            record_data = json.load(f)
                                    except:
                                        pass
                                
                                if target_mail not in record_data:
                                    record_data[target_mail] = []
                                
                                from datetime import datetime
                                record_data[target_mail].insert(0, {
                                    "quote_no": quote_no,
                                    "submit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                })
                                # 只保留最近20条记录
                                record_data[target_mail] = record_data[target_mail][:20]
                                
                                with open(record_file, "w", encoding="utf-8") as f:
                                    json.dump(record_data, f, ensure_ascii=False, indent=2)
                                
                                msgs.append(f"B2B提交委托报价:OK(订单号:{quote_no})")
                            else:
                                msgs.append("B2B提交委托报价:OK(未解析到订单号)")
                        except Exception as e:
                            msgs.append(f"B2B提交委托报价:OK(订单号提取异常:{str(e)})")
                    else:
                        msgs.append(f"B2B提交委托报价:FAIL({check.get('message', '未知错误')})")
        except Exception as e:
            msgs.append(f"B2B流程异常:FAIL({str(e)})")
        
        # 7. 汇总结果
        all_success = all(":OK" in msg for msg in msgs)
        final_result = {
            "success": all_success,
            "message": " | ".join(msgs),
            "status_code": 200 if all_success else 500,
            "actual": f"委托报价提交流程: {' | '.join(msgs)}"
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
