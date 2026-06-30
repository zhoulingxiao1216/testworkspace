# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
import os
import sys

sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

SCREENSHOTS = r"d:\test_workspace\会员体系\测试文档\执行报告\screenshots"
os.makedirs(SCREENSHOTS, exist_ok=True)

TARGET_EMAIL = "359901314@qq.com"


def admin_login(page):
    page.goto("https://lying-admin.hubbuyer.com/login", timeout=30000)
    page.wait_for_selector("input", timeout=10000)
    inputs = page.locator("input").all()
    inputs[0].fill("admin")
    inputs[1].fill("123333")
    page.locator("button").filter(has_text="登录").click()
    page.wait_for_timeout(3000)


def main():
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        try:
            admin_login(page)
            page.goto("https://lying-admin.hubbuyer.com/admin/user/list", timeout=30000)
            page.wait_for_timeout(3000)

            expand_btn = page.locator("text=展开").first
            if expand_btn.count() > 0:
                expand_btn.click()
                page.wait_for_timeout(1000)

            email_input = page.locator("input[placeholder*='邮箱']").first
            if email_input.count() > 0:
                email_input.fill(TARGET_EMAIL)
            else:
                visible_inputs = page.locator("input.el-input__inner:visible").all()
                if visible_inputs:
                    visible_inputs[0].fill(TARGET_EMAIL)
            page.locator("button").filter(has_text="查询").first.click()
            page.wait_for_timeout(3000)
            page.screenshot(path=os.path.join(SCREENSHOTS, "mg_detail_probe_list.webp"), full_page=True)

            row = page.locator("tr.el-table__row").filter(has_text=TARGET_EMAIL).first
            if row.count() == 0:
                results["MG_DETAIL_ENTRY"] = "Blocked-Data (target account not found)"
            else:
                detail = row.locator("button").filter(has_text="详情").first
                detail.click()
                page.wait_for_timeout(3000)
                page.screenshot(path=os.path.join(SCREENSHOTS, "mg_detail_probe_dialog.webp"), full_page=True)
                body_text = page.inner_text("body")
                if "会员等级" in body_text and ("会员到期时间" in body_text or "账户余额" in body_text):
                    results["TC-MG-008"] = "Pass (detail page exposes member level/expiry controls)"
                else:
                    results["TC-MG-008"] = "Blocked-ENV (member controls not visible)"

                page.evaluate(
                    """() => {
                      const selects = Array.from(document.querySelectorAll('.el-dialog .el-select'));
                      const target = selects.find(s => (s.innerText || '').includes('会员')) || selects[0];
                      if (target) target.click();
                    }"""
                )
                page.wait_for_timeout(1000)
                options = page.evaluate(
                    """() => Array.from(document.querySelectorAll('.el-select-dropdown__item'))
                      .map(el => (el.innerText || '').trim())
                      .filter(Boolean)"""
                )
                print("member_level_options=" + "|".join(options))
                if any("VIP" in opt for opt in options) and any("一般" in opt or "企业" in opt for opt in options):
                    results["TC-MG-013_PRECHECK"] = "Pass (member level dropdown has target levels)"
                else:
                    results["TC-MG-013_PRECHECK"] = "Blocked-ENV (level options incomplete)"
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
