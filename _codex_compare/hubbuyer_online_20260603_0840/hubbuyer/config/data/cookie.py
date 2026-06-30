# -*- coding: utf-8 -*-
# d:\sakuradk3\config\data\cookie.py
import json
import os
from core.path_manager import TOKEN_DIR

class CookieManager:
    @staticmethod
    def get_d2c_cookie(target_mail):
        """
        获取 D2C Cookie 字符串（基于实际请求格式）
        从 current_tokens.json 获取 token，生成包含 loginToken 的完整 Cookie
        """
        token_file = os.path.join(TOKEN_DIR, "current_tokens.json")
        if not os.path.exists(token_file):
            return ""

        try:
            with open(token_file, "r", encoding="utf-8") as f:
                tokens_data = json.load(f)
                target_key = target_mail.strip()
                raw_token = tokens_data.get(target_key, "")
                
                # 如果精确匹配失败，尝试去除空格匹配
                if not raw_token:
                    for key, val in tokens_data.items():
                        if key.strip() == target_key:
                            raw_token = val
                            break
                
                if raw_token:
                    # 去除 Bearer 前缀，返回纯 token
                    clean_jwt = raw_token.replace("Bearer ", "").strip()
                    # D2C Cookie：基于实际请求格式，包含必要的 cookie
                    # 注意：实际请求中 loginToken 可能出现多次，最后一次有效
                    cookie_template = (
                        f"PHPSESSID=qokjm6u9opg4qoo68pn3q48g2d; "
                        f"server_login_token={clean_jwt}; "
                        f"loginToken={clean_jwt}"
                    )
                    return cookie_template
        except Exception as e:
            import sys
            print(f"CookieManager.get_d2c_cookie 异常: {e}", file=sys.stderr)
        return ""

    @staticmethod
    def get_b2b_cookie(target_mail):
        """获取 B2B Cookie 字符串（基于 postman 格式）"""
        token_file = os.path.join(TOKEN_DIR, "current_tokens.json")
        if not os.path.exists(token_file):
            return ""

        try:
            with open(token_file, "r", encoding="utf-8") as f:
                tokens_data = json.load(f)
                target_key = target_mail.strip()
                raw_token = tokens_data.get(target_key, "")
                
                # 如果精确匹配失败，尝试去除空格匹配
                if not raw_token:
                    for key, val in tokens_data.items():
                        if key.strip() == target_key:
                            raw_token = val
                            break
                
                if raw_token:
                    clean_jwt = raw_token.replace("Bearer ", "").strip()
                    # B2B Cookie：完整版本，包含所有必要的 cookie（基于 postman）
                    cookie_template = (
                        f"PHPSESSID=qokjm6u9opg4qoo68pn3q48g2d; "
                        f"server_login_token={clean_jwt}; "
                        f"loginToken={clean_jwt}; "
                        f"login_token={clean_jwt}; "
                        f"Hm_lvt_6a2d0dadf560f4632634bc304b87a5dd=1768350161"
                    )
                    return cookie_template
        except Exception as e:
            import sys
            print(f"CookieManager.get_b2b_cookie 异常: {e}", file=sys.stderr)
        return ""