#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright


OUT_DIR = Path.cwd() / "output" / "playwright" / "agent2_login"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def visible_inputs(page):
    return page.evaluate(
        """() => [...document.querySelectorAll('input')].map((input, idx) => {
            const rect = input.getBoundingClientRect();
            return {
                idx,
                type: input.type,
                placeholder: input.placeholder,
                name: input.name,
                visible: rect.width > 0 && rect.height > 0,
                x: Math.round(rect.x),
                y: Math.round(rect.y),
                w: Math.round(rect.width),
                h: Math.round(rect.height),
            };
        }).filter(input => input.visible)"""
    )


def storage_keys(page):
    return page.evaluate(
        """() => ({
            localStorage: Object.keys(localStorage),
            sessionStorage: Object.keys(sessionStorage),
        })"""
    )


def save_artifacts(page, context, name):
    screenshot = OUT_DIR / f"{name}_post.png"
    html = OUT_DIR / f"{name}_after_login.html"
    storage = OUT_DIR / f"{name}_storage_state.json"

    page.screenshot(path=str(screenshot), full_page=True)
    html.write_text(page.content(), encoding="utf-8")
    context.storage_state(path=str(storage))

    return {
        "screenshot": str(screenshot),
        "html": str(html),
        "storage_state": str(storage),
    }


def click_first_visible_button(page):
    buttons = page.locator("button")
    for index in range(buttons.count()):
        button = buttons.nth(index)
        try:
            if button.is_visible():
                button.click(timeout=3000)
                return True
        except Exception:
            continue
    return False


def admin_login(browser):
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        ignore_https_errors=True,
    )
    page = context.new_page()
    result = {
        "name": "admin",
        "target": "https://hlc-admin.hubbuyer.com/",
        "account": "admin",
        "success": False,
    }

    try:
        page.goto(result["target"], wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)

        inputs = visible_inputs(page)
        user_idx = next(
            item["idx"]
            for item in inputs
            if item["type"] in ("text", "email") and item["w"] > 100
        )
        pwd_idx = next(item["idx"] for item in inputs if item["type"] == "password")

        page.locator("input").nth(user_idx).fill("admin")
        page.locator("input").nth(pwd_idx).fill("123333")
        if not click_first_visible_button(page):
            page.locator("input").nth(pwd_idx).press("Enter")

        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass
        page.wait_for_timeout(3000)

        keys = storage_keys(page)
        body_text = page.locator("body").inner_text(timeout=10000)
        final_inputs = visible_inputs(page)
        has_password = any(item["type"] == "password" for item in final_inputs)

        result.update(
            {
                "final_url": page.url,
                "title": page.title(),
                "cookies": [cookie["name"] for cookie in context.cookies()],
                **keys,
                "success": (
                    "/admin/user/list" in page.url
                    and "user_info" in keys["localStorage"]
                    and not has_password
                ),
                "evidence_text": body_text[:500],
            }
        )
        if not result["success"]:
            result["reason"] = "Admin login did not reach expected user list page/session."
    except Exception as exc:
        result["reason"] = str(exc)
    finally:
        result["artifacts"] = save_artifacts(page, context, "admin")
        context.close()

    return result


def front_login(browser):
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        ignore_https_errors=True,
    )
    page = context.new_page()
    result = {
        "name": "front",
        "target": "https://hlc-b2b.hubbuyer.com/",
        "account": "17706793737@163.com",
        "success": False,
    }

    try:
        page.goto(result["target"], wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)

        # The front site opens on the public home page. The login dialog is
        # triggered from the top bar, not by navigating to a standalone login URL.
        page.mouse.click(139, 14)
        page.wait_for_timeout(1500)

        inputs = visible_inputs(page)
        email_idx = next(
            item["idx"]
            for item in inputs
            if item["type"] in ("text", "email") and item["y"] > 300 and item["w"] > 300
        )
        pwd_idx = next(item["idx"] for item in inputs if item["type"] == "password")

        page.locator("input").nth(email_idx).fill("17706793737@163.com")
        page.locator("input").nth(pwd_idx).fill("123456")
        # There are hidden primary buttons in the page DOM. Click the visible
        # login button area in the active dialog after locating the modal inputs.
        page.mouse.click(640, 654)

        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass
        page.wait_for_timeout(3000)

        keys = storage_keys(page)
        cookies = [cookie["name"] for cookie in context.cookies()]
        body_text = page.locator("body").inner_text(timeout=10000)
        final_inputs = visible_inputs(page)
        has_password = any(item["type"] == "password" for item in final_inputs)

        result.update(
            {
                "final_url": page.url,
                "title": page.title(),
                "cookies": cookies,
                **keys,
                "success": (
                    "test_auth_token" in cookies
                    and "login" in keys["localStorage"]
                    and not has_password
                ),
                "evidence_text": body_text[:500],
            }
        )
        if not result["success"]:
            result["reason"] = "Front login did not produce expected token/session."
    except Exception as exc:
        result["reason"] = str(exc)
    finally:
        result["artifacts"] = save_artifacts(page, context, "front")
        context.close()

    return result


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        results = [admin_login(browser), front_login(browser)]
        browser.close()

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project": "message reminder and important todo",
        "step": "login precheck",
        "results": results,
        "all_success": all(item["success"] for item in results),
    }
    report_path = OUT_DIR / "agent2_login_precheck_result.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
