# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import json
import os
import sys

sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

SCREENSHOTS = r"D:\test_workspace\会员体系\测试文档\执行报告\screenshots"
os.makedirs(SCREENSHOTS, exist_ok=True)

TARGET_EMAIL = os.getenv("TARGET_EMAIL", "codex.jp.001@hubbuyer.test")
LABEL = os.getenv("LABEL", "cod_jp_001")


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


def accept_notice(page):
    for text in ["Agree", "同意", "同意する", "OK"]:
        try:
            btn = page.locator("button").filter(has_text=text).first
            if btn.count() > 0 and btn.is_visible(timeout=800):
                btn.click(timeout=1500)
                page.wait_for_timeout(1000)
                return
        except Exception:
            pass


def click_button(page, keyword, min_y=0):
    clicked = page.evaluate(
        """({ keyword, minY }) => {
          const items = Array.from(document.querySelectorAll('button,a,[role="button"],.el-button'))
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
              return { el, y: r.y, x: r.x, text: (el.innerText || el.textContent || '').trim() };
            })
            .sort((a, b) => a.y - b.y || a.x - b.x);
          if (!items.length) return '';
          items[0].el.click();
          return items[0].text;
        }""",
        {"keyword": keyword, "minY": min_y},
    )
    if clicked:
        page.wait_for_timeout(2500)
    return clicked


def main():
    result = {"target_email": TARGET_EMAIL, "checkout_opened": False}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = ctx.new_page()
        try:
            admin_login(page)
            front = open_sso(page)
            front.goto("https://lying-www.hubbuyer.com/zh/fee", timeout=30000, wait_until="domcontentloaded")
            front.wait_for_timeout(6000)
            accept_notice(front)
            front.wait_for_timeout(2000)
            save(front, f"cl_pay_checkout_{LABEL}_fee.webp")
            if not click_button(front, "今すぐ加入", min_y=300):
                click_button(front, "立即加入", min_y=300)
            front.wait_for_timeout(2000)
            save(front, f"cl_pay_checkout_{LABEL}_member_modal.webp")
            if not click_button(front, "今すぐ加入", min_y=300):
                click_button(front, "立即加入", min_y=300)
            front.wait_for_timeout(5000)
            save(front, f"cl_pay_checkout_{LABEL}_checkout.webp")
            text = front.locator("body").inner_text(timeout=8000)
            html = front.content()
            result["checkout_opened"] = any(k in (text + html).lower() for k in ["stripe", "paypal", "apple pay", "google pay", "checkout", "チェックアウト"])
            result["third_party"] = any(k in (text + html).lower() for k in ["stripe", "paypal", "apple pay", "google pay", "visa", "mastercard"])
            result["bank_or_deposit_text"] = any(k in text for k in ["銀行", "入金", "振込", "汇款", "银行", "充值", "チャージ"])
            result["body_text_head"] = text[:3500]
            controls = front.evaluate(
                """() => Array.from(document.querySelectorAll('button,a,input,textarea,[role="button"]'))
                  .map((el, idx) => {
                    const r = el.getBoundingClientRect();
                    return {
                      idx,
                      tag: el.tagName,
                      type: el.getAttribute('type') || '',
                      text: (el.innerText || el.textContent || el.getAttribute('placeholder') || el.getAttribute('aria-label') || '').trim().replace(/\\s+/g, ' '),
                      visible: r.width > 0 && r.height > 0,
                      disabled: !!el.disabled || el.getAttribute('aria-disabled') === 'true'
                    };
                  })
                  .filter(i => i.visible && (i.text || i.tag === 'INPUT' || i.tag === 'TEXTAREA'))"""
            )
            result["controls"] = controls[:80]
        except Exception as exc:
            result["error"] = repr(exc)
        finally:
            browser.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
