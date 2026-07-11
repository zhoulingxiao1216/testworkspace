# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import json
import os
import sys

sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

TARGET_EMAIL = os.getenv("TARGET_EMAIL", "codex.jp.001@hubbuyer.test")


def admin_login(page):
    page.goto("https://lying-admin.hubbuyer.com/login", timeout=30000)
    page.wait_for_selector("input", timeout=10000)
    inputs = page.locator("input").all()
    inputs[0].fill("admin")
    inputs[1].fill("123333")
    page.locator("button").filter(has_text="登录").click()
    page.wait_for_timeout(3500)


def open_sso(page):
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
        email_input.fill(TARGET_EMAIL)
    else:
        page.locator("input.el-input__inner:visible").first.fill(TARGET_EMAIL)
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


def safe_headers(headers):
    keep = {}
    for key, value in headers.items():
        lk = key.lower()
        if lk in ("authorization", "cookie", "x-token", "token"):
            keep[key] = "<redacted>"
        elif lk.startswith("sec-"):
            continue
        else:
            keep[key] = value
    return keep


def main():
    events = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = ctx.new_page()

        def on_response(resp):
            req = resp.request
            if req.resource_type not in ("xhr", "fetch"):
                return
            if "lying-api.hubbuyer.com/api_b2b" not in resp.url:
                return
            item = {
                "method": req.method,
                "status": resp.status,
                "url": resp.url,
                "post_data": (req.post_data or "")[:1000],
                "headers": safe_headers(req.headers),
            }
            try:
                body = resp.text()
                item["body_head"] = body[:1000]
            except Exception as exc:
                item["body_error"] = repr(exc)
            events.append(item)

        try:
            admin_login(page)
            front = open_sso(page)
            front.on("response", on_response)
            front.goto("https://lying-b2b.hubbuyer.com/user/cart/index", timeout=30000, wait_until="domcontentloaded")
            front.wait_for_timeout(6000)
            try:
                front.mouse.click(1145, 978)
            except Exception:
                pass
            for y in [280, 385]:
                front.mouse.click(194, y)
                front.wait_for_timeout(300)
            front.mouse.click(1354, 967)
            front.wait_for_timeout(8000)
            try:
                front.mouse.click(1109, 163)
                front.wait_for_timeout(800)
            except Exception:
                pass
        finally:
            browser.close()
    unique = []
    keys = set()
    for event in events:
        key = (event["method"], event["url"], event["post_data"])
        if key in keys:
            continue
        keys.add(key)
        unique.append(event)
    print(json.dumps({"target_email": TARGET_EMAIL, "events": unique}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
