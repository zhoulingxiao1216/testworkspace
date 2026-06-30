# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import json
import os
import sys

sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

SCREENSHOTS = r"D:\test_workspace\会员体系\测试文档\执行报告\screenshots"
os.makedirs(SCREENSHOTS, exist_ok=True)

TARGET_EMAIL = os.getenv("TARGET_EMAIL", "codex.jp.001@hubbuyer.test")


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
    btn = page.locator("button").filter(has_text="会员中心").first
    if btn.count() == 0:
        raise RuntimeError("no member center button")
    btn.click()
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


def page_summary(page, label):
    for text in ["Agree", "同意", "同意する", "OK"]:
        try:
            btn = page.locator("button").filter(has_text=text).first
            if btn.count() > 0 and btn.is_visible(timeout=800):
                btn.click(timeout=1500)
                page.wait_for_timeout(2000)
                break
        except Exception:
            pass
    save(page, f"cl_pay_history_{label}.webp")
    text = page.locator("body").inner_text(timeout=8000)
    controls = page.evaluate(
        """() => Array.from(document.querySelectorAll('a,button,[role="button"]'))
          .map((el, idx) => {
            const r = el.getBoundingClientRect();
            const text = (el.innerText || el.textContent || el.getAttribute('aria-label') || '').trim().replace(/\\s+/g, ' ');
            return {idx, tag: el.tagName, text, href: el.href || el.getAttribute('href') || '', visible: r.width > 0 && r.height > 0};
          })
          .filter(i => i.visible && i.text)"""
    )
    return {
        "label": label,
        "url": page.url,
        "hit": any(k in text for k in ["入金", "充值", "残高", "余额", "履歴", "历史", "审核", "拒绝", "チャージ", "銀行", "银行"]),
        "text_head": text[:1800],
        "controls": controls[:80],
    }


def main():
    routes = [
        "https://lying-b2b.hubbuyer.com/",
        "https://lying-b2b.hubbuyer.com/user/account/index",
        "https://lying-b2b.hubbuyer.com/user/account/recharge",
        "https://lying-b2b.hubbuyer.com/user/recharge/index",
        "https://lying-b2b.hubbuyer.com/user/recharge/list",
        "https://lying-b2b.hubbuyer.com/user/member/index",
        "https://lying-b2b.hubbuyer.com/user/member/recharge",
        "https://lying-b2b.hubbuyer.com/user/balance/index",
        "https://lying-b2b.hubbuyer.com/user/finance/index",
        "https://lying-b2b.hubbuyer.com/user/payment/index",
    ]
    result = {"target_email": TARGET_EMAIL, "pages": []}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = ctx.new_page()
        try:
            admin_login(page)
            front = open_sso(page)
            for idx, url in enumerate(routes):
                front.goto(url, timeout=30000, wait_until="domcontentloaded")
                front.wait_for_timeout(4000)
                result["pages"].append(page_summary(front, f"route_{idx}"))
        except Exception as exc:
            result["error"] = repr(exc)
        finally:
            browser.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
