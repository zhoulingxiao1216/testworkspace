# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import json
import os
import sys

sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

SCREENSHOTS = r"D:\test_workspace\会员体系\测试文档\执行报告\screenshots"
os.makedirs(SCREENSHOTS, exist_ok=True)


def save(page, name):
    page.screenshot(path=os.path.join(SCREENSHOTS, name), full_page=True)


def admin_login(page):
    page.goto("https://lying-admin.hubbuyer.com/login", timeout=30000)
    page.wait_for_selector("input", timeout=10000)
    inputs = page.locator("input").all()
    inputs[0].fill("admin")
    inputs[1].fill("123333")
    page.locator("button").filter(has_text="登录").click()
    page.wait_for_timeout(3500)


def sso_to(page, email):
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


def storage_blob(page):
    return page.evaluate(
        """() => JSON.stringify({
          localStorage: Object.fromEntries(Array.from({length: localStorage.length}, (_, i) => [localStorage.key(i), localStorage.getItem(localStorage.key(i))])),
          sessionStorage: Object.fromEntries(Array.from({length: sessionStorage.length}, (_, i) => [sessionStorage.key(i), sessionStorage.getItem(sessionStorage.key(i))]))
        })"""
    )


def main():
    result = {"TC-SE-004": "NotRun", "evidence": {}}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        admin_page = ctx.new_page()
        try:
            admin_login(admin_page)
            jp = sso_to(admin_page, "codex.jp.001@hubbuyer.test")
            jp.goto("https://lying-b2b.hubbuyer.com/user/cart/index", timeout=30000, wait_until="domcontentloaded")
            jp.wait_for_timeout(6000)
            save(jp, "tc_se_switch_jp_cart.webp")
            jp_text = jp.locator("body").inner_text(timeout=10000)

            # Reuse the same browser context, then switch to a different country/account through Admin SSO.
            kr = sso_to(admin_page, "hanguo999@qq.com")
            kr.goto("https://lying-b2b.hubbuyer.com/user/cart/index", timeout=30000, wait_until="domcontentloaded")
            kr.wait_for_timeout(6000)
            save(kr, "tc_se_switch_kr_cart.webp")
            kr_text = kr.locator("body").inner_text(timeout=10000)
            kr_storage = storage_blob(kr)

            jp_markers = ["COD-JP-001", "codex-life007-after", "JPY", "ビジネス会員"]
            kr_markers = ["KOR10", "KRW", "한국어", "마이 카트"]
            residue = any(m in kr_text or m in kr_storage for m in jp_markers)
            kr_visible = any(m in kr_text or m in kr_storage for m in kr_markers)
            result["evidence"] = {
                "jp_cart_visible": any(m in jp_text for m in jp_markers),
                "kr_context_visible": kr_visible,
                "jp_residue_after_switch": residue,
                "kr_text_head": kr_text[:1000],
            }
            if kr_visible and not residue:
                result["TC-SE-004"] = "Pass (same browser context switched JP member -> KR normal; no JP cart/price residue)"
            elif kr_visible:
                result["TC-SE-004"] = "Fail (JP cart/price residue visible after switching to KR)"
            else:
                result["TC-SE-004"] = "Blocked-Auth (KR context not visible)"
        except Exception as exc:
            result["error"] = repr(exc)
        finally:
            browser.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
