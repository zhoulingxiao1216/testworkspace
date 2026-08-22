# -*- coding: utf-8 -*-
# d:\sakuradk3\checker\api\payment.py
import json
import os
import sys
import requests
import traceback
import urllib3
from datetime import datetime, timedelta

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
from config.data.headers import get_b2b_headers, get_b2b_pay_headers
from checker.api.quote_order_store import (
    get_audited_pending_pay_quote,
    update_orderid_after_pay,
    resolve_target_mail,
)

def should_pay(orderid_file, target_mail, payment_type):
    """检查是否应该执行支付（每3天支付一次）"""
    if not os.path.exists(orderid_file):
        return True  # 文件不存在，首次执行，允许支付
    
    try:
        with open(orderid_file, "r", encoding="utf-8") as f:
            orderid_mapping = json.load(f)
        
        if target_mail not in orderid_mapping:
            return True  # 邮箱不存在，首次执行，允许支付
        
        last_pay_time_str = orderid_mapping[target_mail].get(f"last_pay_time_{payment_type}")
        if not last_pay_time_str:
            return True  # 没有支付记录，允许支付
        
        # 解析上次支付时间
        last_pay_time = datetime.strptime(last_pay_time_str, "%Y-%m-%d %H:%M:%S")
        current_time = datetime.now()
        
        # 检查是否超过3天
        days_diff = (current_time - last_pay_time).days
        return days_diff >= 3
    except:
        return True  # 解析失败，允许支付

def update_pay_time(orderid_file, target_mail, payment_type):
    """更新支付时间"""
    orderid_mapping = {}
    if os.path.exists(orderid_file):
        try:
            with open(orderid_file, "r", encoding="utf-8") as f:
                orderid_mapping = json.load(f)
        except:
            pass
    
    if target_mail not in orderid_mapping:
        orderid_mapping[target_mail] = {"B2B": [], "D2C": []}
    
    # 更新支付时间
    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    orderid_mapping[target_mail][f"last_pay_time_{payment_type}"] = current_time_str
    
    with open(orderid_file, "w", encoding="utf-8") as f:
        json.dump(orderid_mapping, f, ensure_ascii=False, indent=2)

def run(task_config=None):
    """B2B&D2C报价单支付流程执行器"""
    msgs = []
    
    try:
        # 1. 加载配置
        payload_path = os.path.join(DATA_DIR, "payment.json")
        orderid_file = os.path.join(DATA_DIR, "payment_orderid.json")
        
        if os.path.exists(payload_path):
            with open(payload_path, "r", encoding="utf-8") as f:
                payment_payloads = json.load(f)
        else:
            payment_payloads = {}
        
        all_rules = AssertionTool.get_rules_dynamically("payment", root_path)
        
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
            if all_rules and isinstance(all_rules.get("payment_task"), dict):
                target_mail = all_rules["payment_task"].get("login_account", "").strip()
        if not target_mail and task_config:
            target_mail = task_config.get("login_account", "").strip()
        if not target_mail:
            target_mail = "qa1tr@2200freefonts.com"
        
        # 3. 获取 Cookie 和 Token
        # d2c_cookie = CookieManager.get_d2c_cookie(target_mail)  # D2C流程已注释
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
        
        # 4. B2B流程：独立执行
        try:
            # B2B步骤1：获取报价单列表
            if not b2b_token or not b2b_cookie:
                msgs.append("B2B报价单列表:FAIL(缺失B2B凭据)")
            else:
                b2b_list_url = f"{base_url}{endpoints.get('payment_B2B_list', '')}"
                b2b_list_headers = get_b2b_headers(base_url, b2b_token, b2b_cookie)
                b2b_list_headers['content-type'] = 'application/json'
                
                # 使用新的请求参数格式
                b2b_list_payload = payment_payloads.get("B2B_list", {}).copy()
                # 确保参数格式正确：{"quote_no":"","pay_status_id":0,"logistics_config_id":0,"status":2000,"date":"","page":1,"limit":20}
                if not b2b_list_payload:
                    b2b_list_payload = {
                        "quote_no": "",
                        "pay_status_id": 0,
                        "logistics_config_id": 0,
                        "status": 2000,
                        "date": "",
                        "page": 1,
                        "limit": 20
                    }
                
                response = requests.post(b2b_list_url, json=b2b_list_payload, headers=b2b_list_headers, timeout=REQUEST_TIMEOUT_API, verify=False, proxies={'http': None, 'https': None})
                check = AssertionTool.verify_api_common(response, rules=all_rules.get("B2B_list", {}))
                
                if check["success"]:
                    msgs.append("B2B报价单列表:OK")
                    # 提取 quote_no 值
                    try:
                        response_data = response.json()
                        quote_nos = []
                        # 新的响应格式：data.data.data[]
                        data_list = response_data.get("data", {}).get("data", {}).get("data", [])
                        if not data_list:
                            # 兼容旧格式：data.list 或 data[]
                            data_list = response_data.get("data", {}).get("list", []) or response_data.get("data", []) or []
                        
                        for item in data_list:
                            quote_no = item.get("quote_no")
                            if quote_no:
                                quote_nos.append(quote_no)
                        
                        # 保存到 payment_orderid.json（按邮箱账号存储，使用quote_no）
                        orderid_mapping = {}
                        if os.path.exists(orderid_file):
                            try:
                                with open(orderid_file, "r", encoding="utf-8") as f:
                                    orderid_mapping = json.load(f)
                            except:
                                pass
                        
                        if target_mail not in orderid_mapping:
                            orderid_mapping[target_mail] = {"B2B": [], "D2C": []}
                        orderid_mapping[target_mail]["B2B"] = quote_nos
                        with open(orderid_file, "w", encoding="utf-8") as f:
                            json.dump(orderid_mapping, f, ensure_ascii=False, indent=2)
                    except Exception as e:
                        pass  # 提取失败不影响流程
                else:
                    msgs.append(f"B2B报价单列表:FAIL({check.get('message', '未知错误')})")
            
            # B2B步骤2：支付已通过报价单审核的报价单（支付后再走代购订单审核）
            if b2b_token and b2b_cookie:
                round_quote = get_audited_pending_pay_quote(orderid_file, target_mail)
                if not round_quote:
                    msgs.append("B2B报价单支付:FAIL(未找到待支付报价单，请先完成报价单审核)")
                else:
                    b2b_pay_url = f"{base_url}{endpoints.get('payment_B2B_pay', '')}"
                    b2b_site = (API_CONFIG.get("url_B2B_pc") or "").rstrip("/")
                    b2b_pay_headers = get_b2b_pay_headers(
                        base_url, b2b_site, b2b_token, b2b_cookie,
                        currency="USD", language="korean", nation="Korea", rate="0.16",
                    )
                    b2b_pay_payload = payment_payloads.get("B2B_pay", {}).copy()
                    b2b_pay_payload["quote_no_arr"] = round_quote

                    response = requests.post(
                        b2b_pay_url, json=b2b_pay_payload, headers=b2b_pay_headers,
                        timeout=REQUEST_TIMEOUT_API, verify=False,
                        proxies={"http": None, "https": None},
                    )
                    check = AssertionTool.verify_api_common(response, rules=all_rules.get("B2B_pay", {}))
                    if check["success"]:
                        order_no = update_orderid_after_pay(orderid_file, target_mail, round_quote)
                        update_pay_time(orderid_file, target_mail, "B2B")
                        msgs.append(f"B2B报价单支付:OK({round_quote}→{order_no})")
                    else:
                        detail = check.get("message", "未知错误")
                        try:
                            body = response.json()
                            if body.get("message"):
                                detail = f"{detail} | api_msg={body.get('message')}"
                        except Exception:
                            pass
                        msgs.append(f"B2B报价单支付:FAIL({round_quote}: {detail})")
        except Exception as e:
            msgs.append(f"B2B流程异常:FAIL({str(e)})")
        
        # ========== D2C流程已注释 ==========
        # # 5. D2C流程：独立执行
        # try:
        #     # D2C步骤1：获取报价单列表
        #     if not d2c_cookie:
        #         msgs.append("D2C报价单列表:FAIL(缺失D2C Cookie)")
        #     else:
        #         d2c_list_url = f"{base_url}{endpoints.get('payment_D2C_list', '')}"
        #         d2c_list_headers = get_d2c_headers(d2c_cookie, base_url)
        #         d2c_list_headers['content-type'] = 'application/json'
        #         
        #         d2c_list_payload = payment_payloads.get("D2C_list", {}).copy()
        #         
        #         response = requests.post(d2c_list_url, json=d2c_list_payload, headers=d2c_list_headers, timeout=REQUEST_TIMEOUT_API, verify=False, proxies={'http': None, 'https': None})
        #         check = AssertionTool.verify_api_common(response, rules=all_rules.get("D2C_list", {}))
        #         
        #         if check["success"]:
        #             msgs.append("D2C报价单列表:OK")
        #             # 提取 orderid（quoteStateName 为 "確認済み" 的订单）
        #             try:
        #                 response_data = response.json()
        #                 orderids = []
        #                 # 根据实际响应结构提取数据
        #                 data_list = response_data.get("data", {}).get("list", []) or response_data.get("data", []) or []
        #                 for item in data_list:
        #                     if item.get("quoteStateName") == "確認済み":
        #                         orderid = item.get("orderid")
        #                         if orderid:
        #                             orderids.append(orderid)
        #                 
        #                 # 保存到 payment_orderid.json（按邮箱账号存储）
        #                 orderid_mapping = {}
        #                 if os.path.exists(orderid_file):
        #                     try:
        #                         with open(orderid_file, "r", encoding="utf-8") as f:
        #                             orderid_mapping = json.load(f)
        #                     except:
        #                         pass
        #                 
        #                 if target_mail not in orderid_mapping:
        #                     orderid_mapping[target_mail] = {"B2B": [], "D2C": []}
        #                 orderid_mapping[target_mail]["D2C"] = orderids
        #                 with open(orderid_file, "w", encoding="utf-8") as f:
        #                     json.dump(orderid_mapping, f, ensure_ascii=False, indent=2)
        #             except Exception as e:
        #                 pass  # 提取失败不影响流程
        #         else:
        #             msgs.append(f"D2C报价单列表:FAIL({check.get('message', '未知错误')})")
        #     
        #     # D2C步骤2：支付报价单（每3天支付一次）
        #     if d2c_cookie:
        #         # 检查是否应该支付（每3天支付一次）
        #         if not should_pay(orderid_file, target_mail, "D2C"):
        #             msgs.append("D2C报价单支付:跳过(距离上次支付未满3天)")
        #         else:
        #             # 读取存储的 orderid（根据邮箱账号）
        #             d2c_orderids = []
        #             if os.path.exists(orderid_file):
        #                 try:
        #                     with open(orderid_file, "r", encoding="utf-8") as f:
        #                         orderid_mapping = json.load(f)
        #                         if target_mail in orderid_mapping:
        #                             d2c_orderids = orderid_mapping[target_mail].get("D2C", [])
        #                 except:
        #                     pass
        #             
        #             if not d2c_orderids:
        #                 msgs.append("D2C报价单支付:FAIL(未找到订单ID)")
        #             else:
        #                 d2c_pay_url = f"{base_url}{endpoints.get('payment_D2C_pay', '')}"
        #                 d2c_pay_headers = get_d2c_headers(d2c_cookie, base_url)
        #                 d2c_pay_headers['content-type'] = 'application/json'
        #                 
        #                 d2c_pay_payload = payment_payloads.get("D2C_pay", {}).copy()
        #                 d2c_pay_payload["orderIds"] = d2c_orderids[0]  # 使用第一个订单ID
        #                 
        #                 response = requests.post(d2c_pay_url, json=d2c_pay_payload, headers=d2c_pay_headers, timeout=REQUEST_TIMEOUT_API, verify=False, proxies={'http': None, 'https': None})
        #                 check = AssertionTool.verify_api_common(response, rules=all_rules.get("D2C_pay", {}))
        #                 if check["success"]:
        #                     msgs.append("D2C报价单支付:OK")
        #                     # 更新支付时间
        #                     update_pay_time(orderid_file, target_mail, "D2C")
        #                 else:
        #                     msgs.append(f"D2C报价单支付:FAIL({check.get('message', '未知错误')})")
        # except Exception as e:
        #     msgs.append(f"D2C流程异常:FAIL({str(e)})")
        
        # 6. 汇总结果
        # 判断成功：所有消息都包含:OK，或者包含"跳过(距离上次支付未满3天)"（这是正常的3天间隔控制）
        def is_step_success(msg):
            """判断单个步骤是否成功"""
            if ":OK" in msg:
                return True
            elif ":FAIL" in msg:
                return False
            else:
                return False
        
        all_success = all(is_step_success(msg) for msg in msgs)
        final_result = {
            "success": all_success,
            "message": " | ".join(msgs),
            "status_code": 200 if all_success else 500,
            "actual": f"报价单支付流程: {' | '.join(msgs)}"
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
