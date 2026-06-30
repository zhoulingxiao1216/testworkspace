# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
import json
import os
import sys

sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

SCREENSHOTS = r"D:\test_workspace\会员体系\测试文档\执行报告\screenshots"
os.makedirs(SCREENSHOTS, exist_ok=True)

FRONT_USER = "359901314@qq.com"
FRONT_PASS = "123456"


def save(page, name):
    page.screenshot(path=os.path.join(SCREENSHOTS, name), full_page=True)


def login_www(page):
    page.goto("http://lying-www.hubbuyer.com/", timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(5000)
    save(page, "cl_pay_fee_probe_home.webp")
    agree = page.locator("button").filter(has_text="Agree").first
    if agree.count() > 0:
        agree.click()
        page.wait_for_timeout(800)

    login_button = page.locator("button").filter(has_text="Login").first
    if login_button.count() > 0:
        login_button.click()
    else:
        login_link = page.locator("a").filter(has_text="Login").first
        if login_link.count() > 0:
            login_link.click()
        else:
            page.evaluate(
                """() => {
                  const btns = Array.from(document.querySelectorAll('button,a'))
                    .filter(b => {
                      const text = (b.innerText || b.textContent || '').trim();
                      const r = b.getBoundingClientRect();
                      return r.width > 0 && r.height > 0 && (text === 'Login' || text === '登录');
                    });
                  if (btns[0]) btns[0].click();
                }"""
            )
    page.wait_for_timeout(2000)
    save(page, "cl_pay_fee_probe_after_login_click.webp")
    email_input = page.locator("input[placeholder='Please enter your email']").first
    password_input = page.locator("input[placeholder='Please enter your password']").first
    if email_input.count() == 0 or password_input.count() == 0:
        page.wait_for_selector("input[type='password']", timeout=10000)
        text_inputs = page.locator("input[type='text']:visible").all()
        email_input = text_inputs[-1]
        password_input = page.locator("input[type='password']:visible").last
    email_input.fill(FRONT_USER)
    password_input.fill(FRONT_PASS)
    submit = page.locator(".el-overlay-dialog button").filter(has_text="Login").first
    if submit.count() == 0:
        submit = page.locator(".pc-login button").filter(has_text="Login").first
    if submit.count() == 0:
        submit = page.locator("button").filter(has_text="登录").last
    if submit.count() > 0:
        submit.click()
    else:
        page.keyboard.press("Enter")
    page.wait_for_timeout(5000)
    save(page, "cl_pay_fee_probe_after_submit.webp")


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
              x: Math.round(r.x),
              y: Math.round(r.y),
              w: Math.round(r.width),
              h: Math.round(r.height)
            };
          })
          .filter(item => item.visible && item.text)
        """
    )


def accept_cookie_or_notice(page):
    for text in ["Agree", "同意", "确定", "OK"]:
        btn = page.locator("button").filter(has_text=text).first
        try:
            if btn.count() > 0 and btn.is_visible(timeout=800):
                btn.click(timeout=1500)
                page.wait_for_timeout(800)
                return True
        except Exception:
            pass
    try:
        clicked = page.evaluate(
            """() => {
              const keywords = ['Agree', '同意', '确定', 'OK'];
              const els = Array.from(document.querySelectorAll('button,a,span,div'))
                .filter(el => {
                  const text = (el.innerText || el.textContent || '').trim();
                  const r = el.getBoundingClientRect();
                  return r.width > 0 && r.height > 0 && r.width < 260 && r.height < 120 &&
                    keywords.some(k => text === k || text.includes(k));
                });
              const target = els[0];
              if (target) { target.click(); return (target.innerText || target.textContent || '').trim(); }
              return '';
            }"""
        )
        if clicked:
            page.wait_for_timeout(800)
            return True
    except Exception:
        pass
    return False


def click_clickable(page, item):
    try:
        page.mouse.click(item["x"] + item["w"] / 2, item["y"] + item["h"] / 2)
        return True
    except Exception:
        return page.evaluate(
            """(idx) => {
          const items = Array.from(document.querySelectorAll('button,a,[role="button"],.el-button'));
          const el = items[idx];
          if (!el) return false;
          el.scrollIntoView({block: 'center', inline: 'center'});
          el.click();
          return true;
        }""",
            item["idx"],
        )


def main():
    result = {"candidate_count": 0, "modal_opened": False, "balance_entry": False, "third_party_entry": False}
    buy_keywords = [
        "购买", "升级", "开通", "续费", "支付", "加入",
        "Buy", "Purchase", "Upgrade", "Renew", "Pay", "Subscribe", "Join"
    ]
    balance_keywords = ["余额", "Balance", "account balance", "会员费账户"]
    third_party_keywords = ["PayPal", "Stripe", "paypal.com", "stripe.com", "信用卡", "Credit Card", "VISA", "Mastercard"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = ctx.new_page()
        try:
            login_www(page)
            print("[LOGIN] OK via lying-www")

            page.goto("https://lying-www.hubbuyer.com/zh/fee", timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)
            accept_cookie_or_notice(page)
            page.wait_for_timeout(1000)
            save(page, "cl_pay_fee_probe_initial.webp")

            body = page.locator("body").inner_text(timeout=5000)
            print("[FEE_TEXT_HEAD]")
            print(body[:2500])

            clickables = collect_clickables(page)
            candidates = [
                item for item in clickables
                if not item["disabled"] and any(k.lower() in item["text"].lower() for k in buy_keywords)
            ]
            result["candidate_count"] = len(candidates)
            print("[VISIBLE_CLICKABLES]")
            for item in clickables[:80]:
                print(json.dumps(item, ensure_ascii=False))
            print("[PURCHASE_CANDIDATES]")
            for item in candidates[:20]:
                print(json.dumps(item, ensure_ascii=False))

            text_all = (body + "\n" + "\n".join([c.get("href", "") for c in clickables]))
            result["third_party_entry"] = any(k.lower() in text_all.lower() for k in third_party_keywords)

            for seq, item in enumerate(candidates[:8], start=1):
                print(f"[OPEN_CANDIDATE] {seq}: {item['text']}")
                page.goto("https://lying-www.hubbuyer.com/zh/fee", timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                accept_cookie_or_notice(page)
                page.wait_for_timeout(800)
                ok = click_clickable(page, item)
                page.wait_for_timeout(3500)
                save(page, f"cl_pay_fee_probe_candidate_{seq}.webp")
                after_text = page.locator("body").inner_text(timeout=5000)
                print("[AFTER_CLICK_TEXT_HEAD]")
                print(after_text[:2500])
                after_url = page.url
                print(f"[AFTER_CLICK_URL] {after_url}")

                if any(k.lower() in after_text.lower() or k.lower() in after_url.lower() for k in third_party_keywords):
                    result["third_party_entry"] = True
                if any(k.lower() in after_text.lower() for k in balance_keywords):
                    result["balance_entry"] = True
                if after_text != body or after_url != "https://lying-www.hubbuyer.com/zh/fee":
                    result["modal_opened"] = True
                    break
        except Exception as exc:
            result["error"] = repr(exc)
        finally:
            browser.close()

    print("=" * 60)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
