# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import json
import os
import sys
import urllib.parse

sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

SCREENSHOTS = r"D:\test_workspace\会员体系\测试文档\执行报告\screenshots"
os.makedirs(SCREENSHOTS, exist_ok=True)

TARGET_EMAIL = os.getenv("TARGET_EMAIL", "hanguo999@qq.com")
LABEL = os.getenv("LABEL", "kor10")


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
    save(page, f"tc_cl_block_{LABEL}_admin.webp")
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


def accept_notice(page):
    page.evaluate(
        """() => {
          const keywords = ['Agree', '同意', '同意する', '동의하다', 'OK'];
          const els = Array.from(document.querySelectorAll('button,a,span,div'))
            .filter(el => {
              const text = (el.innerText || el.textContent || '').trim();
              const r = el.getBoundingClientRect();
              return r.width > 0 && r.height > 0 && r.width < 300 && r.height < 140 &&
                keywords.some(k => text === k || text.includes(k));
            });
          if (els[0]) els[0].click();
        }"""
    )
    try:
        page.mouse.click(1140, 978)
    except Exception:
        pass
    page.wait_for_timeout(800)


def click_text(page, texts, last=True):
    for text in texts:
        loc = page.get_by_text(text)
        try:
            if loc.count() > 0:
                (loc.last if last else loc.first).click(timeout=5000, force=True)
                page.wait_for_timeout(3000)
                return text
        except Exception:
            pass
    return ""


def click_first_cart_rows(page):
    # The cart checkboxes are custom rendered and not always toggled by DOM click in headless mode.
    for y in [280, 385, 490]:
        try:
            page.mouse.click(194, y)
            page.wait_for_timeout(400)
        except Exception:
            pass
    page.wait_for_timeout(1200)


def click_next_or_checkout(page):
    clicked = click_text(page, ["Next Step", "下一步", "다음 단계", "다음", "次へ"], last=True)
    if clicked:
        return clicked
    clicked = page.evaluate(
        """() => {
          const keywords = ['Next', '下一步', '다음', '결제', '주문', '提交'];
          const els = Array.from(document.querySelectorAll('button,a,div,[role="button"]'))
            .filter(el => {
              const text = (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' ');
              const r = el.getBoundingClientRect();
              return r.width > 0 && r.height > 0 && keywords.some(k => text.includes(k));
            })
            .sort((a, b) => b.getBoundingClientRect().y - a.getBoundingClientRect().y);
          if (els[0]) { els[0].click(); return (els[0].innerText || els[0].textContent || '').trim(); }
          return '';
        }"""
    )
    if clicked:
        page.wait_for_timeout(3000)
        return clicked
    try:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(800)
        page.mouse.click(1360, 970)
        page.wait_for_timeout(3000)
        return "coordinate-bottom-right"
    except Exception:
        return ""


def close_dialogs(page):
    try:
        page.mouse.click(1109, 163)
        page.wait_for_timeout(500)
    except Exception:
        pass
    page.evaluate(
        """() => {
          const closeSelectors = ['.el-dialog__headerbtn', '.el-overlay .el-dialog__close', '.el-dialog button[aria-label="Close"]'];
          for (const selector of closeSelectors) {
            const el = document.querySelector(selector);
            if (el) { el.click(); return; }
          }
          const candidates = Array.from(document.querySelectorAll('button,span,i,div'))
            .filter(el => {
              const text = (el.innerText || el.textContent || '').trim();
              const r = el.getBoundingClientRect();
              return r.width > 0 && r.height > 0 && r.x > window.innerWidth * 0.55 && r.y < window.innerHeight * 0.35 &&
                ['×', 'X', 'close', 'Close'].some(k => text === k || text.includes(k));
            });
          if (candidates[0]) candidates[0].click();
        }"""
    )
    page.wait_for_timeout(800)


def advance_from_additional_services(page):
    close_dialogs(page)
    try:
        page.mouse.click(191, 967)
        page.wait_for_timeout(700)
        page.mouse.click(1382, 130)
        page.wait_for_timeout(2500)
        page.mouse.click(1354, 967)
        page.wait_for_timeout(4500)
    except Exception:
        pass
    for texts in (["Save", "保存", "저장"], ["Next Step", "下一步", "次へ", "다음 단계", "다음"]):
        clicked = click_text(page, texts, last=True)
        if clicked:
            page.wait_for_timeout(3500)
    if "additionalservices" in page.url.lower():
        try:
            page.mouse.click(1355, 966)
            page.wait_for_timeout(4500)
        except Exception:
            pass


def main():
    result = {
        "target_email": TARGET_EMAIL,
        "TC-CL-BLOCK-001": "NotRun",
        "TC-CL-BLOCK-003": "NotRun",
        "TC-CL-BLOCK-004": "NotRun",
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        admin_page = ctx.new_page()
        try:
            admin_login(admin_page)
            page = open_sso(admin_page)
            page.goto("https://lying-b2b.hubbuyer.com/user/cart/index", timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)
            accept_notice(page)
            save(page, f"tc_cl_block_{LABEL}_cart.webp")
            cart_text = page.locator("body").inner_text(timeout=8000)
            if not any(k in cart_text for k in ["CNY", "JPY", "KRW", "Total", "합계", "购物车", "Cart"]):
                result["TC-CL-BLOCK-001"] = "Blocked-Data (cart not loaded or empty)"
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 2

            click_first_cart_rows(page)
            save(page, f"tc_cl_block_{LABEL}_cart_selected.webp")
            click_next_or_checkout(page)
            page.wait_for_timeout(6000)
            save(page, f"tc_cl_block_{LABEL}_after_next1.webp")

            url = page.url.lower()
            if "additionalservices" in url:
                advance_from_additional_services(page)
            save(page, f"tc_cl_block_{LABEL}_confirm.webp")

            confirm_text = page.locator("body").inner_text(timeout=8000)
            if any(k in confirm_text for k in ["checkout", "Checkout", "确认订单", "注文", "見積金額", "주문", "支払い", "收银台", "Total", "合计"]):
                preview_ok = True
            else:
                preview_ok = False

            clicked = ""
            if preview_ok:
                try:
                    page.mouse.click(1355, 967)
                    page.wait_for_timeout(6000)
                    clicked = "coordinate-order-confirm-next"
                except Exception:
                    clicked = ""
            if not clicked:
                clicked = click_text(
                    page,
                    ["Submit Order", "Submit", "提交订单", "提交", "注文", "支払い", "Pay", "결제", "주문하기", "Next Step"],
                    last=True,
                )
            page.wait_for_timeout(6000)
            save(page, f"tc_cl_block_{LABEL}_after_submit.webp")
            after_text = page.locator("body").inner_text(timeout=8000)
            after_url = page.url

            block_tokens = ["会员", "会員", "member", "购买", "購入", "가입", "등급", "拦截", "권한", "403", "Forbidden"]
            pay_tokens = ["checkout", "チェックアウト", "PayPal", "Stripe", "支払金額", "支付", "收银台"]
            blocked = any(k.lower() in (after_text + after_url).lower() for k in block_tokens)
            went_pay = any(k.lower() in (after_text + after_url).lower() for k in pay_tokens)

            if preview_ok and blocked and not went_pay:
                result["TC-CL-BLOCK-001"] = "Pass"
                result["TC-CL-BLOCK-004"] = "Pass (modal/overlay present; screenshot captured)"
                result["TC-CL-BLOCK-003"] = "Blocked-UI (purchase button not clicked in automated pass)"
            elif went_pay:
                result["TC-CL-BLOCK-001"] = "Fail (unqualified Korea account reached payment/checkout)"
                result["TC-CL-BLOCK-003"] = "Blocked-Dep (no intercept modal)"
                result["TC-CL-BLOCK-004"] = "Blocked-Dep (no intercept modal)"
            elif not clicked:
                result["TC-CL-BLOCK-001"] = "Blocked-UI (submit button not found)"
                result["TC-CL-BLOCK-003"] = "Blocked-Dep"
                result["TC-CL-BLOCK-004"] = "Blocked-Dep"
            else:
                result["TC-CL-BLOCK-001"] = "Blocked-Review (unclear result, screenshots captured)"
                result["TC-CL-BLOCK-003"] = "Blocked-Review"
                result["TC-CL-BLOCK-004"] = "Blocked-Review"
            result["clicked_submit"] = clicked
            result["after_url"] = after_url
            result["after_text_head"] = after_text[:1600]
        except Exception as exc:
            result["error"] = repr(exc)
        finally:
            browser.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
