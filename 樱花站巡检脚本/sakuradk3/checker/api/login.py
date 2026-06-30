# -*- coding: utf-8 -*-
# d:\sakuradk3\checker\api\login.py
import json
import sys
import os
import requests
from datetime import datetime

# --- 必须在 import core 之前手动初始化路径 ---
current_file = os.path.abspath(__file__)
# 向上跳三级找到 d:\sakuradk3
root_path = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import core.path_manager  # 现在可以正常导入了
from core.path_manager import TOKEN_DIR 
from config.settings import API_CONFIG, ENV_TYPE
from config.data.headers import get_base_headers
from core.rules.assertion import AssertionTool  # 引入断言工具类

def run_login_check(task_config=None):
    # 1. 约定加载规则：匹配 config/rules/login.json
    all_rules = AssertionTool.get_rules_dynamically("login")
    # login 脚本通常只有一个业务，直接取 rules 节点或全量
    specific_rules = all_rules if all_rules else None

    base_url = API_CONFIG.get("BASE_URL", "").rstrip('/')
    login_path = API_CONFIG.get("ENDPOINTS", {}).get("login", "")
    full_url = f"{base_url}{login_path}"
    headers = get_base_headers(base_url)
    accounts = API_CONFIG.get("ACCOUNT_LIST", [])

    success_count = 0
    results_summary = []
    token_dir = os.path.join(root_path, "token")
    if not os.path.exists(token_dir):
        os.makedirs(token_dir)

    all_current_tokens = {}
    last_valid_token = None
    last_status_code = 0

    # --- 循环处理账号 ---
    for account in accounts:
        mail = account.get("mail", "未知账号")
        try:
            response = requests.post(full_url, headers=headers, json=account, timeout=15, proxies={'http': None, 'https': None})
            last_status_code = response.status_code
            
            # --- 使用统一断言工具 ---
            # 如果没有 login.json，则自动走公共“双200”校验
            check_res = AssertionTool.verify_api_common(response, rules=specific_rules)

            if check_res["success"]:
                res_json = response.json()
                # 提取 Token（约定 token 路径，也可从 rules 提取）
                token_val = res_json.get("data", {}).get("token")
                
                success_count += 1
                last_valid_token = token_val
                all_current_tokens[mail] = token_val
                
                # 保存 Token 文件
                safe_mail = mail.replace("@", "_").replace(".", "_")
                timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M')
                file_path = os.path.join(token_dir, f"{safe_mail}_{timestamp}.txt")
                
                # 清理旧文件并写入
                for old_file in os.listdir(token_dir):
                    if old_file.startswith(f"{safe_mail}_"):
                        try: os.remove(os.path.join(token_dir, old_file))
                        except: pass
                
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(str(token_val))
                
                results_summary.append(f"{mail}:OK")
            else:
                results_summary.append(f"{mail}:ERR({check_res['message']})")
                
        except Exception as e:
            results_summary.append(f"{mail}:异常({type(e).__name__})")

    # 保存汇总 Token
    if all_current_tokens:
        summary_path = os.path.join(token_dir, "current_tokens.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(all_current_tokens, f, ensure_ascii=False, indent=4)

    # --- 汇总结果 ---a
    total = len(accounts)
    final_result = {
        "success": success_count == total and total > 0,
        "message": f"【{ENV_TYPE}】" + " | ".join(results_summary),
        "status_code": last_status_code,
        "token": last_valid_token
    }
    print(json.dumps(final_result, ensure_ascii=False))
    return final_result

if __name__ == "__main__":
    run_login_check()