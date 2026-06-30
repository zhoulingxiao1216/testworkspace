# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
import json
import sys

sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

FRONT_USER = "359901314@qq.com"
FRONT_PASS = "123456"


def login_www(page):
    page.goto("http://lying-www.hubbuyer.com/", timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(5000)
    agree = page.locator("button").filter(has_text="Agree").first
    if agree.count() > 0:
        agree.click()
        page.wait_for_timeout(800)
    page.locator("button").filter(has_text="Login").first.click()
    page.wait_for_selector("input[type='password']", timeout=10000)
    text_inputs = page.locator("input[type='text']:visible").all()
    text_inputs[-1].fill(FRONT_USER)
    page.locator("input[type='password']:visible").last.fill(FRONT_PASS)
    page.locator(".el-overlay-dialog button").filter(has_text="Login").first.click()
    page.wait_for_timeout(6000)


def main():
    seen = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        def on_response(resp):
            req = resp.request
            if req.resource_type not in ("xhr", "fetch"):
                return
            url = resp.url
            if "hubbuyer.com" not in url:
                return
            try:
                ctype = resp.header_value("content-type") or ""
            except Exception:
                ctype = ""
            seen.append({
                "method": req.method,
                "status": resp.status,
                "type": req.resource_type,
                "url": url,
                "content_type": ctype[:80],
                "post_data": (req.post_data or "")[:500],
            })

        page.on("response", on_response)
        try:
            login_www(page)
            for url in [
                "https://lying-b2b.hubbuyer.com/",
                "https://lying-b2b.hubbuyer.com/user/cart/index",
                "https://lying-www.hubbuyer.com/fee",
                "https://lying-www.hubbuyer.com/zh/fee",
            ]:
                try:
                    page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    page.wait_for_timeout(7000)
                except Exception:
                    pass
        finally:
            browser.close()
    unique = []
    seen_keys = set()
    for item in seen:
        key = (item["method"], item["url"])
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique.append(item)
    print(json.dumps(unique[-80:], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
