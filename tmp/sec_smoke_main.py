#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import copy
import json
import sys
from datetime import datetime, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_BASE = "https://main-api.hubbuyer.com"
ADMIN_ORIGIN = "https://main-admin.hubbuyer.com"
B2B_ORIGIN = "https://main-b2b.hubbuyer.com"
TIMEOUT = 45

ACCOUNTS = {
    "user_a": {"email": "mxnrq@airsworld.net", "password": "123456"},
    "user_b": {"email": "zhoulingxiao1216@proton.me", "password": "123456"},
    "admin": {"account": "admin", "password": "123333"},
}

RESULTS = []


def session():
    s = requests.Session()
    s.proxies = {"http": None, "https": None}
    retry = Retry(total=3, backoff_factor=0.6, status_forcelist=[502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


S = session()


def record(case_id, status, summary, detail=None):
    RESULTS.append({"case_id": case_id, "status": status, "summary": summary, "detail": detail or {}})


def safe_json(r):
    try:
        return r.json()
    except Exception:
        return {"raw": (r.text or "")[:300]}


def login_user(email, password):
    payload = {
        "email": email,
        "password": password,
        "code": "",
        "type": "password",
        "jump_url": f"{B2B_ORIGIN}/jump_common",
        "jump_site": "B2B",
    }
    r = S.post(f"{API_BASE}/api/login/login", json=payload, timeout=TIMEOUT, headers={"Content-Type": "application/json", "Platform": "PC", "Origin": API_BASE})
    body = safe_json(r)
    token = r.cookies.get("pro_auth_token") or (body.get("data") or {}).get("token")
    return bool(token), token, r.status_code, body.get("code"), body.get("message")


def login_admin(account, password):
    r = S.post(
        f"{API_BASE}/admin/login/login",
        json={"account": account, "password": password},
        timeout=TIMEOUT,
        headers={"content-type": "application/json", "logintype": "admin", "origin": ADMIN_ORIGIN, "referer": ADMIN_ORIGIN + "/"},
    )
    body = safe_json(r)
    token = (body.get("data") or {}).get("login_token")
    return bool(token), token, r.status_code, body.get("code"), body.get("message")


def user_headers(token):
    return {"Content-Type": "application/json", "Platform": "PC", "Origin": API_BASE, "authorization": token.replace("Bearer ", "").strip()}


def admin_headers(token=None):
    h = {"content-type": "application/json", "logintype": "admin", "origin": ADMIN_ORIGIN, "referer": ADMIN_ORIGIN + "/"}
    if token:
        h["authorization"] = token.replace("Bearer ", "").strip()
    return h


def run():
    # SECRET-001
    pem_paths = ["/storage/certificates/worldtrade/sandbox/private_key.pem", "/storage/certificates/worldtrade/sandbox/public_key.pem"]
    pem_detail = []
    leak = False
    for p in pem_paths:
        r = S.get(API_BASE + p, timeout=TIMEOUT)
        text = r.text or ""
        is_pem = "BEGIN" in text and "PRIVATE KEY" in text
        pem_detail.append({"path": p, "http": r.status_code, "pem_leak": is_pem, "preview": text[:100]})
        leak = leak or is_pem
    record("TC-SEC-SECRET-001", "Fail" if leak else "Pass", "私钥未泄露" if not leak else "私钥可下载", pem_detail)

    # AUTH-001 anonymous admin_index
    probes = [
        ("/admin_index/blogArticle/updateDeepLConfig", {"auth_key": "sec_probe"}),
        ("/admin_index/bannerConfig/update", {"id": 1, "title": "sec_probe"}),
    ]
    anon_detail = []
    anon_ok = True
    for path, payload in probes:
        try:
            r = S.post(API_BASE + path, headers=admin_headers(), json=payload, timeout=TIMEOUT)
            body = safe_json(r)
            anon_detail.append({"path": path, "http": r.status_code, "biz_code": body.get("code"), "msg": body.get("message") or body.get("msg")})
            if r.status_code == 200 and body.get("code") == 200:
                anon_ok = False
        except Exception as e:
            anon_detail.append({"path": path, "error": type(e).__name__})
    record("TC-SEC-AUTH-001", "Pass" if anon_ok else "Fail", "匿名 admin_index 写接口拒绝" if anon_ok else "匿名仍可写", anon_detail)

    # AUTH-003 refreshToken
    rt_detail = []
    rt_ok = True
    for path in ["/api_tb/auth/refreshToken", "/api_tb/Auth/refreshToken"]:
        try:
            r = S.post(API_BASE + path, headers={"Content-Type": "application/json", "site": "B2B", "Origin": API_BASE}, json={}, timeout=TIMEOUT)
            body = safe_json(r)
            rt_detail.append({"path": path, "http": r.status_code, "biz_code": body.get("code"), "msg": body.get("message") or body.get("msg")})
            if r.status_code == 200 and body.get("code") == 200:
                rt_ok = False
        except Exception as e:
            rt_detail.append({"path": path, "error": type(e).__name__})
    record("TC-SEC-AUTH-003", "Pass" if rt_ok else "Fail", "refreshToken 无鉴权拒绝" if rt_ok else "refreshToken 无鉴权成功", rt_detail)

    ok_a, tok_a, *_ = login_user(ACCOUNTS["user_a"]["email"], ACCOUNTS["user_a"]["password"])
    ok_b, tok_b, *_ = login_user(ACCOUNTS["user_b"]["email"], ACCOUNTS["user_b"]["password"])
    ok_ad, tok_ad, *_ = login_admin(ACCOUNTS["admin"]["account"], ACCOUNTS["admin"]["password"])
    record("LOGIN-user_a", "Pass" if ok_a else "Fail", "user_a 登录", {"ok": ok_a})
    record("LOGIN-user_b", "Pass" if ok_b else "Fail", "user_b 登录", {"ok": ok_b})
    record("LOGIN-admin", "Pass" if ok_ad else "Fail", "admin 登录", {"ok": ok_ad})

    # AUTH-002 with admin token - one probe only
    if ok_ad:
        try:
            r = S.post(API_BASE + "/admin_index/blogArticle/deeplConfig", headers=admin_headers(tok_ad), json={}, timeout=TIMEOUT)
            body = safe_json(r)
            denied = r.status_code in (401, 403) or body.get("code") in (401, 403)
            record("TC-SEC-AUTH-002", "Fail" if denied else "Pass", "合法管理员可读 deeplConfig" if not denied else "合法管理员仍被拒", {"http": r.status_code, "biz_code": body.get("code")})
        except Exception as e:
            record("TC-SEC-AUTH-002", "Blocked", str(e))
    else:
        record("TC-SEC-AUTH-002", "Blocked", "admin 登录失败")

    # IDOR-001
    b_ids = []
    if ok_b:
        for path in ["/api_b2b/userDeliveryAddress/list", "/api_b2b/userDeliveryAddress/getList"]:
            try:
                r = S.post(API_BASE + path, headers=user_headers(tok_b), json={}, timeout=TIMEOUT)
                body = safe_json(r)
                if body.get("code") == 200:
                    data = body.get("data")
                    items = data if isinstance(data, list) else (data or {}).get("list") or []
                    b_ids = [x.get("id") for x in items if isinstance(x, dict) and x.get("id")]
                    if b_ids:
                        break
            except Exception:
                pass
    if ok_a and ok_b and b_ids:
        target = b_ids[0]
        cross = False
        idor_detail = []
        for path in ["/api_b2b/userDeliveryAddress/update", "/api_b2b/userDeliveryAddress/updateData"]:
            try:
                r = S.post(API_BASE + path, headers=user_headers(tok_a), json={"id": target, "consignee": "sec_probe"}, timeout=TIMEOUT)
                body = safe_json(r)
                idor_detail.append({"path": path, "id": target, "http": r.status_code, "biz_code": body.get("code")})
                if r.status_code == 200 and body.get("code") == 200:
                    cross = True
            except Exception as e:
                idor_detail.append({"path": path, "error": type(e).__name__})
        record("TC-SEC-IDOR-001", "Fail" if cross else "Pass", "跨用户改地址" + ("成功" if cross else "被拒绝"), idor_detail)
    else:
        record("TC-SEC-IDOR-001", "Blocked", "缺登录或 user_b 无 address_id", {"ok_a": ok_a, "ok_b": ok_b, "b_ids": b_ids})

    out = {"environment": "main", "executed_at": datetime.now(timezone.utc).isoformat(), "results": RESULTS}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return out


if __name__ == "__main__":
    run()
