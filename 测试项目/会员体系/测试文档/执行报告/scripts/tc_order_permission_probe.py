# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import json
import os
import sys

sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

ACCOUNTS = [
    ("codex.jp.001@hubbuyer.test", "jp_member"),
    ("hanguo999@qq.com", "kr_normal"),
]


def admin_login(page):
    page.goto("https://lying-admin.hubbuyer.com/login", timeout=30000)
    page.wait_for_selector("input", timeout=10000)
    inputs = page.locator("input").all()
    inputs[0].fill("admin")
    inputs[1].fill("123333")
    page.locator("button").filter(has_text="登录").click()
    page.wait_for_timeout(3500)


def open_sso(page, email):
    opened = []
    page.context.on("page", lambda new_page: opened.append(new_page))
    page.goto("https://lying-admin.hubbuyer.com/admin/user/list", timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    expand_btn = page.locator("text=展开").first
    if expand_btn.count() > 0:
        expand_btn.click()
        page.wait_for_timeout(800)
    email_input = page.locator("input[placeholder*='邮箱']").first
    if email_input.count() > 0:
        email_input.fill(email)
    else:
        page.locator("input.el-input__inner:visible").first.fill(email)
    page.locator("button").filter(has_text="查询").first.click()
    page.wait_for_timeout(3500)
    page.locator("button").filter(has_text="会员中心").first.click()
    page.wait_for_timeout(1000)
    confirm_btn = page.locator(".el-popper button").filter(has_text="确定").first
    if confirm_btn.count() == 0:
        confirm_btn = page.locator("button").filter(has_text="确定").last
    try:
        with page.expect_popup(timeout=8000) as popup_info:
            confirm_btn.click()
        target = popup_info.value
        target.wait_for_load_state(timeout=15000)
        target.wait_for_timeout(5000)
        return target
    except PlaywrightTimeoutError:
        page.wait_for_timeout(6000)
        return opened[-1] if opened else page


def main():
    result = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for email, label in ACCOUNTS:
            ctx = browser.new_context(viewport={"width": 1440, "height": 900})
            page = ctx.new_page()
            capture = []
            request_headers = {}

            def on_response(resp):
                if "api_b2b/sysConfig/orderPermission" not in resp.url:
                    return
                try:
                    capture.append({"status": resp.status, "json": resp.json()})
                except Exception as exc:
                    capture.append({"status": resp.status, "error": repr(exc)})

            def on_request(req):
                if "api_b2b/user/userInfo" in req.url or "api_b2b/sysConfig/orderPermission" in req.url:
                    request_headers.update(dict(req.headers))

            try:
                admin_login(page)
                front = open_sso(page, email)
                front.on("request", on_request)
                front.on("response", on_response)
                front.goto("https://lying-b2b.hubbuyer.com/", timeout=30000, wait_until="domcontentloaded")
                front.wait_for_timeout(5000)
                direct_headers = {
                    k: v for k, v in request_headers.items()
                    if k.lower() not in ("content-length", "host", "origin", "referer", "cookie")
                }
                direct_headers.setdefault("content-type", "application/json")
                api = p.request.new_context(ignore_https_errors=True)
                resp = api.post(
                    "https://lying-api.hubbuyer.com/api_b2b/sysConfig/orderPermission",
                    headers=direct_headers,
                    data="{}",
                    timeout=30000,
                )
                try:
                    active_body = resp.json()
                except Exception:
                    active_body = {"raw": resp.text()[:500]}
                active_call = {"status": resp.status, "body": active_body}
                api.dispose()
                result[label] = {
                    "email": email,
                    "order_permission_responses": capture,
                    "active_call": active_call,
                    "captured_header_keys": sorted([k for k in direct_headers.keys() if k.lower() not in ("authorization", "userlogintoken")]),
                    "captured_context": {
                        "nation": direct_headers.get("nation"),
                        "currency": direct_headers.get("currency"),
                        "rate": direct_headers.get("rate"),
                        "language": direct_headers.get("language"),
                    },
                }
            except Exception as exc:
                result[label] = {"email": email, "error": repr(exc)}
            finally:
                ctx.close()
        browser.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
