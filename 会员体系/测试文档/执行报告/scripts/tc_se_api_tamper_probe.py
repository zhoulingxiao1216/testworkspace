# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import json
import os
import sys

sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

TARGET_EMAIL = os.getenv("TARGET_EMAIL", "codex.jp.001@hubbuyer.test")


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


def summarize(resp_json):
    data = resp_json.get("data") if isinstance(resp_json, dict) else None
    if not isinstance(data, dict):
        data = {}
    return {
        "code": resp_json.get("code") if isinstance(resp_json, dict) else None,
        "field": resp_json.get("field") if isinstance(resp_json, dict) else None,
        "message": resp_json.get("message") if isinstance(resp_json, dict) else None,
        "currency": data.get("currency"),
        "rate": data.get("rate"),
        "pay_total": data.get("pay_total"),
        "foreign_pay_total_fee": data.get("foreign_pay_total_fee"),
        "total_service_fee": data.get("total_service_fee"),
        "procurement_fee_matrix_id": (data.get("procurement_fee_matrix") or [{}])[0].get("id")
        if isinstance(data.get("procurement_fee_matrix"), list) and data.get("procurement_fee_matrix")
        else None,
    }


def main():
    result = {
        "target_email": TARGET_EMAIL,
        "TC-SE-001": "NotRun",
        "TC-SE-002": "NotRun",
        "evidence": {},
    }
    captured = {"headers": None, "body": None}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = ctx.new_page()

        def on_request(req):
            if "api_b2b/cartQuoteStep2/cartDetailListTotalFee" in req.url:
                captured["headers"] = dict(req.headers)
                captured["body"] = req.post_data or ""

        try:
            admin_login(page)
            front = open_sso(page)
            front.on("request", on_request)
            front.goto("https://lying-b2b.hubbuyer.com/user/cart/index", timeout=30000, wait_until="domcontentloaded")
            front.wait_for_timeout(6000)
            try:
                front.mouse.click(1145, 978)
            except Exception:
                pass
            for y in [280, 385]:
                front.mouse.click(194, y)
                front.wait_for_timeout(300)
            front.mouse.click(1354, 967)
            front.wait_for_timeout(5000)
            try:
                front.mouse.click(1109, 163)
            except Exception:
                pass
            front.wait_for_timeout(1000)
            front.mouse.click(1354, 967)
            front.wait_for_timeout(8000)

            if not captured["headers"] or not captured["body"]:
                result["TC-SE-001"] = "Blocked-Endpoint (fee API request not captured)"
                result["TC-SE-002"] = "Blocked-Endpoint"
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return

            base_headers = {
                k: v
                for k, v in captured["headers"].items()
                if k.lower() not in ("content-length", "host", "origin", "referer", "cookie")
            }
            api = p.request.new_context(ignore_https_errors=True)
            url = "https://lying-api.hubbuyer.com/api_b2b/cartQuoteStep2/cartDetailListTotalFee"

            def post_with(headers, body):
                resp = api.post(url, headers=headers, data=body, timeout=30000)
                try:
                    payload = resp.json()
                except Exception:
                    payload = {"raw": resp.text()[:500]}
                return {"http_status": resp.status, "summary": summarize(payload)}

            baseline = post_with(base_headers, captured["body"])

            country_headers = dict(base_headers)
            country_headers["nation"] = "America"
            country_headers["currency"] = "USD"
            country_headers["rate"] = "0.15"
            country_tamper = post_with(country_headers, captured["body"])

            level_body = captured["body"] + "&member_level_uuid=MLV-VIP-001&level_id=999&role_id=999"
            level_tamper = post_with(base_headers, level_body)
            api.dispose()

            result["evidence"] = {
                "body_shape": captured["body"],
                "baseline": baseline,
                "country_tamper": country_tamper,
                "level_tamper": level_tamper,
            }

            base_summary = baseline["summary"]
            country_summary = country_tamper["summary"]
            level_summary = level_tamper["summary"]

            country_rejected = country_tamper["http_status"] in (401, 403) or country_summary.get("code") not in (200, "200")
            country_ignored = (
                country_summary.get("currency") == base_summary.get("currency")
                and country_summary.get("rate") == base_summary.get("rate")
                and country_summary.get("foreign_pay_total_fee") == base_summary.get("foreign_pay_total_fee")
            )
            country_trusted = country_summary.get("currency") == "USD" or country_summary.get("rate") == "0.15"
            if country_rejected:
                result["TC-SE-001"] = "Pass (tampered country rejected)"
            elif country_ignored:
                result["TC-SE-001"] = "Pass (tampered country ignored; token-bound country used)"
            elif country_trusted:
                result["TC-SE-001"] = "Fail (server accepted tampered nation/currency/rate)"
            else:
                result["TC-SE-001"] = "Blocked-Review (unexpected country tamper response)"

            level_ignored = (
                level_summary.get("pay_total") == base_summary.get("pay_total")
                and level_summary.get("total_service_fee") == base_summary.get("total_service_fee")
                and level_summary.get("procurement_fee_matrix_id") == base_summary.get("procurement_fee_matrix_id")
            )
            level_rejected = level_tamper["http_status"] in (401, 403) or level_summary.get("code") not in (200, "200")
            if level_rejected:
                result["TC-SE-002"] = "Pass (tampered level rejected)"
            elif level_ignored:
                result["TC-SE-002"] = "Pass (tampered level fields ignored)"
            else:
                result["TC-SE-002"] = "Fail (tampered level changed pricing result)"
        except Exception as exc:
            result["error"] = repr(exc)
        finally:
            browser.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
