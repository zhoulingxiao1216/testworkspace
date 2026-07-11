# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
import json
import os
import sys

sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

SCREENSHOTS = r"D:\test_workspace\会员体系\测试文档\执行报告\screenshots"
os.makedirs(SCREENSHOTS, exist_ok=True)


def screenshot(page, name):
    page.screenshot(path=os.path.join(SCREENSHOTS, name), full_page=True)


def login_www(page, email, password):
    page.goto("http://lying-www.hubbuyer.com/", timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(5000)
    agree = page.locator("button").filter(has_text="Agree").first
    if agree.count() > 0:
        agree.click()
        page.wait_for_timeout(800)
    login_button = page.locator("button").filter(has_text="Login").first
    if login_button.count() == 0:
        login_button = page.locator("button").filter(has_text="登录").first
    login_button.click()
    page.wait_for_selector("input[type='password']", timeout=12000)
    text_inputs = page.locator("input[type='text']:visible").all()
    text_inputs[-1].fill(email)
    page.locator("input[type='password']:visible").last.fill(password)
    submit = page.locator(".el-overlay-dialog button").filter(has_text="Login").first
    if submit.count() == 0:
        submit = page.locator("button").filter(has_text="登录").last
    submit.click()
    page.wait_for_timeout(6000)


def force_logout(page):
    try:
        page.mouse.click(1364, 26)
        page.wait_for_timeout(4000)
    except Exception:
        pass
    page.evaluate("localStorage.clear(); sessionStorage.clear();")
    page.wait_for_timeout(500)


def storage_text(page):
    return page.evaluate(
        """() => JSON.stringify({
          localStorage: Object.fromEntries(Array.from({length: localStorage.length}, (_, i) => [localStorage.key(i), localStorage.getItem(localStorage.key(i))])),
          sessionStorage: Object.fromEntries(Array.from({length: sessionStorage.length}, (_, i) => [sessionStorage.key(i), sessionStorage.getItem(sessionStorage.key(i))]))
        })"""
    )


def main():
    result = {
        "TC-CL-LIFE-006": "NotRun",
        "TC-SE-003": "NotRun",
        "TC-SE-004": "NotRun",
        "evidence": {},
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        try:
            login_www(page, "359901314@qq.com", "123456")
            page.goto("https://lying-b2b.hubbuyer.com/user/cart/index", timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)
            screenshot(page, "tc_cross_account_china_cart.webp")
            china_text = page.locator("body").inner_text(timeout=10000)

            force_logout(page)

            login_www(page, "dyzlxmay@qq.com", "123456")
            page.goto("https://lying-b2b.hubbuyer.com/user/cart/index", timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)
            screenshot(page, "tc_cross_account_us_cart.webp")
            us_cart_text = page.locator("body").inner_text(timeout=10000)
            us_storage = storage_text(page)

            page.goto("https://lying-www.hubbuyer.com/en/fee", timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
            screenshot(page, "tc_cross_account_us_fee.webp")
            us_fee_text = page.locator("body").inner_text(timeout=10000)

            china_markers = ["CHN11", "359901314@qq.com", "厂家仿獭兔毛球挂件", "义乌市一鑫饰品"]
            us_markers = ["USA11", "dyzlxmay@qq.com", "Logout", "退出登录"]
            has_china_residue = any(m in us_cart_text or m in us_fee_text or m in us_storage for m in china_markers)
            us_login_visible = any(m in us_cart_text or m in us_fee_text or m in us_storage for m in us_markers)
            cart_empty_like = any(token in us_cart_text for token in [": 0/0", "SKU: 0", "Cart is empty", "购物车为空", "No Data"])

            result["evidence"] = {
                "china_cart_logged_in": any(m in china_text for m in ["CHN11", "购物车"]),
                "us_login_visible": us_login_visible,
                "has_china_residue_after_us_login": has_china_residue,
                "us_cart_empty_like": cart_empty_like,
                "us_cart_head": us_cart_text[:800],
                "us_fee_head": us_fee_text[:800],
            }

            if us_login_visible and not has_china_residue:
                result["TC-SE-003"] = "Pass (no previous China account markers in US session)"
            elif us_login_visible:
                result["TC-SE-003"] = "Fail (previous China account markers remain after switching to US)"
            else:
                result["TC-SE-003"] = "Blocked-Auth (US login state not visible)"

            if us_login_visible and not has_china_residue:
                result["TC-SE-004"] = "Pass (US cart did not carry China account cart markers)"
            elif us_login_visible:
                result["TC-SE-004"] = "Fail (US cart shows previous account cart markers)"
            else:
                result["TC-SE-004"] = "Blocked-Auth"

            if us_login_visible and not has_china_residue and cart_empty_like:
                result["TC-CL-LIFE-006"] = "Pass"
            elif us_login_visible and not has_china_residue:
                result["TC-CL-LIFE-006"] = "Blocked-Data (US cart is not provably empty, but no cross-account residue found)"
            elif us_login_visible:
                result["TC-CL-LIFE-006"] = "Fail (cross-account residue found)"
            else:
                result["TC-CL-LIFE-006"] = "Blocked-Auth"
        except Exception as exc:
            result["error"] = repr(exc)
        finally:
            browser.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
