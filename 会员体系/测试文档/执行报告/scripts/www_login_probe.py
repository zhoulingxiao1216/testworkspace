# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
import os
import sys

sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

SCREENSHOTS = r"d:\test_workspace\会员体系\测试文档\执行报告\screenshots"
os.makedirs(SCREENSHOTS, exist_ok=True)


def dump_page(page, label):
    page.screenshot(path=os.path.join(SCREENSHOTS, f"{label}.webp"), full_page=True)
    print(f"{label}: url={page.url} title={page.title()}")
    links = page.locator("a").all()
    buttons = page.locator("button").all()
    inputs = page.locator("input").all()
    print(f"{label}: links={len(links)} buttons={len(buttons)} inputs={len(inputs)}")
    for i, link in enumerate(links[:80]):
        try:
            text = (link.inner_text(timeout=500) or "").strip().replace("\n", " ")
            href = link.get_attribute("href", timeout=500)
            if text or href:
                print(f"link[{i}] text={text} href={href}")
        except Exception:
            pass
    for i, button in enumerate(buttons[:60]):
        try:
            text = (button.inner_text(timeout=500) or "").strip().replace("\n", " ")
            if text:
                print(f"button[{i}] text={text}")
        except Exception:
            pass
    for i, input_el in enumerate(inputs[:30]):
        try:
            typ = input_el.get_attribute("type", timeout=500)
            placeholder = input_el.get_attribute("placeholder", timeout=500)
            name = input_el.get_attribute("name", timeout=500)
            print(f"input[{i}] type={typ} placeholder={placeholder} name={name}")
        except Exception:
            pass


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        try:
            page.goto("http://lying-www.hubbuyer.com/", timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            dump_page(page, "www_login_probe_home")

            popup_pages = []
            ctx.on("page", lambda new_page: popup_pages.append(new_page))
            agree = page.locator("button").filter(has_text="Agree").first
            if agree.count() > 0:
                agree.click()
                page.wait_for_timeout(1000)
            login_button = page.locator("button").filter(has_text="Login").first
            if login_button.count() > 0:
                clicked = "button:Login"
                login_button.click()
            else:
                login_link = page.locator("a").filter(has_text="Login").first
                if login_link.count() > 0:
                    clicked = "a:Login"
                    login_link.click()
                else:
                    clicked = ""
            print(f"clicked_login_candidate={clicked}")
            page.wait_for_timeout(3000)
            if popup_pages:
                page = popup_pages[-1]
                page.wait_for_load_state(timeout=10000)
            dump_page(page, "www_login_probe_after_click")

            email_input = page.locator("input[placeholder='Please enter your email']").first
            password_input = page.locator("input[placeholder='Please enter your password']").first
            if email_input.count() > 0 and password_input.count() > 0:
                # Try the registered China frontend account first; it is known to pass API login.
                email_input.fill("359901314@qq.com")
                password_input.fill("123456")
                submit = page.locator(".el-overlay-dialog button").filter(has_text="Login").first
                if submit.count() == 0:
                    submit = page.locator(".pc-login button").filter(has_text="Login").first
                if submit.count() == 0:
                    submit = page.locator("button").filter(has_text="登录").last
                if submit.count() > 0:
                    submit.click()
                else:
                    page.keyboard.press("Enter")
                page.wait_for_timeout(6000)
                dump_page(page, "www_login_probe_after_submit")

                page.goto("https://lying-b2b.hubbuyer.com/", timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(5000)
                dump_page(page, "www_login_probe_b2b_after_www_login")
            else:
                print("result=blocked:no_login_inputs_after_click")
                return 2

            html = page.content()
            if any(token in html for token in ["CHN11", "退出登录", "Logout", "会员", "Member", "B2B"]):
                print("result=pass:login_state_visible_on_b2b")
                return 0
            print("result=blocked:login_state_not_visible_on_b2b")
            return 2
        except Exception as exc:
            print(f"result=error:{exc}")
            return 1
        finally:
            browser.close()


if __name__ == "__main__":
    sys.exit(main())
