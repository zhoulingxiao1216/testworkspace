#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""安全优化 main 环境 R1 Smoke 执行脚本（Agent2）"""
import json
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests

API_BASE = "https://main-api.hubbuyer.com"
ADMIN_ORIGIN = "https://main-admin.hubbuyer.com"
B2B_ORIGIN = "https://main-b2b.hubbuyer.com"
TIMEOUT = 30
PROXIES = {"http": None, "https": None}

ACCOUNTS = {
    "user_a": {
        "email": "mxnrq@airsworld.net",
        "password": "123456",
        "jump_url": f"{B2B_ORIGIN}/jump_common",
        "jump_site": "B2B",
    },
    "user_b": {
        "email": "zhoulingxiao1216@proton.me",
        "password": "123456",
        "jump_url": f"{B2B_ORIGIN}/jump_common",
        "jump_site": "B2B",
    },
    "admin": {"account": "admin", "password": "123333"},
    "admin_patrol": {"account": "test-zhou", "password": "123456qwe"},
}

RESULTS = []


def record(case_id, status, summary, detail=None):
    RESULTS.append(
        {
            "case_id": case_id,
            "status": status,
            "summary": summary,
            "detail": detail or {},
            "at": datetime.now(timezone.utc).isoformat(),
        }
    )


def user_headers(token=None):
    h = {
        "Content-Type": "application/json",
        "Platform": "PC",
        "Origin": API_BASE,
        "User-Agent": "SecuritySmoke/1.0",
    }
    if token:
        h["authorization"] = token.replace("Bearer ", "").strip()
    return h


def admin_headers(token=None):
    origin = ADMIN_ORIGIN.rstrip("/")
    h = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "logintype": "admin",
        "origin": origin,
        "referer": origin + "/",
    }
    if token:
        h["authorization"] = token.replace("Bearer ", "").strip()
    return h


def login_user(key):
    acc = ACCOUNTS[key]
    payload = {
        "email": acc["email"],
        "password": acc["password"],
        "code": "",
        "type": "password",
        "jump_url": acc["jump_url"],
        "jump_site": acc["jump_site"],
    }
    r = requests.post(
        f"{API_BASE}/api/login/login",
        headers=user_headers(),
        json=payload,
        timeout=TIMEOUT,
        proxies=PROXIES,
    )
    token = r.cookies.get("pro_auth_token")
    body = {}
    try:
        body = r.json()
    except Exception:
        pass
    if not token:
        token = (body.get("data") or {}).get("token")
    if not token and "pro_auth_token=" in r.headers.get("Set-Cookie", ""):
        sc = r.headers.get("Set-Cookie", "")
        start = sc.find("pro_auth_token=") + len("pro_auth_token=")
        end = sc.find(";", start)
        token = sc[start:end if end != -1 else None].strip()
    code = body.get("code")
    ok = r.status_code == 200 and code == 200 and bool(token)
    return ok, token, {"http": r.status_code, "code": code, "message": body.get("message")}


def login_admin(key="admin"):
    acc = ACCOUNTS[key]
    r = requests.post(
        f"{API_BASE}/admin/login/login",
        headers=admin_headers(),
        json={"account": acc["account"], "password": acc["password"]},
        timeout=TIMEOUT,
        proxies=PROXIES,
    )
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    token = (body.get("data") or {}).get("login_token")
    ok = r.status_code == 200 and body.get("code") == 200 and bool(token)
    return ok, token, {"http": r.status_code, "code": body.get("code"), "message": body.get("message")}


def tc_secret_001():
    paths = [
        "/storage/certificates/worldtrade/sandbox/private_key.pem",
        "/storage/certificates/worldtrade/sandbox/public_key.pem",
    ]
    detail = []
    leaked = False
    for p in paths:
        url = API_BASE + p
        r = requests.get(url, timeout=TIMEOUT, proxies=PROXIES, allow_redirects=False)
        body_preview = (r.text or "")[:80]
        is_pem = "BEGIN" in r.text and "KEY" in r.text
        detail.append({"path": p, "http": r.status_code, "pem_leak": is_pem, "preview": body_preview})
        if is_pem and r.status_code == 200:
            leaked = True
    if leaked:
        record("TC-SEC-SECRET-001", "Fail", "私钥或密钥仍可通过 public 路径下载", detail)
    elif all(d["http"] in (403, 404, 401) for d in detail):
        record("TC-SEC-SECRET-001", "Pass", "敏感 .pem 路径不可公开访问", detail)
    else:
        record("TC-SEC-SECRET-001", "Conditional", "路径响应非常规，需人工复核", detail)


def probe_admin_index_write(case_id, token_label, token, expect_deny):
    candidates = [
        ("POST", "/admin_index/blogArticle/updateDeepLConfig", {"auth_key": "probe"}),
        ("POST", "/admin_index/bannerConfig/update", {"id": 1, "title": "sec_probe"}),
        ("POST", "/admin_index/navigationConfig/update", {"id": 1}),
    ]
    detail = []
    denied = True
    for method, path, payload in candidates:
        url = API_BASE + path
        headers = admin_headers(token) if token else admin_headers()
        if not token:
            headers.pop("authorization", None)
        r = requests.request(
            method, url, headers=headers, json=payload, timeout=TIMEOUT, proxies=PROXIES
        )
        try:
            body = r.json()
        except Exception:
            body = {"raw": (r.text or "")[:200]}
        code = body.get("code") if isinstance(body, dict) else None
        detail.append(
            {
                "path": path,
                "http": r.status_code,
                "biz_code": code,
                "message": body.get("message") if isinstance(body, dict) else None,
            }
        )
        if expect_deny:
            if r.status_code in (200, 201) and code == 200:
                denied = False
        else:
            if r.status_code in (401, 403) or code in (401, 403):
                denied = False
    if expect_deny:
        status = "Pass" if denied else "Fail"
        summary = "匿名/无鉴权 admin_index 写接口被拒绝" if denied else "匿名仍可写 admin_index"
    else:
        status = "Pass" if denied else "Fail"
        summary = "合法管理员可访问 admin_index" if denied else "合法管理员仍被拒绝"
    record(case_id, status, summary, {"token": token_label, "probes": detail})


def tc_auth_001():
    probe_admin_index_write("TC-SEC-AUTH-001", "none", None, expect_deny=True)


def tc_auth_002(admin_token):
    if not admin_token:
        record("TC-SEC-AUTH-002", "Blocked", "admin 登录失败，跳过正向回归")
        return
    probe_admin_index_write("TC-SEC-AUTH-002", "admin", admin_token, expect_deny=False)


def tc_auth_003():
    paths = [
        "/api_tb/auth/refreshToken",
        "/api_tb/Auth/refreshToken",
    ]
    detail = []
    accepted = False
    for path in paths:
        url = API_BASE + path
        headers = user_headers()
        headers["site"] = "B2B"
        r = requests.post(url, headers=headers, json={}, timeout=TIMEOUT, proxies=PROXIES)
        try:
            body = r.json()
        except Exception:
            body = {"raw": (r.text or "")[:200]}
        code = body.get("code") if isinstance(body, dict) else None
        detail.append({"path": path, "http": r.status_code, "biz_code": code, "message": body.get("message") if isinstance(body, dict) else None})
        if r.status_code == 200 and code == 200:
            accepted = True
    if accepted:
        record("TC-SEC-AUTH-003", "Fail", "refreshToken 无鉴权仍可成功", detail)
    elif detail:
        record("TC-SEC-AUTH-003", "Pass", "refreshToken 无鉴权调用被拒绝", detail)
    else:
        record("TC-SEC-AUTH-003", "Blocked", "未找到 refreshToken 路由")


def fetch_addresses(token):
    paths = [
        "/api_b2b/userDeliveryAddress/list",
        "/api_b2b/userDeliveryAddress/getList",
    ]
    for path in paths:
        r = requests.post(
            API_BASE + path,
            headers=user_headers(token),
            json={},
            timeout=TIMEOUT,
            proxies=PROXIES,
        )
        if r.status_code != 200:
            continue
        try:
            body = r.json()
        except Exception:
            continue
        if body.get("code") != 200:
            continue
        data = body.get("data")
        items = data if isinstance(data, list) else (data or {}).get("list") or (data or {}).get("data") or []
        ids = []
        for item in items:
            if isinstance(item, dict) and item.get("id"):
                ids.append(item["id"])
        if ids:
            return path, ids, body
    return None, [], {}


def tc_idor_001(token_a, token_b, b_address_ids):
    if not token_a or not token_b:
        record("TC-SEC-IDOR-001", "Blocked", "用户登录失败")
        return
    if not b_address_ids:
        record("TC-SEC-IDOR-001", "Blocked", "用户 B 无收货地址，无法构造跨用户 address_id")
        return
    target_id = b_address_ids[0]
    update_paths = [
        "/api_b2b/userDeliveryAddress/update",
        "/api_b2b/userDeliveryAddress/updateData",
    ]
    detail = []
    cross_ok = False
    for path in update_paths:
        r = requests.post(
            API_BASE + path,
            headers=user_headers(token_a),
            json={"id": target_id, "consignee": "sec_idor_probe", "address": "probe"},
            timeout=TIMEOUT,
            proxies=PROXIES,
        )
        try:
            body = r.json()
        except Exception:
            body = {"raw": (r.text or "")[:200]}
        code = body.get("code") if isinstance(body, dict) else None
        detail.append({"path": path, "target_id": target_id, "http": r.status_code, "biz_code": code})
        if r.status_code == 200 and code == 200:
            cross_ok = True
    verify = requests.post(
        API_BASE + (detail[0]["path"].replace("updateData", "list") if detail else "/api_b2b/userDeliveryAddress/list"),
        headers=user_headers(token_b),
        json={},
        timeout=TIMEOUT,
        proxies=PROXIES,
    )
    if cross_ok:
        record("TC-SEC-IDOR-001", "Fail", "用户 A 可修改用户 B 收货地址", detail)
    else:
        record("TC-SEC-IDOR-001", "Pass", "跨用户修改收货地址被拒绝", detail)


def main():
    print("=== 安全优化 main R1 Smoke 开始 ===", flush=True)
    tc_secret_001()
    tc_auth_001()
    tc_auth_003()

    ok_a, tok_a, det_a = login_user("user_a")
    ok_b, tok_b, det_b = login_user("user_b")
    ok_admin, tok_admin, det_admin = login_admin("admin")

    record(
        "LOGIN",
        "Pass" if ok_a else "Fail",
        f"user_a 登录 {'OK' if ok_a else 'FAIL'}",
        {"masked": True, **det_a},
    )
    record(
        "LOGIN",
        "Pass" if ok_b else "Fail",
        f"user_b 登录 {'OK' if ok_b else 'FAIL'}",
        {"masked": True, **det_b},
    )
    record(
        "LOGIN",
        "Pass" if ok_admin else "Fail",
        f"admin 登录 {'OK' if ok_admin else 'FAIL'}",
        {"masked": True, **det_admin},
    )

    tc_auth_002(tok_admin)

    list_path, ids_b, _ = fetch_addresses(tok_b)
    if list_path:
        record("RESOURCE", "Pass", f"user_b 地址 list 路径 {list_path}, ids={ids_b[:3]}", {"count": len(ids_b)})
    tc_idor_001(tok_a, tok_b, ids_b)

    out = {
        "environment": "main",
        "api_base": API_BASE,
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "results": RESULTS,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return out


if __name__ == "__main__":
    main()
