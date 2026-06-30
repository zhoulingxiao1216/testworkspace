# -*- coding: utf-8 -*-
# d:\sakuradk3\checker\api\login.py
import json
import sys
import os
import requests
import argparse
from datetime import datetime

# --- 必须在 import core 之前手动初始化路径 ---
current_file = os.path.abspath(__file__)
# 向上跳三级找到 d:\sakuradk3
root_path = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

import core.path_manager  # 现在可以正常导入了
from core.path_manager import TOKEN_DIR 
from config.settings import API_CONFIG, ENV_TYPE, REQUEST_TIMEOUT_API
from config.data.headers import get_base_headers
from core.rules.assertion import AssertionTool  # 引入断言工具类

def run_login_check(task_config=None, custom_accounts=None):
    """
    执行登录检查
    
    Args:
        task_config: 任务配置（可选，用于批量检查）
        custom_accounts: 自定义账号列表（可选，优先级高于配置文件）
    """
    # 1. 约定加载规则：匹配 config/rules/login.json
    all_rules = AssertionTool.get_rules_dynamically("login")
    # login 脚本通常只有一个业务，直接取 rules 节点或全量
    specific_rules = all_rules if all_rules else None

    base_url = API_CONFIG.get("BASE_URL", "").rstrip('/')
    login_path = API_CONFIG.get("ENDPOINTS", {}).get("login", "")
    full_url = f"{base_url}{login_path}"
    headers = get_base_headers(base_url)
    
    # 优先使用自定义账号，其次使用配置文件中的账号
    if custom_accounts:
        accounts = custom_accounts
    else:
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
        # 支持 "mail" 和 "email" 两种字段名
        mail = account.get("mail") or account.get("email", "未知账号")
        try:
            response = requests.post(full_url, headers=headers, json=account, timeout=REQUEST_TIMEOUT_API, proxies={'http': None, 'https': None})
            last_status_code = response.status_code
            
            # --- 使用统一断言工具 ---
            # 如果没有 login.json，则自动走公共“双200”校验
            check_res = AssertionTool.verify_api_common(response, rules=specific_rules)

            if check_res["success"]:
                # 优先从 Set-Cookie 中提取 pro_auth_token
                token_val = None
                
                # 方式1: 从 response.cookies 中提取（推荐，自动解析）
                if response.cookies:
                    token_val = response.cookies.get("pro_auth_token")
                
                # 方式2: 如果方式1失败，从响应头 Set-Cookie 中手动解析
                if not token_val:
                    set_cookie_header = response.headers.get("Set-Cookie", "")
                    if "pro_auth_token=" in set_cookie_header:
                        # 解析 Set-Cookie 头，提取 pro_auth_token 的值
                        # 格式: pro_auth_token=xxx; Domain=...; Max-Age=...; Path=...; Secure; SameSite=...
                        try:
                            # 找到 pro_auth_token= 后面的值，直到遇到分号或空格
                            start_idx = set_cookie_header.find("pro_auth_token=")
                            if start_idx != -1:
                                start_idx += len("pro_auth_token=")
                                end_idx = set_cookie_header.find(";", start_idx)
                                if end_idx == -1:
                                    end_idx = len(set_cookie_header)
                                token_val = set_cookie_header[start_idx:end_idx].strip()
                        except Exception:
                            pass
                
                # 方式3: 如果前两种方式都失败，尝试从响应体 JSON 中提取（向后兼容）
                if not token_val:
                    try:
                        res_json = response.json()
                        token_val = res_json.get("data", {}).get("token")
                    except Exception:
                        pass
                
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

    # --- 汇总结果 ---
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
    # 判断是否为批量模式（通过 ScriptRunner 调用）
    # 批量模式：sys.argv[1] 是 JSON 配置字符串
    # 独立模式：使用 argparse 解析命令行参数
    if len(sys.argv) > 1:
        # 批量模式：尝试解析 sys.argv[1] 为 JSON
        try:
            task_config = json.loads(sys.argv[1])
            # 批量模式下，直接调用 run_login_check，使用配置文件中的账号
            run_login_check(task_config=task_config)
            # 批量模式执行完毕，直接退出
            sys.exit(0)
        except (json.JSONDecodeError, ValueError):
            # 如果不是有效的 JSON，可能是独立模式的参数，继续使用 argparse
            pass
    
    # 独立模式：使用 argparse 解析命令行参数
    custom_accounts = None
    parser = argparse.ArgumentParser(description="登录接口测试工具")
    parser.add_argument("--email", type=str, help="登录邮箱（支持 --email 或 --mail）")
    parser.add_argument("--mail", type=str, help="登录邮箱（支持 --email 或 --mail）")
    parser.add_argument("--password", type=str, help="登录密码")
    parser.add_argument("--account-json", type=str, help="账号JSON字符串，例如: '{\"email\":\"test@example.com\",\"password\":\"123456\"}'")
    parser.add_argument("--account-file", type=str, help="账号JSON文件路径，文件内容应为账号列表数组")
    
    args = parser.parse_args()
    
    # 方式1: 通过 --account-file 从文件读取
    if args.account_file:
        if os.path.exists(args.account_file):
            with open(args.account_file, "r", encoding="utf-8") as f:
                custom_accounts = json.load(f)
                if not isinstance(custom_accounts, list):
                    custom_accounts = [custom_accounts]
        else:
            print(json.dumps({"success": False, "message": f"账号文件不存在: {args.account_file}"}, ensure_ascii=False))
            sys.exit(1)
    
    # 方式2: 通过 --account-json 从JSON字符串读取
    elif args.account_json:
        try:
            account_data = json.loads(args.account_json)
            custom_accounts = [account_data] if isinstance(account_data, dict) else account_data
        except json.JSONDecodeError as e:
            print(json.dumps({"success": False, "message": f"JSON格式错误: {str(e)}"}, ensure_ascii=False))
            sys.exit(1)
    
    # 方式3: 通过 --email/--mail 和 --password 单独指定
    elif args.email or args.mail or args.password:
        email = args.email or args.mail
        if not email or not args.password:
            print(json.dumps({"success": False, "message": "请同时提供 --email/--mail 和 --password 参数"}, ensure_ascii=False))
            sys.exit(1)
        custom_accounts = [{"email": email, "password": args.password}]
    
    # 如果没有提供自定义参数，则使用配置文件中的账号
    run_login_check(custom_accounts=custom_accounts)