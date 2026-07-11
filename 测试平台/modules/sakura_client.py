"""Sakura 后台 / 用户 API 客户端（测试工具共用）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import requests

BASE_URL = "https://www.sakuradk2.com"
CONFIG_PATH = Path(__file__).resolve().parent.parent / "sku_accounts.json"
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "GXe3u7AdzRDn#"


def create_direct_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    return session


def load_sku_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_sku_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=4)


def fetch_admin_captcha() -> dict:
    """获取后台登录验证码图片与 rand。"""
    session = create_direct_session()
    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json;charset=UTF-8",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
        ),
    }
    try:
        resp = session.post(
            f"{BASE_URL}/api/v1/captcha/get",
            headers=headers,
            data="{}",
            timeout=15,
        )
        resp.raise_for_status()
        body = resp.json()
    except requests.exceptions.ProxyError as exc:
        return {"success": False, "error": "PROXY_ERROR", "detail": str(exc)}
    except requests.exceptions.RequestException as exc:
        return {"success": False, "error": "NETWORK_ERROR", "detail": str(exc)}
    except ValueError:
        return {"success": False, "error": "INVALID_JSON", "detail": resp.text[:200]}

    data = body.get("data") or {}
    captcha = data.get("captcha")
    rand = data.get("rand")
    captcha_sessid = session.cookies.get("PHPSESSID", "")

    if body.get("status") not in (200, "200") or not captcha or not rand:
        return {
            "success": False,
            "error": "CAPTCHA_FETCH_FAILED",
            "detail": body.get("message") or body.get("msg") or str(body),
            "body": body,
        }

    return {
        "success": True,
        "captcha": captcha,
        "rand": rand,
        "captcha_sessid": captcha_sessid,
        "ip": data.get("ip", ""),
    }


def login_admin_with_captcha(
    username: str,
    password: str,
    captcha_code: str,
    rand: str,
    captcha_sessid: str = "",
    purl: str = "",
) -> dict:
    """通过账号密码 + 图片验证码登录后台，换取管理员 PHPSESSID。"""
    session = create_direct_session()
    if captcha_sessid:
        session.cookies.set("PHPSESSID", captcha_sessid, domain="sakuradk2.com")

    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json;charset=UTF-8",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
        ),
    }
    payload = {
        "txtusername": username,
        "txtpassword": password,
        "login_type": "new",
        "button": "登陆",
        "purl": purl,
        "captcha": captcha_code,
        "rand": rand,
    }

    try:
        resp = session.post(
            f"{BASE_URL}/manager/login",
            headers=headers,
            data=json.dumps(payload, ensure_ascii=False),
            timeout=20,
        )
        resp.raise_for_status()
        body = resp.json()
    except requests.exceptions.ProxyError as exc:
        return {"success": False, "error": "PROXY_ERROR", "detail": str(exc)}
    except requests.exceptions.RequestException as exc:
        return {"success": False, "error": "NETWORK_ERROR", "detail": str(exc)}
    except ValueError:
        return {"success": False, "error": "INVALID_JSON", "detail": resp.text[:200]}

    message = body.get("message") or body.get("msg") or ""
    code = body.get("code")
    new_sessid = session.cookies.get("PHPSESSID", captcha_sessid)

    # 后台登录成功时返回 code:200 并携带 token/admin_id，无 status 字段
    login_ok = code in (200, "200") and (body.get("token") or body.get("admin_id"))
    if login_ok and new_sessid:
        return {
            "success": True,
            "sessid": new_sessid,
            "detail": message or "登录成功",
            "body": body,
        }

    normalized = message.lower()
    if "验证码" in message or "captcha" in normalized:
        error = "INVALID_CAPTCHA"
    elif "密码" in message or "账号" in message or "login" in normalized:
        error = "INVALID_CREDENTIALS"
    else:
        error = "LOGIN_FAILED"

    return {
        "success": False,
        "error": error,
        "detail": message or str(body),
        "body": body,
    }


def get_user_token(admin_sessid: str, uid: str) -> dict:
    """模拟后台「进入会员中心」，获取客户 login_token。"""
    session = create_direct_session()
    session.cookies.set("PHPSESSID", admin_sessid, domain="sakuradk2.com")

    try:
        resp = session.get(
            f"{BASE_URL}/user/userShow",
            params={"uid": uid, "type": 1},
            timeout=15,
            allow_redirects=False,
        )
    except requests.exceptions.ProxyError as exc:
        return {"success": False, "error": "PROXY_ERROR", "detail": str(exc)}
    except requests.exceptions.RequestException as exc:
        return {"success": False, "error": "NETWORK_ERROR", "detail": str(exc)}

    location = resp.headers.get("Location", "")
    if "/manager/login" in location:
        return {"success": False, "error": "ADMIN_SESSION_EXPIRED"}

    login_token = session.cookies.get("login_token", "")
    new_sessid = session.cookies.get("PHPSESSID", admin_sessid)
    user_id = session.cookies.get("login_user_id", uid)

    if not login_token:
        return {"success": False, "error": "NO_TOKEN_RETURNED"}

    return {
        "success": True,
        "token": login_token,
        "sessid": new_sessid,
        "user_id": user_id,
    }


def build_auth_context(token_info: dict) -> tuple[dict, dict]:
    headers = {
        "accept": "application/json, text/plain, */*",
        "authorization": token_info["token"],
        "content-type": "application/x-www-form-urlencoded",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
        ),
    }
    cookies = {
        "PHPSESSID": token_info["sessid"],
        "login_token": token_info["token"],
        "server_login_token": token_info["token"],
        "login_user_id": token_info.get("user_id", ""),
    }
    return headers, cookies


def save_external_id(
    order_id: str,
    external_id: str,
    token_info: dict,
    *,
    item_type: int = 1,
) -> dict:
    """
    更新 orderdetail.order_ExternalID。
    item_type=1 订单，2 见积书。
    """
    headers, cookies = build_auth_context(token_info)
    url = f"{BASE_URL}/User/Agentorder/saveExternalID"
    data = {
        "type": item_type,
        "itemId": order_id,
        "usku": external_id,
    }

    session = create_direct_session()
    try:
        resp = session.post(url, headers=headers, cookies=cookies, data=data, timeout=20)
        resp.raise_for_status()
        body = resp.json()
    except requests.exceptions.RequestException as exc:
        return {"success": False, "error": "NETWORK_ERROR", "detail": str(exc)}
    except ValueError:
        return {"success": False, "error": "INVALID_JSON", "detail": resp.text[:200]}

    status = body.get("status")
    if status in (1, "1", "y", "Y", 200):
        return {"success": True, "body": body}

    msg = body.get("msg") or body.get("message") or body.get("cn_msg") or str(body)
    return {"success": False, "error": "API_ERROR", "detail": msg, "body": body}


def fetch_order_items(order_id: str, token_info: dict) -> dict:
    """拉取主订单下商品列表（含 order_ExternalID）。"""
    headers = {
        "accept": "application/json, text/plain, */*",
        "authorization": token_info["token"],
        "content-type": "application/json",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
        ),
    }
    cookies = {
        "PHPSESSID": token_info["sessid"],
        "login_token": token_info["token"],
        "server_login_token": token_info["token"],
        "login_user_id": token_info.get("user_id", ""),
    }
    url = f"{BASE_URL}/api_user/agent/orderDetail"
    session = create_direct_session()
    try:
        resp = session.post(
            url,
            headers=headers,
            cookies=cookies,
            json={"orderId": order_id},
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
    except requests.exceptions.RequestException as exc:
        return {"success": False, "error": str(exc)}
    except ValueError:
        return {"success": False, "error": "INVALID_JSON", "detail": resp.text[:200]}

    status = body.get("status")
    if status not in (200, "200"):
        msg = body.get("message") or body.get("msg") or "订单数据拉取失败"
        return {"success": False, "error": msg, "body": body}

    return {"success": True, "data": body}
