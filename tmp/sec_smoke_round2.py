#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""安全优化 main 环境 R1 第二轮 API 执行"""
import json
import uuid
from datetime import datetime, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API = "https://main-api.hubbuyer.com"
ADMIN_ORIGIN = "https://main-admin.hubbuyer.com"
B2B = "https://main-b2b.hubbuyer.com"
TIMEOUT = 45

USER_A = {"email": "mxnrq@airsworld.net", "password": "123456"}
USER_B = {"email": "zhoulingxiao1216@proton.me", "password": "123456"}
ADMIN = {"account": "admin", "password": "123333"}

RESULTS = []


def S():
    s = requests.Session()
    s.proxies = {"http": None, "https": None}
    s.mount("https://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=0.5)))
    return s


SESSION = S()


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


def j(r):
    try:
        return r.json()
    except Exception:
        return {"raw": (r.text or "")[:400]}


def login_user(acc):
    r = SESSION.post(
        f"{API}/api/login/login",
        json={
            "email": acc["email"],
            "password": acc["password"],
            "code": "",
            "type": "password",
            "jump_url": f"{B2B}/jump_common",
            "jump_site": "B2B",
        },
        headers={"Content-Type": "application/json", "Platform": "PC", "Origin": API},
        timeout=TIMEOUT,
    )
    b = j(r)
    t = r.cookies.get("pro_auth_token") or (b.get("data") or {}).get("token")
    return t, b


def login_admin():
    r = SESSION.post(
        f"{API}/admin/login/login",
        json={"account": ADMIN["account"], "password": ADMIN["password"]},
        headers={
            "content-type": "application/json",
            "logintype": "admin",
            "origin": ADMIN_ORIGIN,
            "referer": ADMIN_ORIGIN + "/",
        },
        timeout=TIMEOUT,
    )
    b = j(r)
    return (b.get("data") or {}).get("login_token"), b


def uh(token):
    return {
        "Content-Type": "application/json",
        "Platform": "PC",
        "Origin": API,
        "authorization": (token or "").replace("Bearer ", "").strip(),
    }


def ah(token=None):
    h = {
        "content-type": "application/json",
        "logintype": "admin",
        "origin": ADMIN_ORIGIN,
        "referer": ADMIN_ORIGIN + "/",
    }
    if token:
        h["authorization"] = token.replace("Bearer ", "").strip()
    return h


def list_nested_items(body):
    data = body.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("data", "list", "items"):
            v = data.get(k)
            if isinstance(v, list):
                return v
    return []


def fetch_list(token, paths):
    for p in paths:
        for method in ("POST", "GET"):
            try:
                r = SESSION.request(method, API + p, headers=uh(token), json={}, timeout=TIMEOUT)
                b = j(r)
                items = list_nested_items(b)
                if b.get("code") == 200 and items:
                    return p, items, b
            except Exception:
                pass
    return None, [], {}


def denied(code, msg):
    msg = str(msg or "")
    if code in (401, 403):
        return True
    if any(x in msg for x in ("权限", "403", "无权", "不属于", "permission", "denied")):
        return True
    return False


def tc_secret_001_ext():
    paths = [
        "/storage/certificates/worldtrade/sandbox/private_key.pem",
        "/.env",
        "/.env.example",
        "/storage/.env",
        "/config/database.key",
    ]
    detail = []
    leak = False
    for p in paths:
        r = SESSION.get(API + p, timeout=TIMEOUT)
        text = r.text or ""
        is_secret = ("BEGIN PRIVATE KEY" in text) or (text.startswith("APP_") and "=" in text[:80])
        detail.append({"path": p, "http": r.status_code, "leak": is_secret, "preview": text[:80]})
        leak = leak or is_secret
    record(
        "TC-SEC-SECRET-001",
        "Fail" if leak else "Pass",
        "扩展敏感路径未泄露" if not leak else "发现敏感内容泄露",
        detail,
    )


def tc_auth_001_forged():
    paths = [
        "/admin_index/blogArticle/updateDeepLConfig",
        "/admin_index/bannerConfig/update",
    ]
    detail = []
    ok = True
    for p in paths:
        r = SESSION.post(
            API + p,
            headers=ah("Bearer forged-invalid-token-sec-test"),
            json={"id": 1, "title": "probe"},
            timeout=TIMEOUT,
        )
        b = j(r)
        detail.append({"path": p, "biz_code": b.get("code"), "msg": b.get("message") or b.get("msg")})
        if b.get("code") == 200:
            ok = False
    record(
        "TC-SEC-AUTH-001",
        "Pass" if ok else "Fail",
        "伪造 admin token 写 admin_index 被拒绝" if ok else "伪造 token 仍可写",
        {"variant": "forged_token", "probes": detail},
    )


def tc_auth_003_004(admin_token):
    detail = {}
    if not admin_token:
        record("TC-SEC-AUTH-003", "Blocked", "admin 未登录")
        record("TC-SEC-AUTH-004", "Blocked", "admin 未登录")
        return
    paths = ["/api_tb/auth/refreshToken", "/api_tb/Auth/refreshToken"]
    leaked = False
    accepted = False
    probes = []
    for p in paths:
        r = SESSION.post(
            API + p,
            headers={**ah(admin_token), "site": "B2B"},
            json={"site": "B2B"},
            timeout=TIMEOUT,
        )
        b = j(r)
        text = json.dumps(b, ensure_ascii=False)
        probes.append({"path": p, "biz_code": b.get("code"), "msg": b.get("message") or b.get("msg")})
        if b.get("code") == 200:
            accepted = True
        if any(k in text.lower() for k in ("access_token", "refresh_token", "client_secret", "token")):
            data = b.get("data")
            if isinstance(data, dict) and any(isinstance(v, str) and len(v) > 20 for v in data.values()):
                leaked = True
    record(
        "TC-SEC-AUTH-003",
        "Fail" if accepted else "Pass",
        "admin 路径 refreshToken 未无鉴权成功" if not accepted else "refreshToken 无鉴权仍成功",
        probes,
    )
    record(
        "TC-SEC-AUTH-004",
        "Fail" if leaked else "Pass",
        "refreshToken 响应未泄漏长 token/secret" if not leaked else "响应可能含敏感明文",
        probes,
    )


def tc_auth_008():
    registered = USER_A["email"]
    unregistered = f"sec-not-exist-{uuid.uuid4().hex[:8]}@proton.me"
    paths = [
        "/api/register/checkEmail",
        "/api/emailCode/send",
        "/api/register/register",
    ]
    detail = []
    enum_risk = False
    for p in paths:
        for email in (registered, unregistered):
            try:
                r = SESSION.post(API + p, json={"email": email}, headers=uh(None), timeout=TIMEOUT)
                b = j(r)
                detail.append(
                    {
                        "path": p,
                        "email_type": "registered" if email == registered else "unregistered",
                        "biz_code": b.get("code"),
                        "msg": b.get("message") or b.get("msg"),
                    }
                )
            except Exception as e:
                detail.append({"path": p, "error": type(e).__name__})
    msgs_reg = [d.get("msg") for d in detail if d.get("email_type") == "registered" and d.get("msg")]
    msgs_unreg = [d.get("msg") for d in detail if d.get("email_type") == "unregistered" and d.get("msg")]
    if msgs_reg and msgs_unreg and len(set(msgs_reg) & set(msgs_unreg)) == 0:
        if any("exist" in str(m).lower() or "已注册" in str(m) or "注册" in str(m) for m in msgs_reg):
            enum_risk = True
    record(
        "TC-SEC-AUTH-008",
        "Fail" if enum_risk else "Pass",
        "注册/发码接口可区分邮箱是否存在" if enum_risk else "未发现明显邮箱枚举差异（或接口不可用）",
        detail,
    )


def tc_secret_003(tok_a, admin_token):
    checks = []
    leaked = False
    for label, token in (("user_login", tok_a), ("admin_login", admin_token)):
        if not token:
            continue
        if len(token) > 30:
            checks.append({label: "token_obtained", "len": len(token)})
    r = SESSION.post(f"{API}/api/login/login", json={"email": USER_A["email"], "password": "wrong-pass"}, timeout=TIMEOUT)
    b = j(r)
    body_text = json.dumps(b, ensure_ascii=False)
    if USER_A["email"] in body_text and "password" in body_text.lower():
        leaked = True
    checks.append({"wrong_password_response": b.get("message") or b.get("msg")})
    record(
        "TC-SEC-SECRET-003",
        "Fail" if leaked else "Pass",
        "错误登录响应未泄漏敏感明文" if not leaked else "错误响应可能泄漏敏感信息",
        checks,
    )


def tc_idor_address(case_id, tok_a, tok_b, b_items, ops):
    if not tok_a or not tok_b or not b_items:
        record(case_id, "Blocked", "缺 token 或 B 侧地址")
        return
    target = b_items[0]
    tid = target.get("id")
    before_name = target.get("name")
    detail = {"target_id": tid, "ops": []}
    side_effect = False
    for op_name, path, payload_extra in ops:
        payload = {"id": tid, **payload_extra}
        r = SESSION.post(API + path, headers=uh(tok_a), json=payload, timeout=TIMEOUT)
        b = j(r)
        detail["ops"].append(
            {
                "op": op_name,
                "path": path,
                "biz_code": b.get("code"),
                "msg": b.get("message") or b.get("msg"),
                "denied": denied(b.get("code"), b.get("message") or b.get("msg")),
            }
        )
        if b.get("code") == 200:
            side_effect = True
    _, after_items, _ = fetch_list(tok_b, ["/api_b2b/userDeliveryAddress/list"])
    after = after_items[0] if after_items else {}
    unchanged = after.get("name") == before_name and str(after.get("id")) == str(tid)
    detail["verify"] = {"name_before": before_name, "name_after": after.get("name"), "unchanged": unchanged}
    if side_effect:
        status = "Fail"
        summary = "跨用户写操作成功"
    elif unchanged:
        status = "Pass" if any(o.get("denied") for o in detail["ops"]) else "Conditional"
        summary = "跨用户写被拒绝或无副作用"
    else:
        status = "Fail"
        summary = "检测到可能的副作用"
    record(case_id, status, summary, detail)


def tc_idor_importer(tok_a, tok_b):
    path, items, _ = fetch_list(
        tok_b,
        [
            "/api_b2b/userImporterAddress/list",
            "/api_b2b/userImporterAddress/getList",
        ],
    )
    if not items:
        record("TC-SEC-IDOR-003", "Blocked", "user_b 无进口商地址或 list 接口不可用", {"path": path})
        return
    tid = items[0].get("id")
    ops = [
        ("update", "/api_b2b/userImporterAddress/update", {"name": "SEC_PROBE"}),
        ("delete", "/api_b2b/userImporterAddress/delete", {}),
        ("default", "/api_b2b/userImporterAddress/updateDefault", {}),
    ]
    detail = {"list_path": path, "target_id": tid, "ops": []}
    ok_write = False
    for op, p, extra in ops:
        r = SESSION.post(API + p, headers=uh(tok_a), json={"id": tid, **extra}, timeout=TIMEOUT)
        b = j(r)
        detail["ops"].append({"op": op, "biz_code": b.get("code"), "msg": b.get("message") or b.get("msg")})
        if b.get("code") == 200:
            ok_write = True
    record(
        "TC-SEC-IDOR-003",
        "Fail" if ok_write else "Pass",
        "跨用户进口商地址写操作被拒绝" if not ok_write else "跨用户写进口商地址成功",
        detail,
    )


def tc_idor_001_full(tok_a, tok_b, b_items):
    if not b_items:
        record("TC-SEC-IDOR-001", "Blocked", "无 B 地址")
        return
    addr = dict(b_items[0])
    old_name = addr.get("name")
    addr["name"] = "SEC_IDOR_FULL_PROBE"
    r = SESSION.post(API + "/api_b2b/userDeliveryAddress/update", headers=uh(tok_a), json=addr, timeout=TIMEOUT)
    b = j(r)
    _, after_items, _ = fetch_list(tok_b, ["/api_b2b/userDeliveryAddress/list"])
    after_name = after_items[0].get("name") if after_items else None
    record(
        "TC-SEC-IDOR-001",
        "Fail" if after_name == "SEC_IDOR_FULL_PROBE" else ("Pass" if denied(b.get("code"), b.get("msg")) else "Conditional"),
        "完整 payload 跨用户 update 未成功" if after_name != "SEC_IDOR_FULL_PROBE" else "跨用户 update 成功",
        {
            "biz_code": b.get("code"),
            "msg": b.get("message") or b.get("msg"),
            "name_before": old_name,
            "name_after": after_name,
        },
    )


def tc_fin_007_008(tok_a, tok_b):
    detail = []
    for label, tok in (("user_a", tok_a), ("user_b", tok_b)):
        if not tok:
            continue
        for amount in (0, -1, 1):
            for path in (
                "/api_b2b/userRechargeLog/withdrawalFunds",
                "/api_b2b/userWithdrawalLog/withdraw",
            ):
                try:
                    r = SESSION.post(
                        API + path,
                        headers=uh(tok),
                        json={"amount": amount, "withdraw_password": "123456"},
                        timeout=TIMEOUT,
                    )
                    b = j(r)
                    detail.append(
                        {
                            "user": label,
                            "path": path,
                            "amount": amount,
                            "biz_code": b.get("code"),
                            "msg": b.get("message") or b.get("msg"),
                        }
                    )
                except Exception as e:
                    detail.append({"user": label, "path": path, "error": type(e).__name__})
    risky = [d for d in detail if d.get("biz_code") == 200 and d.get("amount") in (0, -1)]
    record(
        "TC-SEC-FIN-008",
        "Fail" if risky else "Pass",
        "0/负数/探测提现未成功入账" if not risky else "异常金额提现可能成功",
        detail,
    )
    record(
        "TC-SEC-FIN-007",
        "Conditional",
        "提现密码探测已执行，需结合账号是否设密人工判定",
        detail,
    )


def tc_fin_001(tok_a, tok_b):
    detail = {"orders_b": [], "refund_probes": []}
    _, orders, _ = fetch_list(
        tok_b,
        [
            "/api_b2b/quote/list",
            "/pay/payment/list",
            "/api_b2b/order/list",
        ],
    )
    detail["orders_b"] = [
        {k: o.get(k) for k in ("order_no", "quote_no", "payment_intent_id", "id") if o.get(k)}
        for o in orders[:5]
    ]
    target = None
    for o in orders:
        for k in ("payment_intent_id", "order_no", "quote_no"):
            if o.get(k):
                target = o
                break
        if target:
            break
    if not target or not tok_a:
        record("TC-SEC-FIN-001", "Blocked", "未找到 B 的可退/订单号或 user_a 未登录", detail)
        return
    refund_paths = ["/pay/payment/refund", "/pay/paymentNotify/refund"]
    denied_all = True
    for p in refund_paths:
        payload = {
            "order_no": target.get("order_no") or target.get("quote_no"),
            "payment_intent_id": target.get("payment_intent_id", "probe"),
            "amount": 999999,
        }
        r = SESSION.post(API + p, headers=uh(tok_a), json=payload, timeout=TIMEOUT)
        b = j(r)
        detail["refund_probes"].append({"path": p, "biz_code": b.get("code"), "msg": b.get("message") or b.get("msg")})
        if b.get("code") == 200:
            denied_all = False
    record(
        "TC-SEC-FIN-001",
        "Pass" if denied_all else "Fail",
        "普通用户越权退款被拒绝" if denied_all else "普通用户退款可能成功",
        detail,
    )


def main():
    tok_a, _ = login_user(USER_A)
    tok_b, _ = login_user(USER_B)
    admin_tok, _ = login_admin()

    record("LOGIN", "Pass" if tok_a else "Fail", "user_a", {"ok": bool(tok_a)})
    record("LOGIN", "Pass" if tok_b else "Fail", "user_b", {"ok": bool(tok_b)})
    record("LOGIN", "Pass" if admin_tok else "Fail", "admin", {"ok": bool(admin_tok)})

    tc_secret_001_ext()
    tc_auth_001_forged()
    tc_auth_003_004(admin_tok)
    tc_auth_008()
    tc_secret_003(tok_a, admin_tok)

    _, b_addrs, _ = fetch_list(tok_b, ["/api_b2b/userDeliveryAddress/list"])
    tc_idor_001_full(tok_a, tok_b, b_addrs)
    tc_idor_address(
        "TC-SEC-IDOR-002",
        tok_a,
        tok_b,
        b_addrs,
        [
            ("delete", "/api_b2b/userDeliveryAddress/delete", {}),
            ("default", "/api_b2b/userDeliveryAddress/updateDefault", {}),
            ("delivery_note", "/api_b2b/userDeliveryAddress/updateIncludeDeliveryNote", {"include_delivery_note": 1}),
        ],
    )
    tc_idor_importer(tok_a, tok_b)
    tc_fin_007_008(tok_a, tok_b)
    tc_fin_001(tok_a, tok_b)

    out = {
        "environment": "main",
        "round": "R1-round2",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "results": RESULTS,
    }
    path = "d:/test_workspace/tmp/sec_smoke_round2_20260616.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(path)
    print(json.dumps({k: out[k] for k in ("environment", "round", "executed_at")}, ensure_ascii=False))
    for r in RESULTS:
        print(f"{r['case_id']}: {r['status']} - {r['summary']}")


if __name__ == "__main__":
    main()
