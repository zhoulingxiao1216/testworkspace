# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import json
import os
import sys
import time

sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "helpers"))
from db_helper import query  # noqa: E402

SCREENSHOTS = r"D:\test_workspace\会员体系\测试文档\执行报告\screenshots"
os.makedirs(SCREENSHOTS, exist_ok=True)

TARGET_UUID = os.getenv("TARGET_UUID", "JPN9")
TARGET_EMAIL = os.getenv("TARGET_EMAIL", "1443721555@qq.com")


def save(page, name):
    page.screenshot(path=os.path.join(SCREENSHOTS, name), full_page=True)


def account_snapshot():
    rows = query(
        "SELECT u.uuid,u.email,u.nation,b.balance,r.member_level_uuid,c.name_language,"
        "r.member_start_at,r.member_expire_at,r.role_auto_renew "
        "FROM user u "
        "LEFT JOIN b2b_user b ON b.user_uuid=u.uuid "
        "LEFT JOIN b2b_user_role r ON r.user_uuid=u.uuid "
        "LEFT JOIN b2b_member_level_config c ON c.uuid=r.member_level_uuid "
        "WHERE u.uuid=%s",
        (TARGET_UUID,),
    )
    return rows[0] if rows else None


def admin_login(page):
    page.goto("https://lying-admin.hubbuyer.com/login", timeout=30000)
    page.wait_for_selector("input", timeout=10000)
    inputs = page.locator("input").all()
    inputs[0].fill("admin")
    inputs[1].fill("123333")
    page.locator("button").filter(has_text="登录").click()
    page.wait_for_timeout(3500)


def open_sso_page(page):
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
    save(page, "cl_pay_insufficient_admin_filtered.webp")
    btn = page.locator("button").filter(has_text="会员中心").first
    if btn.count() == 0:
        raise RuntimeError("no_member_center_button")
    btn.click()
    page.wait_for_timeout(1000)
    confirm_btn = page.locator(".el-popper button").filter(has_text="确定").first
    if confirm_btn.count() == 0:
        confirm_btn = page.locator("button").filter(has_text="确定").last
    try:
        with page.expect_popup(timeout=8000) as popup_info:
            confirm_btn.click()
        frontend_page = popup_info.value
        frontend_page.wait_for_load_state(timeout=15000)
        frontend_page.wait_for_timeout(5000)
        return frontend_page
    except PlaywrightTimeoutError:
        page.wait_for_timeout(6000)
        return opened[-1] if opened else page


def accept_cookie_or_notice(page):
    for text in ["Agree", "同意", "同意する", "OK"]:
        try:
            btn = page.locator("button").filter(has_text=text).first
            if btn.count() > 0 and btn.is_visible(timeout=800):
                btn.click(timeout=1500)
                page.wait_for_timeout(1000)
                return
        except Exception:
            pass
    try:
        page.evaluate(
            """() => {
              const keywords = ['Agree', '同意', '同意する', 'OK'];
              const els = Array.from(document.querySelectorAll('button,a,span,div'))
                .filter(el => {
                  const text = (el.innerText || el.textContent || '').trim();
                  const r = el.getBoundingClientRect();
                  return r.width > 0 && r.height > 0 && r.width < 280 && r.height < 120 &&
                    keywords.some(k => text === k || text.includes(k));
                });
              if (els[0]) els[0].click();
            }"""
        )
        page.wait_for_timeout(1000)
    except Exception:
        pass


def click_topmost_button(page, keyword, min_y=0):
    clicked = page.evaluate(
        """({ keyword, minY }) => {
          const buttons = Array.from(document.querySelectorAll('button,a,[role="button"],.el-button'))
            .filter(el => {
              const text = (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' ');
              const r = el.getBoundingClientRect();
              if (!text.includes(keyword) || r.width <= 0 || r.height <= 0 || r.y < minY) return false;
              const cx = r.left + r.width / 2;
              const cy = r.top + r.height / 2;
              const top = document.elementFromPoint(cx, cy);
              return top === el || el.contains(top) || (top && top.closest('button,a,[role="button"],.el-button') === el);
            })
            .map(el => {
              const r = el.getBoundingClientRect();
              return { el, y: r.y, x: r.x };
            })
            .sort((a, b) => a.y - b.y);
          if (!buttons.length) return '';
          buttons[0].el.click();
          return (buttons[0].el.innerText || buttons[0].el.textContent || '').trim();
        }""",
        {"keyword": keyword, "minY": min_y},
    )
    if clicked:
        page.wait_for_timeout(2500)
    return clicked


def main():
    result = {
        "case": "TC-CL-PAY-002",
        "target": TARGET_UUID,
        "before": account_snapshot(),
        "after": None,
        "status": "NotRun",
    }
    if not result["before"]:
        result["status"] = "Blocked-Data (account not found)"
        print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
        return 2

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        admin_page = ctx.new_page()
        try:
            admin_login(admin_page)
            page = open_sso_page(admin_page)
            page.goto("https://lying-www.hubbuyer.com/zh/fee", timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)
            accept_cookie_or_notice(page)
            page.wait_for_timeout(2000)
            save(page, "cl_pay_insufficient_fee_initial.webp")
            opened = click_topmost_button(page, "今すぐ加入", min_y=300)
            if not opened:
                opened = click_topmost_button(page, "立即加入", min_y=300)
            if not opened:
                result["status"] = "Blocked-UI (purchase button not clickable)"
                print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
                return 2
            page.wait_for_timeout(2500)
            save(page, "cl_pay_insufficient_before_submit.webp")
            final_clicked = click_topmost_button(page, "今すぐ加入", min_y=300) or click_topmost_button(page, "立即加入", min_y=300)
            page.wait_for_timeout(5000)
            save(page, "cl_pay_insufficient_after_submit.webp")
            text = page.locator("body").inner_text(timeout=5000)
            html = page.content()
            combined = (text + "\n" + html).lower()
            if any(token in combined for token in ["stripe", "paypal", "apple pay", "google pay", "credit card", "visa", "mastercard"]):
                result["status"] = "Fail (insufficient balance still enters third-party checkout)"
            elif any(token.lower() in combined for token in ["残高不足", "余额不足", "insufficient balance", "balance insufficient"]):
                result["status"] = "Pass"
            elif final_clicked:
                result["status"] = "Fail (submit allowed without insufficient-balance block)"
            else:
                result["status"] = "Blocked-UI (final button not clickable or no visible result)"
        except Exception as exc:
            result["status"] = f"Error ({repr(exc)})"
        finally:
            browser.close()

    time.sleep(3)
    result["after"] = account_snapshot()
    print("=" * 60)
    print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
    return 0 if result["status"] == "Pass" else 1


if __name__ == "__main__":
    sys.exit(main())
