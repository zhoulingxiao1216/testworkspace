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
    result = {
        "target_email": "codex.jp.001@hubbuyer.test",
        "TC-CL-SN-001": "NotRun",
        "TC-CL-SN-002": "Blocked-Dep",
        "TC-CL-SN-003": "Blocked-Dep",
        "evidence": {},
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = ctx.new_page()
        try:
            admin_login(page)
            front = open_sso(page, result["target_email"])
            front.goto("https://lying-b2b.hubbuyer.com/user/cart/index", timeout=30000, wait_until="domcontentloaded")
            front.wait_for_timeout(6000)
            try:
                front.mouse.click(1145, 978)
                front.wait_for_timeout(800)
            except Exception:
                pass
            for y in [280, 385]:
                front.mouse.click(194, y)
                front.wait_for_timeout(300)
            front.mouse.click(1354, 967)
            front.wait_for_timeout(5000)
            save(front, "tc_cl_sn_additional_initial.webp")

            try:
                front.mouse.click(1109, 163)
                front.wait_for_timeout(500)
            except Exception:
                pass
            tab = front.get_by_text("番号管理").first
            if tab.count() > 0:
                tab.click(timeout=5000)
                front.wait_for_timeout(3000)
            save(front, "tc_cl_sn_number_tab.webp")

            text = front.locator("body").inner_text(timeout=8000)
            inputs = front.evaluate(
                """() => Array.from(document.querySelectorAll('input,textarea'))
                  .map((el, idx) => {
                    const r = el.getBoundingClientRect();
                    return {idx, tag: el.tagName, placeholder: el.getAttribute('placeholder') || '', value: el.value || '', visible: r.width > 0 && r.height > 0};
                  }).filter(i => i.visible)"""
            )
            result["evidence"] = {
                "url": front.url,
                "has_number_tab": "番号管理" in text,
                "has_number_input_keyword": any(k in text for k in ["番号要求", "番号", "要求", "Request", "要求事項"]),
                "visible_inputs": inputs[:20],
                "text_head": text[:1600],
            }
            if result["evidence"]["has_number_input_keyword"] and inputs:
                result["TC-CL-SN-001"] = "Pass"
                result["TC-CL-SN-002"] = "NotExecuted (input present; toggle-off not performed)"
                result["TC-CL-SN-003"] = "NotExecuted (requires quantity mutation)"
            elif result["evidence"]["has_number_tab"]:
                result["TC-CL-SN-001"] = "Blocked-Data (number management tab exists but no input/option content visible)"
            else:
                result["TC-CL-SN-001"] = "Blocked-Config (number management not enabled or tab unavailable)"
        except Exception as exc:
            result["error"] = repr(exc)
        finally:
            browser.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
