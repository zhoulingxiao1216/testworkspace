# -*- coding: utf-8 -*-
# checker/api/order_audit.py
# 后台报价单审核：审核本轮新提交的 BJ 报价单（支付前）
import json
import os
import sys
import requests
import traceback

current_file = os.path.abspath(__file__)
root_path = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from config.settings import REQUEST_TIMEOUT_API, ENV_TYPE, API_CONFIG
from config.data.login_data import ACCOUNTS_POOL
from core.path_manager import DATA_DIR
from checker.api.quote_order_store import (
    get_latest_submitted_quote,
    mark_quote_audited,
    resolve_target_mail,
    convert_quote_to_order_no,
    revert_order_to_quote_no,
)

LOGIN_PATH = "/admin/login/login"
AUDIT_PATH = "/admin_b2b/order/purchaseStatusUpdate"


def admin_api_base_url():
    return (API_CONFIG.get("BASE_URL") or "https://api.hubbuyer.com").rstrip("/")


def admin_web_origin():
    return (API_CONFIG.get("url_ADMIN") or "https://admin.hubbuyer.com/").rstrip("/")


def normalize_admin_token(token):
    return (token or "").replace("Bearer ", "").strip()


def admin_base_headers(admin_site_origin=None):
    origin = (admin_site_origin or admin_web_origin()).rstrip("/")
    return {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "logintype": "admin",
        "origin": origin,
        "referer": origin + "/",
    }


def build_admin_auth_headers(token, admin_site_origin=None, extra_headers=None):
    origin = (admin_site_origin or admin_web_origin()).rstrip("/")
    headers = admin_base_headers(origin)
    if extra_headers:
        headers.update(extra_headers)
    headers["origin"] = origin
    headers["referer"] = origin + "/"
    headers["logintype"] = "admin"
    headers["content-type"] = "application/json"
    headers["authorization"] = normalize_admin_token(token)
    return headers


def _admin_login():
    admin_cfg = ACCOUNTS_POOL.get(ENV_TYPE, {}).get("admin", {})
    account = admin_cfg.get("account", "")
    password = admin_cfg.get("password", "")
    url = admin_api_base_url() + LOGIN_PATH
    resp = requests.post(
        url,
        headers=admin_base_headers(),
        json={"account": account, "password": password},
        timeout=REQUEST_TIMEOUT_API,
        proxies={"http": None, "https": None},
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("code") != 200:
        raise RuntimeError(f"后台登录失败: code={body.get('code')} msg={body.get('message')}")
    token = normalize_admin_token(body.get("data", {}).get("login_token"))
    if not token:
        raise RuntimeError("后台登录成功但未返回 login_token")
    return token


def _convert_quote_to_order_no(quote_no):
    return convert_quote_to_order_no(quote_no)


def _revert_order_to_quote_no(order_no):
    return revert_order_to_quote_no(order_no)


def _audit_quote(token, quote_no):
    url = admin_api_base_url() + AUDIT_PATH
    headers = build_admin_auth_headers(token)
    resp = requests.post(
        url,
        headers=headers,
        json={"order_no": quote_no},
        timeout=REQUEST_TIMEOUT_API,
        proxies={"http": None, "https": None},
    )
    resp.raise_for_status()
    return resp.json()


def run(task_config=None):
    msgs = []
    orderid_file = os.path.join(DATA_DIR, "payment_orderid.json")
    target_mail = resolve_target_mail()

    try:
        quote_no = get_latest_submitted_quote(target_mail)
        if not quote_no:
            raise RuntimeError("未找到本轮提交的报价单，请先执行提交自助报价单")
        if not quote_no.startswith("B2B-BJ"):
            raise RuntimeError(f"报价单号格式异常: {quote_no}")

        msgs.append(f"报价单号获取:OK({quote_no})")
        token = _admin_login()
        msgs.append("后台登录:OK")

        body = _audit_quote(token, quote_no)
        resp_code = body.get("code")
        resp_msg = body.get("message", "")

        if resp_code == 200:
            mark_quote_audited(orderid_file, target_mail, quote_no)
            msgs.append(f"报价单审核:OK({quote_no})")
        else:
            msgs.append(f"报价单审核:FAIL(code={resp_code} msg={resp_msg})")

    except Exception as e:
        msgs.append(f"执行异常:{type(e).__name__}: {str(e)}")

    all_ok = all(":OK" in msg for msg in msgs) and len(msgs) >= 3
    message = " | ".join(msgs)
    result = {
        "success": all_ok,
        "message": message,
        "status_code": 200 if all_ok else 500,
        "actual": f"后台报价单审核: {message}",
    }
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            task_config = json.loads(sys.argv[1])
            run(task_config=task_config)
            sys.exit(0)
        except (json.JSONDecodeError, ValueError):
            pass
    run()
