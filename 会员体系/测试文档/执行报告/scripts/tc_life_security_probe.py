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


def screenshot(page, name):
    page.screenshot(path=os.path.join(SCREENSHOTS, name), full_page=True)


def storage_snapshot(page):
    return page.evaluate(
        """() => {
          const dump = (store) => {
            const out = [];
            for (let i = 0; i < store.length; i++) {
              const key = store.key(i);
              const value = store.getItem(key) || '';
              out.push({
                key,
                value_len: value.length,
                hit: /level|country|custom|member|vip|token|user/i.test(key + ' ' + value)
              });
            }
            return out;
          };
          return {localStorage: dump(localStorage), sessionStorage: dump(sessionStorage)};
        }"""
    )


def sensitive_hits(snapshot):
    hits = []
    for scope in ("localStorage", "sessionStorage"):
        for item in snapshot.get(scope, []):
            if item.get("hit"):
                hits.append({"scope": scope, "key": item.get("key"), "value_len": item.get("value_len")})
    return hits


def login_www(page):
    page.goto("http://lying-www.hubbuyer.com/", timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(5000)
    agree = page.locator("button").filter(has_text="Agree").first
    if agree.count() > 0:
        agree.click()
        page.wait_for_timeout(800)
    login_button = page.locator("button").filter(has_text="Login").first
    if login_button.count() == 0:
        login_button = page.locator("button").filter(has_text="登录").first
    login_button.click()
    page.wait_for_selector("input[type='password']", timeout=10000)
    text_inputs = page.locator("input[type='text']:visible").all()
    page.locator("input[type='password']:visible").last.fill(FRONT_PASS)
    text_inputs[-1].fill(FRONT_USER)
    submit = page.locator(".el-overlay-dialog button").filter(has_text="Login").first
    if submit.count() == 0:
        submit = page.locator("button").filter(has_text="登录").last
    submit.click()
    page.wait_for_timeout(6000)


def click_logout(page):
    try:
        page.mouse.click(1364, 26)
        page.wait_for_timeout(2500)
        if "login" in page.url.lower() or "登录" in page.locator("body").inner_text(timeout=3000):
            return "coordinate-top-right"
    except Exception:
        pass
    clicked = page.evaluate(
        """() => {
          const keywords = ['退出登录', 'Logout', 'ログアウト', '로그아웃'];
          const els = Array.from(document.querySelectorAll('button,a,span'))
            .filter(el => {
              const text = (el.innerText || el.textContent || '').trim();
              const r = el.getBoundingClientRect();
              return r.width > 0 && r.height > 0 && r.width < 220 && r.height < 80 &&
                keywords.some(k => text === k || (text.includes(k) && text.length < 30));
            })
            .sort((a, b) => b.getBoundingClientRect().x - a.getBoundingClientRect().x);
          if (els[0]) { els[0].click(); return (els[0].innerText || els[0].textContent || '').trim(); }
          return '';
        }"""
    )
    page.wait_for_timeout(4000)
    return clicked


def cookie_header(cookies):
    pairs = []
    for cookie in cookies:
        if "hubbuyer.com" in cookie.get("domain", ""):
            pairs.append(f"{cookie['name']}={cookie['value']}")
    return "; ".join(pairs)


def main():
    result = {
        "TC-CL-LIFE-005": "NotRun",
        "TC-SE-006": "NotRun",
        "evidence": {},
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        try:
            login_www(page)
            page.goto("https://lying-b2b.hubbuyer.com/user/cart/index", timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)
            screenshot(page, "tc_life_security_before_logout.webp")
            before_storage = storage_snapshot(page)
            before_hits = sensitive_hits(before_storage)
            before_cookie_header = cookie_header(ctx.cookies())
            before_text = page.locator("body").inner_text(timeout=10000)

            clicked_logout = click_logout(page)
            page.wait_for_timeout(3000)
            screenshot(page, "tc_life_security_after_logout.webp")
            after_storage = storage_snapshot(page)
            after_hits = sensitive_hits(after_storage)
            after_text = page.locator("body").inner_text(timeout=10000)

            result["evidence"]["before_sensitive_keys"] = before_hits
            result["evidence"]["after_sensitive_keys"] = after_hits
            result["evidence"]["logout_clicked"] = clicked_logout
            result["evidence"]["after_url"] = page.url

            logged_out = any(token in page.url.lower() for token in ["sign", "login", "auth"]) or not any(
                token in after_text for token in ["CHN11", "退出登录", "购物车"]
            )

            if logged_out and not after_hits:
                result["TC-CL-LIFE-005"] = "Pass"
            elif logged_out or clicked_logout:
                result["TC-CL-LIFE-005"] = "Fail (storage sensitive keys remain after logout)"
            else:
                result["TC-CL-LIFE-005"] = "Blocked-UI (logout button not found)"

            replay_ctx = p.request.new_context(
                ignore_https_errors=True,
                extra_http_headers={"Cookie": before_cookie_header, "User-Agent": "Agent2-readonly-security-probe"},
            )
            replay = replay_ctx.get("https://lying-b2b.hubbuyer.com/user/cart/index", timeout=30000)
            replay_text = replay.text()[:5000]
            replay_ctx.dispose()
            leaked = any(token in replay_text for token in ["CHN11", FRONT_USER, "退出登录", "Myカート", "购物车"])
            result["evidence"]["old_cookie_replay_status"] = replay.status
            result["evidence"]["old_cookie_replay_contains_logged_in_marker"] = leaked
            result["evidence"]["before_page_logged_in_marker"] = any(token in before_text for token in ["CHN11", "退出登录", "购物车"])
            result["evidence"]["after_page_logged_in_marker"] = any(token in after_text for token in ["CHN11", "退出登录", "购物车"])
            result["evidence"]["logged_out_detected"] = logged_out

            if leaked:
                result["TC-SE-006"] = "Fail (old cookie can still fetch logged-in B2B page after logout)"
            else:
                result["TC-SE-006"] = "Pass (old cookie replay did not expose logged-in page marker)"
        except Exception as exc:
            result["error"] = repr(exc)
        finally:
            browser.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
