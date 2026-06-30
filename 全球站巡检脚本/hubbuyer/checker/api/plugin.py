# -*- coding: utf-8 -*-
# d:\sakuradk3\checker\api\plugin.py
import json
import os
import sys
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

from config.settings import API_CONFIG, REQUEST_TIMEOUT_API
from core.rules.assertion import AssertionTool
from core.path_manager import TOKEN_DIR, DATA_DIR
from config.data.cookie import CookieManager
from config.data.headers import get_d2c_headers, get_b2b_headers

def prepare_form_data(payload):
    """准备表单数据：转换为 URL 编码的表单数据"""
    safe_payload = {}
    for k, v in payload.items():
        if v is None:
            safe_payload[k] = ""
        elif isinstance(v, (list, dict)):
            # 列表或字典：转为 JSON 字符串
            safe_payload[k] = json.dumps(v, ensure_ascii=False)
        else:
            # 其他类型：转为字符串
            safe_payload[k] = str(v)
    
    # 使用 urllib.parse.urlencode 进行 URL 编码
    return urllib.parse.urlencode(safe_payload, doseq=True, quote_via=urllib.parse.quote)

def run(task_config=None):
    """B2B&D2C插件添加1688/taobao商品流程执行器"""
    msgs = []
    
    try:
        # 1. 加载配置
        payload_path = os.path.join(DATA_DIR, "plugin.json")
        
        if os.path.exists(payload_path):
            with open(payload_path, "r", encoding="utf-8") as f:
                plugin_payloads = json.load(f)
        else:
            plugin_payloads = {}
        
        all_rules = AssertionTool.get_rules_dynamically("plugin", root_path)
        
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
            if all_rules and isinstance(all_rules.get("plugin_task"), dict):
                target_mail = all_rules["plugin_task"].get("login_account", "").strip()
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
        
        # 4. B2B流程：独立执行
        try:
            # B2B步骤1：插件添加1688商品
            if not b2b_token or not b2b_cookie:
                msgs.append("B2B插件添加1688商品:FAIL(缺失B2B凭据)")
            else:
                b2b_1688_url = f"{base_url}{endpoints.get('plugin_B2B', '')}"
                b2b_1688_payload = plugin_payloads.get("B2B_1688", {}).copy()
                
                # 动态添加 loginToken
                if "loginToken" not in b2b_1688_payload:
                    b2b_1688_payload["loginToken"] = b2b_token
                
                # 获取商品信息用于动态生成 referer 和 currpath
                item_id = b2b_1688_payload.get("ItemID", "")
                item_url = b2b_1688_payload.get("ItemURL", "")
                b2b_1688_headers = get_b2b_headers(base_url, b2b_token, b2b_cookie, item_id=item_id, item_url=item_url)
                # 插件请求使用表单数据格式
                b2b_1688_headers['content-type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
                
                # 准备表单数据
                form_data = prepare_form_data(b2b_1688_payload)
                
                response = requests.post(b2b_1688_url, data=form_data, headers=b2b_1688_headers, timeout=REQUEST_TIMEOUT_API, verify=False, proxies={'http': None, 'https': None})
                check = AssertionTool.verify_api_common(response, rules=all_rules.get("B2B_1688", {}))
                if check["success"]:
                    msgs.append("B2B插件添加1688商品:OK")
                else:
                    msgs.append(f"B2B插件添加1688商品:FAIL({check.get('message', '未知错误')})")
            
            # B2B步骤2：插件添加淘宝商品
            if b2b_token and b2b_cookie:
                b2b_taobao_url = f"{base_url}{endpoints.get('plugin_B2B', '')}"
                b2b_taobao_payload = plugin_payloads.get("B2B_taobao", {}).copy()
                
                # 动态添加 loginToken
                if "loginToken" not in b2b_taobao_payload:
                    b2b_taobao_payload["loginToken"] = b2b_token
                
                # 获取商品信息用于动态生成 referer 和 currpath
                item_id = b2b_taobao_payload.get("ItemID", "")
                item_url = b2b_taobao_payload.get("ItemURL", "")
                b2b_taobao_headers = get_b2b_headers(base_url, b2b_token, b2b_cookie, item_id=item_id, item_url=item_url)
                # 插件请求使用表单数据格式
                b2b_taobao_headers['content-type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
                
                # 准备表单数据
                form_data = prepare_form_data(b2b_taobao_payload)
                
                response = requests.post(b2b_taobao_url, data=form_data, headers=b2b_taobao_headers, timeout=REQUEST_TIMEOUT_API, verify=False, proxies={'http': None, 'https': None})
                check = AssertionTool.verify_api_common(response, rules=all_rules.get("B2B_taobao", {}))
                if check["success"]:
                    msgs.append("B2B插件添加淘宝商品:OK")
                else:
                    msgs.append(f"B2B插件添加淘宝商品:FAIL({check.get('message', '未知错误')})")
        except Exception as e:
            msgs.append(f"B2B流程异常:FAIL({str(e)})")
        
        # 5. D2C流程：独立执行
        try:
            # D2C步骤：插件添加1688代发商品
            if not d2c_cookie:
                msgs.append("D2C插件添加1688商品:FAIL(缺失D2C Cookie)")
            else:
                d2c_1688_url = f"{base_url}{endpoints.get('plugin_D2C', '')}"
                d2c_1688_payload = plugin_payloads.get("D2C_1688", {}).copy()
                
                # 动态添加 loginToken（从 D2C Cookie 中提取）
                # D2C Cookie 中包含 loginToken，get_d2c_headers 会自动处理
                
                # 获取商品 URL 用于动态生成 referer
                item_url = d2c_1688_payload.get("ItemURL", "")
                d2c_1688_headers = get_d2c_headers(d2c_cookie, base_url, item_url=item_url)
                
                # 准备表单数据
                form_data = prepare_form_data(d2c_1688_payload)
                
                response = requests.post(d2c_1688_url, data=form_data, headers=d2c_1688_headers, timeout=REQUEST_TIMEOUT_API, verify=False, proxies={'http': None, 'https': None})
                check = AssertionTool.verify_api_common(response, rules=all_rules.get("D2C_1688", {}))
                if check["success"]:
                    msgs.append("D2C插件添加1688商品:OK")
                else:
                    msgs.append(f"D2C插件添加1688商品:FAIL({check.get('message', '未知错误')})")
        except Exception as e:
            msgs.append(f"D2C流程异常:FAIL({str(e)})")
        
        # 6. 汇总结果
        all_success = all(":OK" in msg for msg in msgs)
        final_result = {
            "success": all_success,
            "message": " | ".join(msgs),
            "status_code": 200 if all_success else 500,
            "actual": f"插件添加商品流程: {' | '.join(msgs)}"
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
