# -*- coding: utf-8 -*-
# checker/api/d2c_keyword_search.py
# D2C 关键字搜索接口校验（1688）
# 接口特征：GET 请求 + JSONP 响应 + ali.sakuradk2.com 独立域名
import json
import re
import random
import requests
import os
import sys
import time
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
from core.path_manager import TOKEN_DIR
from config.data.cookie import CookieManager


def parse_jsonp(text):
    """解析 JSONP 响应，提取 JSON 数据
    服务端可能返回拼接的双 JSONP：flightHandler1({...})({...})
    使用 raw_decode 只提取第一个完整 JSON 对象
    """
    if not text:
        return None
    text = text.strip()

    # 1. 去掉 callback 前缀，如 "flightHandler1("
    cb_match = re.match(r'^(\w+)\(', text)
    if cb_match:
        inner = text[len(cb_match.group(0)):]  # 去掉 "callbackName("
        # 使用 raw_decode 解析第一个完整 JSON 对象
        try:
            decoder = json.JSONDecoder()
            obj, _ = decoder.raw_decode(inner)
            return obj
        except (json.JSONDecodeError, ValueError):
            pass

    # 2. fallback：尝试直接解析为 JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:

        return None


def run(task_config=None):
    """D2C 关键字搜索接口校验（1688）
    基于 ali.sakuradk2.com/newalibaba_list.php 的 JSONP 接口
    """
    msgs = []

    try:
        # 1. 加载规则
        all_rules = AssertionTool.get_rules_dynamically("d2c_keyword_search", root_path)
        d2c_1688_rules = (all_rules or {}).get("d2c_keyword_1688", {})
        task_rules = (all_rules or {}).get("d2c_keyword_search_task", {})

        # 获取登录账号
        target_mail = task_rules.get("login_account", "").strip()
        if not target_mail:
            target_mail = "qa1tr@2200freefonts.com"

        # 2. 获取 Token（从 current_tokens.json）
        token_val = ""
        token_file = os.path.join(TOKEN_DIR, "current_tokens.json")
        if os.path.exists(token_file):
            try:
                with open(token_file, "r", encoding="utf-8") as f:
                    tokens_data = json.load(f)
                    token_val = tokens_data.get(target_mail, "") or tokens_data.get(target_mail.lower(), "")
                    if not token_val:
                        for key, val in tokens_data.items():
                            if key.strip() == target_mail.strip():
                                token_val = val
                                break
            except Exception:
                pass

        if not token_val:
            final_result = {"success": False, "message": "缺失Token", "status_code": 0, "actual": ""}
            print(json.dumps(final_result, ensure_ascii=False))
            return final_result

        # 去除 Bearer 前缀
        clean_token = token_val.replace("Bearer ", "").strip()

        # 3. 获取 D2C Cookie（必须携带，否则服务端返回空响应）
        d2c_cookie = CookieManager.get_d2c_cookie(target_mail)
        if not d2c_cookie:
            final_result = {"success": False, "message": "缺失D2C Cookie", "status_code": 0, "actual": ""}
            print(json.dumps(final_result, ensure_ascii=False))
            return final_result

        # 3. 构建请求
        endpoints = API_CONFIG.get("ENDPOINTS", {})
        d2c_keyword_url = endpoints.get("d2c_keyword_search_1688", "")

        # 从规则获取搜索参数，使用 curl 中的默认值作为 fallback
        # 支持 keywords 列表（随机选取）或单个 keyword 字符串
        keywords_list = d2c_1688_rules.get("keywords", [])
        if keywords_list:
            keyword = random.choice(keywords_list)
        else:
            keyword = d2c_1688_rules.get("keyword", "手机壳")
        sign = d2c_1688_rules.get("sign", "25d4a6f34cd05d0")
        cross_token = d2c_1688_rules.get("cross_token", "f3c34949710da61c2ee51c037d33f922")
        callback = d2c_1688_rules.get("callback", "flightHandler1")

        params = {
            "page": 1,
            "q": keyword,
            "keyword_cn": "",
            "lang": "1",
            "sort": "0",
            "token": clean_token,
            "sign": sign,
            "cross_token": cross_token,
            "callback": callback,
            "_": int(time.time() * 1000)  # 实时生成时间戳
        }

        headers = {
            "accept": "*/*",
            "accept-language": "zh-CN,zh;q=0.9",
            "referer": "https://b2c.sakuradk2.com/",
            "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "script",
            "sec-fetch-mode": "no-cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
            "Cookie": d2c_cookie
        }
        # 如果规则中配置了自定义 headers，合并覆盖
        if d2c_1688_rules and isinstance(d2c_1688_rules.get("headers"), dict):
            headers.update(d2c_1688_rules["headers"])

        # 4. 发送 GET 请求
        response = requests.get(
            d2c_keyword_url,
            params=params,
            headers=headers,
            timeout=25,
            verify=False,
            proxies={'http': None, 'https': None}
        )

        # 5. 校验 HTTP 状态码
        if response.status_code != 200:
            final_result = {
                "success": False,
                "message": f"1688:FAIL(HTTP {response.status_code})",
                "status_code": response.status_code,
                "actual": f"HTTP状态码: {response.status_code}"
            }
            print(json.dumps(final_result, ensure_ascii=False))
            return final_result

        # 6. 解析 JSONP 响应
        raw_text = response.text
        json_data = parse_jsonp(raw_text)

        if json_data is None:
            final_result = {
                "success": False,
                "message": f"1688:FAIL(JSONP解析失败)",
                "status_code": response.status_code,
                "actual": f"响应内容: {repr(raw_text[:100])}"
            }
            print(json.dumps(final_result, ensure_ascii=False))
            return final_result

        # 7. 校验业务状态
        state = json_data.get("state", "")
        if state != "success":
            final_result = {
                "success": False,
                "message": f"1688:FAIL(state={state})",
                "status_code": response.status_code,
                "expected": "success",
                "actual": str(state)
            }
            print(json.dumps(final_result, ensure_ascii=False))
            return final_result

        # 8. 校验搜索结果非空
        # 响应结构: { "items": { "item": [...], "total_results": N }, "state": "success" }
        items_data = json_data.get("items", {})
        item_list = items_data.get("item", []) if isinstance(items_data, dict) else []
        item_count = len(item_list)
        total_results = items_data.get("total_results", 0) if isinstance(items_data, dict) else 0

        if d2c_1688_rules.get("data_not_empty") and item_count == 0:
            final_result = {
                "success": False,
                "message": f"1688:FAIL(搜索结果为空,keyword={keyword})",
                "status_code": response.status_code,
                "actual": f"搜索结果为空(keyword={keyword})"
            }
            print(json.dumps(final_result, ensure_ascii=False))
            return final_result

        msgs.append(f"1688:OK(keyword={keyword},结果数={item_count},总记录={total_results})")

        # 9. 汇总结果
        final_result = {
            "success": True,
            "message": " | ".join(msgs),
            "status_code": response.status_code,
            "actual": f"D2C关键字搜索结果: {' | '.join(msgs)}"
        }
    except Exception as e:
        final_result = {"success": False, "message": str(e), "actual": traceback.format_exc()}

    print(json.dumps(final_result, ensure_ascii=False))
    return final_result


if __name__ == "__main__":
    run()
