# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
import os
import sys

sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

SCREENSHOTS = r"d:\test_workspace\会员体系\测试文档\执行报告\screenshots"
os.makedirs(SCREENSHOTS, exist_ok=True)

FRONT_USER = "359901314@qq.com"
FRONT_PASS = "123456"


def login_www(page):
    page.goto("http://lying-www.hubbuyer.com/", timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(6000)
    agree = page.locator("button").filter(has_text="Agree").first
    if agree.count() > 0:
        agree.click()
        page.wait_for_timeout(1000)

    page.screenshot(path=os.path.join(SCREENSHOTS, "tc_cl_www_before_login_click.webp"), full_page=True)
    clicked = page.evaluate(
        """() => {
          const btns = Array.from(document.querySelectorAll('button'))
            .filter(b => {
              const t = (b.innerText || b.textContent || '').trim();
              const r = b.getBoundingClientRect();
              return r.width > 0 && r.height > 0 && (t === 'Login' || t === '登录');
            });
          const target = btns[0];
          if (target) { target.click(); return target.innerText || target.textContent; }
          return '';
        }"""
    )
    print(f"[LOGIN] clicked={clicked}")
    page.wait_for_timeout(2500)
    page.screenshot(path=os.path.join(SCREENSHOTS, "tc_cl_www_after_login_click.webp"), full_page=True)
    page.wait_for_selector("input[type='password']", timeout=10000)
    text_inputs = page.locator("input[type='text']:visible").all()
    password_input = page.locator("input[type='password']:visible").last
    email_input = text_inputs[-1]
    email_input.fill(FRONT_USER)
    password_input.fill(FRONT_PASS)
    submit = page.locator(".el-overlay-dialog button").filter(has_text="Login").first
    submit.click()
    page.wait_for_timeout(6000)


def main():
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        try:
            print("[LOGIN] www 前台登录")
            login_www(page)
            page.screenshot(path=os.path.join(SCREENSHOTS, "tc_cl_www_login_after_submit.webp"), full_page=True)
            html = page.content()
            if "退出登录" in html or "Logout" in html:
                results["WWW_LOGIN"] = "Pass"
            else:
                results["WWW_LOGIN"] = "Blocked-Auth (login state not visible)"

            print("[TC-CL-INTRO-002] 登录后费用页")
            page.goto("https://lying-www.hubbuyer.com/zh/fee", timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
            page.screenshot(path=os.path.join(SCREENSHOTS, "tc_cl_intro_002_www_login_fee.webp"), full_page=True)
            fee_html = page.content()
            if ("退出登录" in fee_html or "Logout" in fee_html) and any(
                token in fee_html for token in ["会员", "企业会员", "VIP", "CNY", "JPY", "USD"]
            ):
                results["TC-CL-INTRO-002"] = "Pass"
            else:
                results["TC-CL-INTRO-002"] = "Fail (fee page did not show logged-in member pricing context)"

            print("[B2B] 复用登录态访问 B2B 首页")
            page.goto("https://lying-b2b.hubbuyer.com/", timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
            page.screenshot(path=os.path.join(SCREENSHOTS, "tc_cl_b2b_after_www_login.webp"), full_page=True)
            b2b_html = page.content()
            if any(token in b2b_html for token in ["CHN11", "退出登录", "企业会员", "会员", "Alibaba"]):
                results["B2B_SESSION"] = "Pass"
            else:
                results["B2B_SESSION"] = "Blocked-Auth (B2B login state not visible)"

            print("[CART] 购物车页可达性烟测")
            page.goto("https://lying-b2b.hubbuyer.com/user/cart/index", timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
            page.screenshot(path=os.path.join(SCREENSHOTS, "tc_cl_cart_after_www_login.webp"), full_page=True)
            cart_html = page.content()
            if any(token in cart_html for token in ["购物车", "Cart", "Next Step", "Total", "总价"]):
                results["CART_REACHABILITY"] = "Pass"
            else:
                results["CART_REACHABILITY"] = "Blocked-Data (cart empty or cart context not rendered)"
        except Exception as exc:
            results["EXECUTION"] = f"Error: {exc}"
        finally:
            browser.close()

    print("=" * 60)
    for tc, result in results.items():
        mark = "✅" if "Pass" in result else "❌" if "Fail" in result else "⚠️"
        print(f"{mark} {tc}: {result}")


if __name__ == "__main__":
    main()
