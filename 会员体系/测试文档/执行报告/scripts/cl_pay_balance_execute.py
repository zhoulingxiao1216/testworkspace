# -*- coding: utf-8 -*-
from decimal import Decimal
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

TARGET_UUID = "COD-JP-001"
TARGET_EMAIL = "codex.jp.001@hubbuyer.test"
EXPECTED_FEE = Decimal("55000.00")
EXPECTED_LEVEL = "MLV-UP-001"


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


def open_sso_page(page, ctx):
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
        visible_inputs = page.locator("input.el-input__inner:visible").all()
        visible_inputs[0].fill(TARGET_EMAIL)
    page.locator("button").filter(has_text="查询").first.click()
    page.wait_for_timeout(3500)
    save(page, "cl_pay_exec_admin_filtered.webp")

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
        confirm_btn.click()
        page.wait_for_timeout(6000)
        return page


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


def select_no_auto_renew(page):
    clicked = page.evaluate(
        """() => {
          const els = Array.from(document.querySelectorAll('label,span,div'))
            .filter(el => {
              const text = (el.innerText || el.textContent || '').trim();
              const r = el.getBoundingClientRect();
              return r.width > 0 && r.height > 0 && (text === 'いいえ' || text === '否' || text === 'No');
            });
          const target = els[0];
          if (target) { target.click(); return (target.innerText || target.textContent || '').trim(); }
          return '';
        }"""
    )
    page.wait_for_timeout(1000)
    return clicked


def confirm_if_needed(page):
    for text in ["確定", "确认", "确定", "はい", "OK", "Confirm"]:
        try:
            btn = page.locator("button").filter(has_text=text).last
            if btn.count() > 0 and btn.is_visible(timeout=1200):
                btn.click(timeout=2000)
                page.wait_for_timeout(4000)
                return text
        except Exception:
            pass
    return ""


def main():
    result = {
        "case": "TC-CL-PAY-001",
        "target": TARGET_UUID,
        "before": None,
        "after": None,
        "payment_clicked": False,
        "status": "NotRun",
    }
    before = account_snapshot()
    result["before"] = before
    if not before:
        result["status"] = "Blocked-Data (account not found)"
        print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
        return 2
    if Decimal(str(before["balance"])) < EXPECTED_FEE:
        result["status"] = "Blocked-Data (balance insufficient before execution)"
        print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
        return 2

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        admin_page = ctx.new_page()
        try:
            admin_login(admin_page)
            page = open_sso_page(admin_page, ctx)
            page.goto("https://lying-www.hubbuyer.com/zh/fee", timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)
            accept_cookie_or_notice(page)
            page.wait_for_timeout(2000)
            save(page, "cl_pay_exec_fee_initial.webp")

            opened = click_topmost_button(page, "今すぐ加入", min_y=300)
            if not opened:
                result["status"] = "Blocked-UI (purchase button not clickable)"
                save(page, "cl_pay_exec_blocked_no_purchase.webp")
                print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
                return 2
            page.wait_for_timeout(2500)
            select_no_auto_renew(page)
            save(page, "cl_pay_exec_before_confirm.webp")
            visible_text = page.locator("body").inner_text(timeout=5000)
            if any(token in visible_text for token in ["PayPal", "Stripe", "信用卡", "Credit Card", "VISA", "Mastercard"]):
                result["status"] = "Blocked-Safety (third-party payment entry visible)"
                print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
                return 2

            final_clicked = click_topmost_button(page, "今すぐ加入", min_y=300)
            result["payment_clicked"] = bool(final_clicked)
            if not final_clicked:
                result["status"] = "Blocked-UI (final join button not clickable)"
                print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
                return 2
            page.wait_for_timeout(5000)
            save(page, "cl_pay_exec_checkout_opened.webp")
            checkout_text = page.locator("body").inner_text(timeout=5000)
            if "当前のアカウント残高" not in checkout_text and "現在のアカウント残高" not in checkout_text and "当前账户余额" not in checkout_text:
                result["status"] = "Blocked-Safety (balance payment option not visible in checkout)"
                print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
                return 2
            pay_clicked = click_topmost_button(page, "今すぐ支払う", min_y=150)
            if not pay_clicked:
                pay_clicked = click_topmost_button(page, "立即支付", min_y=150)
            if not pay_clicked:
                result["status"] = "Blocked-UI (balance pay button not clickable)"
                print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
                return 2
            confirm_if_needed(page)
            page.wait_for_timeout(8000)
            save(page, "cl_pay_exec_after_payment.webp")
        except Exception as exc:
            result["status"] = f"Error ({repr(exc)})"
        finally:
            browser.close()

    # Poll DB after the UI payment to allow async writes/cache invalidation.
    after = None
    for _ in range(8):
        time.sleep(3)
        after = account_snapshot()
        if after and after["member_level_uuid"] == EXPECTED_LEVEL:
            break
    result["after"] = after

    if after and result["payment_clicked"]:
        before_balance = Decimal(str(before["balance"]))
        after_balance = Decimal(str(after["balance"]))
        deducted = before_balance - after_balance
        result["deducted_balance"] = str(deducted)
        if after["member_level_uuid"] == EXPECTED_LEVEL and deducted > Decimal("0.00"):
            result["status"] = "Pass"
        elif after["member_level_uuid"] == EXPECTED_LEVEL:
            result["status"] = "Fail (level changed but balance was not deducted)"
        else:
            result["status"] = "Fail (payment clicked but member level did not become Business)"

    print("=" * 60)
    print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
    return 0 if result["status"] == "Pass" else 1


if __name__ == "__main__":
    sys.exit(main())
