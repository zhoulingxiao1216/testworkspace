# -*- coding: utf-8 -*-
# checker/api/payment_target.py
# 针对指定报价单号的支付流程（不受 3 天支付间隔限制）
import json
import os
import sys
import requests
import traceback
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

current_file = os.path.abspath(__file__)
root_path = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from config.settings import API_CONFIG, REQUEST_TIMEOUT_API
from core.rules.assertion import AssertionTool
from core.path_manager import TOKEN_DIR, DATA_DIR
from config.data.cookie import CookieManager
from config.data.headers import get_b2b_pay_headers
from checker.api.quote_order_store import update_orderid_after_pay
from checker.api.payment import update_pay_time
from checker.api.payment import update_pay_time

TARGET_CONFIG_FILE = "payment_target.json"


def _load_target_config():
    path = os.path.join(DATA_DIR, TARGET_CONFIG_FILE)
    if not os.path.exists(path):
        raise FileNotFoundError(f"未找到 {TARGET_CONFIG_FILE}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _resolve_account_mail(target_cfg, token_file):
    mail = (target_cfg.get("account_mail") or "").strip()
    if mail:
        return mail
    if os.path.exists(token_file):
        try:
            with open(token_file, "r", encoding="utf-8") as f:
                tokens_data = json.load(f)
                if tokens_data:
                    return list(tokens_data.keys())[0]
        except Exception:
            pass
    return "mxnrq@airsworld.net"


def _get_b2b_credentials(target_mail):
    token_file = os.path.join(TOKEN_DIR, "current_tokens.json")
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
        except Exception:
            pass
    return b2b_token, b2b_cookie, token_file


def _build_pay_headers(api_base_url, b2b_token, b2b_cookie, pay_api_cfg):
    header_cfg = pay_api_cfg.get("headers") or {}
    b2b_site = pay_api_cfg.get("b2b_site_origin") or API_CONFIG.get("url_B2B_pc", "").rstrip("/")
    return get_b2b_pay_headers(
        api_base_url,
        b2b_site,
        b2b_token,
        b2b_cookie,
        currency=header_cfg.get("currency", "USD"),
        language=header_cfg.get("language", "korean"),
        nation=header_cfg.get("nation", "Korea"),
        rate=str(header_cfg.get("rate", "0.16")),
        logintype=header_cfg.get("logintype", "user"),
    )


def _pay_quote(api_base_url, endpoints, quote_no, b2b_token, b2b_cookie, target_cfg, all_rules):
    pay_api_cfg = target_cfg.get("pay_api") or {}
    pay_url = (pay_api_cfg.get("url") or "").strip()
    if not pay_url:
        pay_url = f"{api_base_url}{endpoints.get('payment_B2B_pay', '')}"

    headers = _build_pay_headers(api_base_url, b2b_token, b2b_cookie, pay_api_cfg)
    payload = dict(pay_api_cfg.get("json") or {})
    payload["quote_no_arr"] = quote_no

    response = requests.post(
        pay_url,
        json=payload,
        headers=headers,
        timeout=REQUEST_TIMEOUT_API,
        verify=False,
        proxies={"http": None, "https": None},
    )
    check = AssertionTool.verify_api_common(response, rules=all_rules.get("B2B_pay", {}))
    return check, response


def run(task_config=None):
    msgs = []
    try:
        target_cfg = _load_target_config()
        quote_no = (target_cfg.get("quote_no") or "").strip()
        if not quote_no:
            raise ValueError("payment_target.json 中 quote_no 为空")

        token_file = os.path.join(TOKEN_DIR, "current_tokens.json")
        target_mail = _resolve_account_mail(target_cfg, token_file)
        b2b_token, b2b_cookie, _ = _get_b2b_credentials(target_mail)
        orderid_file = os.path.join(DATA_DIR, "payment_orderid.json")

        api_base_url = API_CONFIG.get("BASE_URL", "").rstrip("/")
        endpoints = API_CONFIG.get("ENDPOINTS", {})
        all_rules = AssertionTool.get_rules_dynamically("payment_target", root_path) or {}

        if not b2b_token or not b2b_cookie:
            msgs.append("B2B报价单支付:FAIL(缺失B2B凭据)")
        else:
            check, response = _pay_quote(
                api_base_url, endpoints, quote_no, b2b_token, b2b_cookie, target_cfg, all_rules
            )
            if check["success"]:
                order_no = update_orderid_after_pay(orderid_file, target_mail, quote_no)
                msgs.append(f"B2B报价单支付:OK({quote_no}→{order_no})")
                if target_cfg.get("force_pay") or target_cfg.get("skip_three_day_check"):
                    update_pay_time(orderid_file, target_mail, "B2B")
            else:
                detail = check.get("message", "未知错误")
                try:
                    body = response.json()
                    if body.get("message"):
                        detail = f"{detail} | api_msg={body.get('message')}"
                except Exception:
                    pass
                msgs.append(f"B2B报价单支付:FAIL({detail})")

        all_success = all(":OK" in msg for msg in msgs)
        final_result = {
            "success": all_success,
            "message": " | ".join(msgs),
            "status_code": 200 if all_success else 500,
            "actual": f"指定报价单支付: {' | '.join(msgs)}",
        }
    except Exception as e:
        final_result = {
            "success": False,
            "message": str(e),
            "status_code": 500,
            "actual": traceback.format_exc(),
        }

    print(json.dumps(final_result, ensure_ascii=False))
    return final_result


if __name__ == "__main__":
    task_config = None
    if len(sys.argv) > 1:
        try:
            task_config = json.loads(sys.argv[1])
        except Exception:
            task_config = {}
    run(task_config)
