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


def filter_customer(page, email):
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
        visible_inputs = page.locator("input.el-input__inner:visible").all()
        if visible_inputs:
            visible_inputs[0].fill(email)
    page.locator("button").filter(has_text="查询").first.click()
    page.wait_for_timeout(3500)
    save(page, "cl_pay_sso_admin_filtered.webp")


def open_member_center(page, ctx):
    opened = []
    ctx.on("page", lambda new_page: opened.append(new_page))
    btn = page.locator("button").filter(has_text="会员中心").first
    if btn.count() == 0:
        return None, "no_member_center_button"
    btn.click()
    page.wait_for_timeout(1000)
    save(page, "cl_pay_sso_popconfirm.webp")
    confirm_btn = page.locator(".el-popper button").filter(has_text="确定").first
    if confirm_btn.count() == 0:
        confirm_btn = page.locator("button").filter(has_text="确定").last
    try:
        with page.expect_popup(timeout=8000) as popup_info:
            confirm_btn.click()
        frontend_page = popup_info.value
        frontend_page.wait_for_load_state(timeout=15000)
        frontend_page.wait_for_timeout(5000)
        return frontend_page, "popup"
    except PlaywrightTimeoutError:
        page.wait_for_timeout(6000)
        if opened:
            frontend_page = opened[-1]
            frontend_page.wait_for_load_state(timeout=15000)
            return frontend_page, "event_page"
        if page.url != "https://lying-admin.hubbuyer.com/admin/user/list":
            return page, "same_page"
        return None, "no_popup_or_navigation"


def collect_clickables(page):
    return page.evaluate(
        """() => Array.from(document.querySelectorAll('button,a,[role="button"],.el-button'))
          .map((el, idx) => {
            const r = el.getBoundingClientRect();
            const text = (el.innerText || el.textContent || el.getAttribute('aria-label') || '').trim().replace(/\\s+/g, ' ');
            return {
              idx,
              tag: el.tagName,
              text,
              href: el.href || el.getAttribute('href') || '',
              visible: r.width > 0 && r.height > 0,
              disabled: !!el.disabled || el.getAttribute('aria-disabled') === 'true' || el.className.toString().includes('disabled'),
              x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)
            };
          })
          .filter(item => item.visible && item.text)
        """
    )


def click_by_item(page, item):
    try:
        page.mouse.click(item["x"] + item["w"] / 2, item["y"] + item["h"] / 2)
        return True
    except Exception:
        return page.evaluate(
            """(idx) => {
              const items = Array.from(document.querySelectorAll('button,a,[role="button"],.el-button'));
              if (!items[idx]) return false;
              items[idx].scrollIntoView({block: 'center', inline: 'center'});
              items[idx].click();
              return true;
            }""",
            item["idx"],
        )


def accept_cookie_or_notice(page):
    for text in ["Agree", "同意", "同意する", "OK"]:
        try:
            btn = page.locator("button").filter(has_text=text).first
            if btn.count() > 0 and btn.is_visible(timeout=800):
                btn.click(timeout=1500)
                page.wait_for_timeout(1000)
                return True
        except Exception:
            pass
    try:
        clicked = page.evaluate(
            """() => {
              const keywords = ['Agree', '同意', '同意する', 'OK'];
              const els = Array.from(document.querySelectorAll('button,a,span,div'))
                .filter(el => {
                  const text = (el.innerText || el.textContent || '').trim();
                  const r = el.getBoundingClientRect();
                  return r.width > 0 && r.height > 0 && r.width < 280 && r.height < 120 &&
                    keywords.some(k => text === k || text.includes(k));
                });
              const target = els[0];
              if (target) { target.click(); return (target.innerText || target.textContent || '').trim(); }
              return '';
            }"""
        )
        if clicked:
            page.wait_for_timeout(1000)
            return True
    except Exception:
        pass
    return False


def main():
    result = {
        "target_email": TARGET_EMAIL,
        "sso": "not_started",
        "candidate_count": 0,
        "modal_or_navigation": False,
        "balance_entry": False,
        "third_party_entry": False,
    }
    buy_keywords = ["购买", "升级", "开通", "续费", "支付", "加入", "Buy", "Purchase", "Upgrade", "Renew", "Pay", "Join"]
    balance_keywords = ["余额", "Balance", "account balance", "会员费账户"]
    third_party_keywords = ["PayPal", "Stripe", "paypal.com", "stripe.com", "信用卡", "Credit Card", "VISA", "Mastercard"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        admin_page = ctx.new_page()
        try:
            admin_login(admin_page)
            filter_customer(admin_page, TARGET_EMAIL)
            frontend_page, mode = open_member_center(admin_page, ctx)
            result["sso"] = mode
            if not frontend_page:
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 2

            save(frontend_page, "cl_pay_sso_front_member_center.webp")
            print(f"[SSO] mode={mode} url={frontend_page.url}")

            frontend_page.goto("https://lying-www.hubbuyer.com/zh/fee", timeout=30000, wait_until="domcontentloaded")
            frontend_page.wait_for_timeout(6000)
            accept_cookie_or_notice(frontend_page)
            frontend_page.wait_for_timeout(5000)
            save(frontend_page, "cl_pay_sso_fee_initial.webp")
            body = frontend_page.locator("body").inner_text(timeout=5000)
            print("[FEE_TEXT_HEAD]")
            print(body[:2200])

            clickables = collect_clickables(frontend_page)
            candidates = [
                item for item in clickables
                if not item["disabled"] and any(k.lower() in item["text"].lower() for k in buy_keywords)
            ]
            result["candidate_count"] = len(candidates)
            print("[PURCHASE_CANDIDATES]")
            for item in candidates[:20]:
                print(json.dumps(item, ensure_ascii=False))

            page_before = frontend_page.url + "\n" + body
            for seq, item in enumerate(candidates[:6], start=1):
                print(f"[OPEN_CANDIDATE] {seq}: {item['text']}")
                click_by_item(frontend_page, item)
                frontend_page.wait_for_timeout(4000)
                save(frontend_page, f"cl_pay_sso_candidate_{seq}.webp")
                after_text = frontend_page.locator("body").inner_text(timeout=5000)
                print("[AFTER_CLICK_TEXT_HEAD]")
                print(after_text[:2600])
                print(f"[AFTER_CLICK_URL] {frontend_page.url}")
                combined = frontend_page.url + "\n" + after_text
                if combined != page_before:
                    result["modal_or_navigation"] = True
                if any(k.lower() in combined.lower() for k in balance_keywords):
                    result["balance_entry"] = True
                if any(k.lower() in combined.lower() for k in third_party_keywords):
                    result["third_party_entry"] = True
                if result["modal_or_navigation"] or result["balance_entry"] or result["third_party_entry"]:
                    break
        except Exception as exc:
            result["error"] = repr(exc)
        finally:
            browser.close()

    print("=" * 60)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
