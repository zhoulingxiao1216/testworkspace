# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
import os
import sys

sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

SCREENSHOTS = r"d:\test_workspace\会员体系\测试文档\执行报告\screenshots"
os.makedirs(SCREENSHOTS, exist_ok=True)


def admin_login(page):
    page.goto("https://lying-admin.hubbuyer.com/login", timeout=30000)
    page.wait_for_selector("input", timeout=10000)
    inputs = page.locator("input").all()
    inputs[0].fill("admin")
    inputs[1].fill("123333")
    page.locator("button").filter(has_text="登录").click()
    page.wait_for_timeout(3000)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        opened = []
        requests = []
        responses = []

        ctx.on("page", lambda new_page: opened.append(new_page))
        page.on(
            "request",
            lambda req: requests.append(req.url)
            if any(key in req.url.lower() for key in ["sso", "login", "member", "user"])
            else None,
        )
        page.on(
            "response",
            lambda resp: responses.append(resp)
            if "impersonatelogin" in resp.url.lower()
            else None,
        )

        try:
            admin_login(page)
            page.goto("https://lying-admin.hubbuyer.com/admin/user/list", timeout=30000)
            page.wait_for_timeout(3000)

            expand_btn = page.locator("text=展开").first
            if expand_btn.count() > 0:
                expand_btn.click()
                page.wait_for_timeout(1000)

            email = "dyzlxmay@qq.com"
            email_input = page.locator("input[placeholder*='邮箱']").first
            if email_input.count() > 0:
                email_input.fill(email)
            else:
                visible_inputs = page.locator("input.el-input__inner:visible").all()
                if visible_inputs:
                    visible_inputs[0].fill(email)
            page.locator("button").filter(has_text="查询").first.click()
            page.wait_for_timeout(3000)

            page.screenshot(path=os.path.join(SCREENSHOTS, "sso_probe_admin_list.webp"), full_page=True)

            buttons = page.locator("button").all()
            print(f"buttons={len(buttons)}")
            for i, btn in enumerate(buttons[:80]):
                text = (btn.inner_text(timeout=1000) or "").strip().replace("\n", " ")
                if text:
                    print(f"button[{i}]={text}")

            btn = page.locator("button").filter(has_text="会员中心").first
            if btn.count() == 0:
                print("result=blocked:no_member_center_button")
                return 2

            btn.click()
            page.wait_for_timeout(1000)
            page.screenshot(path=os.path.join(SCREENSHOTS, "sso_probe_popconfirm.webp"), full_page=True)

            confirm_btn = page.locator(".el-popper button").filter(has_text="确定").first
            if confirm_btn.count() == 0:
                confirm_btn = page.locator("button").filter(has_text="确定").last

            before_url = page.url
            confirm_btn.click()
            page.wait_for_timeout(8000)
            after_url = page.url

            print(f"before_url={before_url}")
            print(f"after_url={after_url}")
            print(f"opened_pages={len(opened)}")
            for idx, opened_page in enumerate(opened):
                try:
                    opened_page.wait_for_load_state(timeout=10000)
                    print(f"opened[{idx}]={opened_page.url}")
                    opened_page.screenshot(
                        path=os.path.join(SCREENSHOTS, f"sso_probe_opened_{idx}.webp"),
                        full_page=True,
                    )
                    opened_page.goto("https://lying-www.hubbuyer.com/fee", timeout=30000)
                    opened_page.wait_for_timeout(5000)
                    opened_page.screenshot(
                        path=os.path.join(SCREENSHOTS, f"sso_probe_fee_{idx}.webp"),
                        full_page=True,
                    )
                    html = opened_page.content()
                    fee_ok = any(token in html for token in ["会员", "Member", "VIP", "企业会员", "%", "USD", "JPY", "CNY"])
                    print(f"fee_page_ok={fee_ok} title={opened_page.title()} url={opened_page.url}")
                except Exception as exc:
                    print(f"opened[{idx}]=error:{exc}")

            print("matched_requests:")
            for req_url in requests[-30:]:
                print(req_url)

            print("impersonate_responses:")
            for resp in responses[-5:]:
                try:
                    print(f"status={resp.status} url={resp.url}")
                    print(resp.text()[:1000])
                except Exception as exc:
                    print(f"response_read_error={exc}")

            if opened:
                print("result=pass:page_opened")
                return 0
            if after_url != before_url:
                print("result=pass:same_page_navigated")
                return 0
            print("result=blocked:no_popup_or_navigation")
            return 2
        except Exception as exc:
            print(f"result=error:{exc}")
            return 1
        finally:
            browser.close()


if __name__ == "__main__":
    sys.exit(main())
