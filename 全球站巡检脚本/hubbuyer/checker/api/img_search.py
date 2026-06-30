# -*- coding: utf-8 -*-
# d:\sakuradk3\checker\api\img_search.py
import json
import requests
import os
import sys
import traceback
import random

# --- 定位根目录 ---
current_file = os.path.abspath(__file__)
root_path = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from config.settings import API_CONFIG, REQUEST_TIMEOUT_API
from config.data.headers import get_b2b_img_search_headers
from config.data.cookie import CookieManager
from core.rules.assertion import AssertionTool  # 引入全能断言类
from core.path_manager import TOKEN_DIR, DATA_DIR


def run(task_config=None):
    # 1. 初始化
    results_status = {"B2B": False}
    msgs = []
    final_result = {
        "success": False,
        "message": "",
        "status_code": 0,
        "expected": "优先JSON校验，无JSON则自动降级公共双200",
        "actual": ""
    }

    try:
        # 2. 从 config/data/img_search.json 读取参数配置
        data_file_path = os.path.join(DATA_DIR, "img_search.json")
        if not os.path.exists(data_file_path):
            final_result["success"] = False
            final_result["message"] = "B2B:FAIL(未找到数据配置文件)"
            final_result["actual"] = f"配置文件不存在: {data_file_path}"
            print(json.dumps(final_result, ensure_ascii=False))
            return final_result
        
        with open(data_file_path, "r", encoding="utf-8") as f:
            data_config = json.load(f)
        
        # 获取 B2B 配置
        b2b_config = data_config.get("B2B", {})
        
        # 获取请求参数
        b2b_params = b2b_config.get("params", {}).copy()
        
        # 获取图片 URL 列表并随机选择
        image_urls = b2b_config.get("image_urls", [])
        if image_urls:
            selected_image_url = random.choice(image_urls)
            b2b_params["image_url"] = selected_image_url
        else:
            selected_image_url = ""
        
        # 3. 从 config/rules/img_search.json 读取断言规则
        all_rules = AssertionTool.get_rules_dynamically("img_search", root_path)
        b2b_rules = all_rules.get("B2B_img", {}) if all_rules else {}

        # 4. 获取 Token 逻辑
        # 优先从规则配置获取账号，其次从 API_CONFIG.ACCOUNT_LIST 第一个，最后使用默认值
        target_mail = None
        if all_rules and isinstance(all_rules.get("img_search_task"), dict):
            target_mail = all_rules["img_search_task"].get("login_account")
        
        if not target_mail and API_CONFIG.get("ACCOUNT_LIST"):
            target_mail = API_CONFIG["ACCOUNT_LIST"][0].get("mail") or API_CONFIG["ACCOUNT_LIST"][0].get("email")
        
        safe_mail = target_mail.replace("@", "_").replace(".", "_") if target_mail else ""
        token_dir = TOKEN_DIR  # 使用统一的 token 目录
        
        # 从 current_tokens.json 读取 token
        token_val = ""
        current_token_file = os.path.join(token_dir, "current_tokens.json")
        tokens_map = {}
        if os.path.exists(current_token_file):
            try:
                with open(current_token_file, "r", encoding="utf-8") as f:
                    tokens_map = json.load(f)
            except Exception as e:
                pass
        
        # 如果配置的账号在 current_tokens.json 中找不到 token，则使用 current_tokens.json 中的第一个账号
        if tokens_map:
            if target_mail:
                # 尝试使用配置的账号匹配 token（支持多种匹配方式）
                token_val = tokens_map.get(target_mail, "") or tokens_map.get(target_mail.lower(), "")
                # 尝试去除空格匹配
                if not token_val:
                    for key, val in tokens_map.items():
                        if key.strip() == target_mail.strip():
                            token_val = val
                            target_mail = key  # 更新为实际匹配到的账号
                            break
            
            # 如果配置的账号找不到 token，使用 current_tokens.json 中的第一个账号
            if not token_val and tokens_map:
                target_mail = list(tokens_map.keys())[0]
                token_val = tokens_map[target_mail]
                safe_mail = target_mail.replace("@", "_").replace(".", "_")
        
        # 如果 current_tokens.json 中没有账号，使用默认值
        if not target_mail:
            target_mail = "qa1tr@2200freefonts.com"  # 默认值
            safe_mail = target_mail.replace("@", "_").replace(".", "_")
        
        # 如果 current_tokens.json 中沒有，則使用舊的 txt 文件邏輯
        if not token_val and os.path.exists(token_dir):
            matching_files = sorted([f for f in os.listdir(token_dir) if f.startswith(safe_mail) and f.endswith(".txt")])
            if matching_files:
                with open(os.path.join(token_dir, matching_files[-1]), "r", encoding="utf-8") as f:
                    token_val = f.read().strip()

        # 4. B2B 图搜请求与校验
        base_url = API_CONFIG.get("BASE_URL", "").rstrip('/')
        # 使用关键词搜索 API 的 endpoint（图搜使用相同的接口，通过 image_url 参数区分）
        b2b_url = f"{base_url}/api_ali/product/keyword"
        
        # 获取 B2B Cookie
        b2b_cookie = CookieManager.get_b2b_cookie(target_mail)
        
        res_b = None
        if not token_val:
            msgs.append(f"B2B:FAIL(未找到Token,账号:{target_mail})")
        elif not b2b_cookie:
            msgs.append(f"B2B:FAIL(未找到Cookie,账号:{target_mail})")
        else:
            # 使用 headers.py 中的函数构建请求头
            b2b_headers = get_b2b_img_search_headers(
                base_url=base_url,
                token=token_val,
                cookie_str=b2b_cookie
            )
            
            # B2B 图搜请求参数（从数据文件读取，已包含随机选择的 image_url）
            res_b = requests.post(b2b_url, headers=b2b_headers, json=b2b_params, timeout=REQUEST_TIMEOUT_API, verify=False, proxies={'http': None, 'https': None})
            
            # 获取 B2B 专用规则（用于校验）
            b2b_check_rules = {"status_code": b2b_rules.get("status_code", 200)} if b2b_rules else None
            # 如果 b2b_check_rules 为 None，则内部自动执行公共双 200
            check_b = AssertionTool.verify_api_common(res_b, rules=b2b_check_rules)
            
            if check_b["success"]:
                results_status["B2B"] = True
                tag = "规则" if b2b_rules else "双200"
                msgs.append(f"B2B:OK({tag})")
            else:
                msgs.append(f"B2B:FAIL({check_b['message']})")

        # --- D2C 相关代码已注释 ---
        # # --- 任务 2: D2C 请求与校验（支持 token 轮询） ---
        # d2c_base_url = API_CONFIG.get("BASE_URL", "").rstrip('/')
        # d2c_endpoint = API_CONFIG["ENDPOINTS"].get("image_search_D2C", "")
        # d2c_url = f"{d2c_base_url}{d2c_endpoint}" if d2c_endpoint else None
        # d2c_rules = all_rules.get("D2C_img", {}) if all_rules else {}
        # 
        # # 获取 D2C Cookie
        # d2c_cookie = CookieManager.get_d2c_cookie(target_mail)
        # 
        # res_d = None
        # if d2c_url:
        #     if not d2c_cookie:
        #         msgs.append(f"D2C:FAIL(未找到Cookie,账号:{target_mail})")
        #     else:
        #         # 使用 D2C headers（需要导入 get_d2c_headers）
        #         # from config.data.headers import get_d2c_headers
        #         # d2c_headers = get_d2c_headers(d2c_cookie, d2c_base_url)
        #         # d2c_headers['content-type'] = 'application/json'
        #         
        #         # 获取 D2C 图搜参数（从数据文件读取）
        #         # d2c_config = data_config.get("D2C", {})
        #         # d2c_params = d2c_config.get("params", {}).copy()
        #         # d2c_image_urls = d2c_config.get("image_urls", [])
        #         # if d2c_image_urls:
        #         #     selected_d2c_image_url = random.choice(d2c_image_urls)
        #         #     d2c_params["image_url"] = selected_d2c_image_url
        #         
        #         # D2C 图搜请求
        #         # res_d = requests.post(d2c_url, headers=d2c_headers, json=d2c_params, timeout=REQUEST_TIMEOUT_API, verify=False, proxies={'http': None, 'https': None})
        #         
        #         # 获取 D2C 专用规则（用于校验）
        #         # d2c_check_rules = {"status_code": d2c_rules.get("status_code", 200)} if d2c_rules else None
        #         # check_d = AssertionTool.verify_api_common(res_d, rules=d2c_check_rules)
        #         
        #         # if check_d["success"]:
        #         #     results_status["D2C"] = True
        #         #     tag = "规则" if d2c_rules else "双200"
        #         #     msgs.append(f"D2C:OK({tag})")
        #         # else:
        #         #     msgs.append(f"D2C:FAIL({check_d['message']})")
        # else:
        #     msgs.append("D2C:未配置endpoint，跳过")

        # 5. 汇总结果
        final_result["success"] = results_status.get("B2B", False)
        final_result["message"] = " | ".join(msgs)
        final_result["status_code"] = res_b.status_code if res_b else 0
        
        # 构建实际结果信息
        if results_status.get("B2B", False) and res_b:
            try:
                res_json = res_b.json()
                b2b_total = "N/A"
                
                # 根据实际API响应结构解析：{code: 200, data: {data: {totalRecords: 686, data: [...]}}}
                # 结构1: 三层嵌套结构 data.data.data
                data_level1 = res_json.get("data", {})
                if isinstance(data_level1, dict):
                    data_level2 = data_level1.get("data", {})
                    if isinstance(data_level2, dict):
                        # 商品列表在 data.data.data
                        product_list = data_level2.get("data", [])
                        if isinstance(product_list, list):
                            b2b_total = len(product_list)
                        else:
                            # 如果 data.data.data 不是列表，尝试其他字段
                            for key in ["list", "items", "products", "goods"]:
                                if key in data_level2 and isinstance(data_level2[key], list):
                                    b2b_total = len(data_level2[key])
                                    break
                    # 结构2: 两层嵌套，data.data 直接是列表
                    elif isinstance(data_level2, list):
                        b2b_total = len(data_level2)
                # 结构3: data 直接是列表
                elif isinstance(data_level1, list):
                    b2b_total = len(data_level1)
                
                image_info = f" | 使用图片: {selected_image_url.split('/')[-1]}" if selected_image_url else ""
                final_result["actual"] = f"B2B记录: {b2b_total}{image_info}"
            except Exception as e:
                image_info = f" | 使用图片: {selected_image_url.split('/')[-1]}" if selected_image_url else ""
                final_result["actual"] = f"B2B解析失败: {str(e)}{image_info}"
        else:
            final_result["actual"] = "B2B:未执行"

    except Exception as e:
        final_result["success"] = False
        final_result["message"] = f"脚本崩溃: {str(e)}"
        final_result["actual"] = traceback.format_exc()

    # 最終結果輸出（必須是最後一行，runner 會取最後一行作為結果）
    final_output = json.dumps(final_result, ensure_ascii=False)
    print(final_output)
    return final_result

if __name__ == "__main__":
    run()
