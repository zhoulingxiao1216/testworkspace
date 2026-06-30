# -*- coding: utf-8 -*-
# checker/api/purchase_order_audit.py
# 后台代购订单审核（B2B-DD 代购订单号，与报价单审核区分）
import json
import os
import sys
import requests
import traceback
from urllib.parse import urlparse

current_file = os.path.abspath(__file__)
root_path = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from config.settings import REQUEST_TIMEOUT_API, ENV_TYPE
from core.rules.assertion import AssertionTool
from core.path_manager import DATA_DIR, normalize_api_block
from checker.api.order_audit import _admin_login, admin_api_base_url, build_admin_auth_headers
from core.path_manager import normalize_purchase_order_audit_config
from checker.api.quote_order_store import (
    get_round_paid_order,
    resolve_target_mail,
    validate_round_order_matches_quote,
)

TARGET_CONFIG_FILE = "purchase_order_audit.json"


def _load_target_config():
    path = os.path.join(DATA_DIR, TARGET_CONFIG_FILE)
    if not os.path.exists(path):
        raise FileNotFoundError(f"未找到 {TARGET_CONFIG_FILE}")
    with open(path, "r", encoding="utf-8") as f:
        return normalize_purchase_order_audit_config(json.load(f))


def _resolve_order_no(target_cfg, orderid_file, target_mail):
    order_no = (target_cfg.get("order_no") or "").strip()
    if target_cfg.get("auto_resolve_order_no"):
        resolved = get_round_paid_order(orderid_file, target_mail)
        if not resolved:
            raise RuntimeError("未找到本轮已支付的代购订单号，请先完成前台报价单支付")
        validate_round_order_matches_quote(target_mail, resolved)
        return resolved
    if order_no:
        return order_no
    raise RuntimeError("未找到本轮已支付的代购订单号，请先完成前台报价单支付")


def _build_audit_headers(token, audit_cfg):
    admin_site = (audit_cfg.get("admin_site_origin") or "").strip() or None
    extra_headers = dict(audit_cfg.get("headers") or {})
    return build_admin_auth_headers(token, admin_site, extra_headers)


def _execute_audit_api(token, order_no, audit_cfg, all_rules):
    if not audit_cfg or not audit_cfg.get("enabled"):
        return {
            "success": True,
            "skipped": True,
            "message": "代购订单审核:跳过(待配置 curl)",
        }

    audit_cfg = normalize_api_block(dict(audit_cfg))
    url = (audit_cfg.get("url") or "").strip()
    if not url:
        return {
            "success": False,
            "message": "代购订单审核:FAIL(已启用但 url 为空)",
        }

    login_host = urlparse(admin_api_base_url()).netloc
    audit_host = urlparse(url).netloc
    if login_host and audit_host and login_host != audit_host:
        return {
            "success": False,
            "message": (
                f"代购订单审核:FAIL(登录域={login_host}|审核域={audit_host}|ENV={ENV_TYPE}；"
                "请确认 settings.ENV_TYPE 与 purchase_order_audit.json 的 url 同属 prod/main)"
            ),
        }

    method = (audit_cfg.get("method") or "POST").upper()
    headers = _build_audit_headers(token, audit_cfg)

    kwargs = {
        "headers": headers,
        "timeout": REQUEST_TIMEOUT_API,
        "verify": False,
        "proxies": {"http": None, "https": None},
    }
    if audit_cfg.get("json") is not None:
        payload = dict(audit_cfg["json"])
        payload["order_no"] = order_no
        kwargs["json"] = payload
    elif audit_cfg.get("body") is not None:
        kwargs["data"] = audit_cfg["body"]

    response = requests.request(method, url, **kwargs)
    check = AssertionTool.verify_api_common(response, rules=all_rules.get("audit_api", {}))
    if check["success"]:
        return {"success": True, "message": f"代购订单审核:OK({order_no})"}
    detail = check.get("message", "未知错误")
    try:
        body = response.json()
        if body.get("message"):
            detail = f"{detail} | api_msg={body.get('message')}"
        if body.get("code") == 30001:
            detail += (
                f" | 提示:登录域={login_host} 审核域={audit_host} ENV={ENV_TYPE}；"
                "prod 应均为 api.hubbuyer.com，且 url 建议用相对路径 /admin_b2b/..."
            )
    except Exception:
        pass
    return {"success": False, "message": f"代购订单审核:FAIL({detail})"}


def run(task_config=None):
    msgs = []
    try:
        target_cfg = _load_target_config()
        all_rules = AssertionTool.get_rules_dynamically("purchase_order_audit", root_path) or {}

        target_mail = resolve_target_mail()
        orderid_file = os.path.join(DATA_DIR, "payment_orderid.json")

        order_no = _resolve_order_no(target_cfg, orderid_file, target_mail)
        msgs.append(f"代购订单号获取:OK({order_no})")

        token = _admin_login()
        msgs.append("后台登录:OK")

        audit_result = _execute_audit_api(
            token, order_no, target_cfg.get("audit_api"), all_rules
        )
        if audit_result.get("skipped"):
            msgs.append(audit_result["message"])
        elif audit_result["success"]:
            msgs.append(audit_result["message"])
        else:
            msgs.append(audit_result["message"])

        all_ok = all(":OK" in msg or ":跳过" in msg for msg in msgs)
        message = " | ".join(msgs)
        result = {
            "success": all_ok,
            "message": message,
            "status_code": 200 if all_ok else 500,
            "actual": f"后台代购订单审核: {message}",
        }
    except Exception as e:
        message = f"执行异常:{type(e).__name__}: {str(e)}"
        result = {
            "success": False,
            "message": message,
            "status_code": 500,
            "actual": traceback.format_exc(),
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
