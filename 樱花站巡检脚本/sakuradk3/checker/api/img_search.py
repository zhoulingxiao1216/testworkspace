# -*- coding: utf-8 -*-
# d:\sakuradk3\checker\api\img_search.py
import json
import requests
import os
import sys
import time
import traceback
import base64

# --- 定位根目录 ---
current_file = os.path.abspath(__file__)
root_path = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from config.settings import API_CONFIG
from config.data.headers import get_base_headers
from core.rules.assertion import AssertionTool  # 引入全能断言类
from core.path_manager import TOKEN_DIR

def run(task_config=None):
    # 1. 初始化
    results_status = {"B2B": False, "D2C": False}
    msgs = []
    final_result = {
        "success": False,
        "message": "",
        "status_code": 0,
        "expected": "优先JSON校验，无JSON则自动降级公共双200",
        "actual": ""
    }

    try:
        # 2. 获取约定规则 (img_search.json)
        # 只要 config/rules/img_search.json 存在，all_rules 就会包含其内容
        all_rules = AssertionTool.get_rules_dynamically("img_search", root_path)

        # 加载本地图片用于 B2B 搜索
        local_img_path = os.path.join(root_path, "config", "data", "img_search.jpg")
        if not os.path.exists(local_img_path):
            raise FileNotFoundError(f"未找到图片: {local_img_path}")

        with open(local_img_path, "rb") as f:
            img_base64 = base64.b64encode(f.read()).decode('utf-8')
            img_data = f"data:image/jpeg;base64,{img_base64}"

        # 3. 获取 Token 逻辑（支持轮询多个 token）
        # 优先从规则配置获取账号，其次从 API_CONFIG.ACCOUNT_LIST 第一个，最后使用默认值
        target_mail = None
        if all_rules and isinstance(all_rules.get("img_search_task"), dict):
            target_mail = all_rules["img_search_task"].get("login_account")
        
        if not target_mail and API_CONFIG.get("ACCOUNT_LIST"):
            target_mail = API_CONFIG["ACCOUNT_LIST"][0].get("mail")
        
        if not target_mail:
            target_mail = "qa1tr@2200freefonts.com"  # 默认值
        
        safe_mail = target_mail.replace("@", "_").replace(".", "_")
        token_dir = TOKEN_DIR  # 使用统一的 token 目录
        token_list = []  # 用于存储所有可用的 token
        
        # 優先從 current_tokens.json 讀取所有 token（用於輪詢）
        current_token_file = os.path.join(token_dir, "current_tokens.json")
        if os.path.exists(current_token_file):
            try:
                with open(current_token_file, "r", encoding="utf-8") as f:
                    tokens_map = json.load(f)
                # 收集所有 token（用於 D2C 輪詢）
                token_list = [token for token in tokens_map.values() if token]
                # B2B 使用指定账号的 token
                token_val = tokens_map.get(target_mail, "") or tokens_map.get(target_mail.lower(), "")
            except Exception as e:
                # 如果讀取失敗，繼續使用舊邏輯
                pass
        
        # 如果 current_tokens.json 中沒有，則使用舊的 txt 文件邏輯
        if not token_val and os.path.exists(token_dir):
            matching_files = sorted([f for f in os.listdir(token_dir) if f.startswith(safe_mail) and f.endswith(".txt")])
            if matching_files:
                with open(os.path.join(token_dir, matching_files[-1]), "r", encoding="utf-8") as f:
                    token_val = f.read().strip()
                    if token_val and token_val not in token_list:
                        token_list.append(token_val)

        # --- 任务 1: B2B 请求与校验 ---
        base_url = API_CONFIG.get("BASE_URL", "").rstrip('/')
        b2b_url = f"{base_url}{API_CONFIG['ENDPOINTS'].get('image_search_B2B')}"
        b2b_headers = get_base_headers(base_url)
        b2b_headers.update({'authorization': token_val, 'content-type': 'application/json'})
        
        b2b_payload = {
            "page": 1, "limit": 20, "is_search": "1", "language": "ja",
            "img_url": img_data,
            "filter": "isOnePsale"
        }
        res_b = requests.post(b2b_url, headers=b2b_headers, json=b2b_payload, timeout=25, proxies={'http': None, 'https': None})
        
        # 获取 B2B 专用规则
        b2b_rules = all_rules.get("B2B_img") if all_rules else None
        # 如果 b2b_rules 为 None，则内部自动执行公共双 200
        check_b = AssertionTool.verify_api_common(res_b, rules=b2b_rules)
        
        if check_b["success"]:
            results_status["B2B"] = True
            tag = "规则" if b2b_rules else "双200"
            msgs.append(f"B2B:OK({tag})")
        else:
            msgs.append(f"B2B:FAIL({check_b['message']})")

        # --- 任务 2: D2C 请求与校验（支持 token 轮询） ---
        d2c_base_url = API_CONFIG["ENDPOINTS"].get("image_search_D2C")
        d2c_rules = all_rules.get("D2C_img") if all_rules else None
        
        # 准备基础参数（从规则读取，无则使用默认值）
        base_params = {
            "imageUrl": (d2c_rules.get("imageUrl") if d2c_rules else None) or "http://hk-sakuradk2.oss-cn-hongkong.aliyuncs.com/img/202601/20260106160236466_min.jpg",
            "page": 1,
            "sign": (d2c_rules.get("sign") if d2c_rules else None) or "5e55ded552957a2",
            "cross_token": (d2c_rules.get("cross_token") if d2c_rules else None) or "a0a188a29b6bd5fd809a5055cfb459e6",
            "callback": (d2c_rules.get("callback") if d2c_rules else None) or "flightHandler1",
            "_": int(time.time() * 1000)  # 强制实时生成时间戳
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Sakuradk3/1.0",
            "Referer": "https://www.sakuradk2.com"
        }
        if d2c_rules and isinstance(d2c_rules.get("headers"), dict):
            headers.update(d2c_rules["headers"])

        # Token 轮询：如果有多个 token，每个都尝试一次
        # 优先使用规则中配置的 token / tokens，其次才使用 current_tokens.json 中的 token
        d2c_tokens_to_try = []

        # 1）优先：img_search.json -> D2C_img.tokens / D2C_img.token
        if d2c_rules:
            # 支持配置为数组：["token1", "token2", ...]
            tokens_from_rules = d2c_rules.get("tokens")
            if isinstance(tokens_from_rules, list):
                d2c_tokens_to_try.extend([t for t in tokens_from_rules if t])

            # 兼容单个 token 字段
            single_token = d2c_rules.get("token")
            if single_token:
                d2c_tokens_to_try.append(single_token)

        # 2）其次：使用 current_tokens.json / txt 中登录得到的 token（轮询所有）
        if not d2c_tokens_to_try:
            if token_list:
                # token_list 可能已有重复，这里去重保持顺序
                seen = set()
                unique_tokens = []
                for t in token_list:
                    if t and t not in seen:
                        seen.add(t)
                        unique_tokens.append(t)
                d2c_tokens_to_try = unique_tokens
            elif token_val:
                d2c_tokens_to_try = [token_val]
        
        d2c_check_results = []
        d2c_success_count = 0
        
        for idx, d2c_token in enumerate(d2c_tokens_to_try):
            if not d2c_token:
                continue
                
            params = base_params.copy()
            params["token"] = d2c_token
            
            try:
                res_d = requests.get(d2c_base_url, params=params, headers=headers, timeout=20, verify=False, proxies={'http': None, 'https': None})
            except Exception as req_err:
                d2c_check_results.append(f"Token{idx+1}:请求异常({str(req_err)})")
                continue
            
            # 执行校验
            check_d = AssertionTool.verify_api_common(res_d, rules=d2c_rules)
            
            if check_d["success"]:
                d2c_success_count += 1
                d2c_check_results.append(f"Token{idx+1}:OK")
                results_status["D2C"] = True
            else:
                error_detail = check_d.get("message", "未知错误")
                # 记录详细错误信息
                response_preview = repr(res_d.text[:50]) if res_d.text else "(空响应)"
                error_msg = f"Token{idx+1}:FAIL({error_detail[:50]})"
                if "响应为空" in error_detail or "Expecting value" in error_detail:
                    error_msg += f" | 响应内容: {response_preview}"
                d2c_check_results.append(error_msg)
        
        # 汇总 D2C 结果
        if d2c_tokens_to_try:
            if d2c_success_count > 0:
                msgs.append(f"D2C:OK({d2c_success_count}/{len(d2c_tokens_to_try)}成功) {'|'.join(d2c_check_results)}")
            else:
                msgs.append(f"D2C:FAIL(全部失败) {'|'.join(d2c_check_results)}")
        else:
            msgs.append("D2C:FAIL(无可用Token)")

        # 4. 汇总结果
        final_result["success"] = all(results_status.values())
        final_result["message"] = " | ".join(msgs)
        final_result["status_code"] = res_b.status_code
        
        try:
            b2b_total = res_b.json().get("data", {}).get("totalRecords", "N/A")
            d2c_summary = f"D2C轮询: {d2c_success_count}/{len(d2c_tokens_to_try) if d2c_tokens_to_try else 0}成功"
            if d2c_check_results:
                d2c_summary += f" | {'|'.join(d2c_check_results[:3])}"  # 只显示前3个结果
            final_result["actual"] = f"B2B记录: {b2b_total} | {d2c_summary}"
        except:
            final_result["actual"] = f"B2B解析失败 | D2C轮询: {d2c_success_count}/{len(d2c_tokens_to_try) if d2c_tokens_to_try else 0}成功"

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