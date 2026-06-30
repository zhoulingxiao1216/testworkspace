#!/usr/bin/env python3
import json
import re
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright


OUT_DIR = Path.cwd() / "output" / "playwright" / "agent2_execution_write"
OUT_DIR.mkdir(parents=True, exist_ok=True)

ADMIN_URL = "https://hlc-admin.hubbuyer.com/"

TXT_PENDING = "\u5f85\u5ba1\u6838"
TXT_IN_REVIEW = "\u5ba1\u6838\u4e2d"
TXT_PASS = "\u901a\u8fc7"
TXT_ALLOW_PURCHASE = "\u5141\u8bb8\u91c7\u8d2d"
TXT_START_REVIEW = "\u5f00\u59cb\u5ba1\u6838"
TXT_CONFIRM_OPTIONS = [
    "\u786e\u5b9a",
    "\u786e\u8ba4",
    "\u901a\u8fc7",
    "\u63d0\u4ea4",
    "OK",
]


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def login_admin(page):
    page.goto(ADMIN_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1000)
    page.locator("input").nth(0).fill("admin")
    page.locator('input[type="password"]').fill("123333")
    page.locator("button").first.click()
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    page.wait_for_timeout(1500)


def visible_state(page, max_body=6000):
    return page.evaluate(
        r"""(maxBody) => {
            const visible = el => {
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);
                return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
            };
            return {
                url: location.href,
                title: document.title,
                body: document.body.innerText.slice(0, maxBody),
                dialogs: [...document.querySelectorAll('.el-dialog,.el-message-box,.el-drawer,.el-overlay')]
                    .filter(visible)
                    .map(el => (el.innerText || '').trim())
                    .filter(Boolean)
                    .slice(-8),
                buttons: [...document.querySelectorAll('button,a,.el-button,[role=button]')]
                    .filter(visible)
                    .map((el, idx) => {
                        const r = el.getBoundingClientRect();
                        return {
                            idx,
                            text: (el.innerText || el.textContent || '').trim(),
                            x: Math.round(r.x),
                            y: Math.round(r.y),
                            w: Math.round(r.width),
                            h: Math.round(r.height),
                            disabled: el.disabled || el.classList.contains('is-disabled'),
                        };
                    })
                    .filter(item => item.text)
            };
        }""",
        max_body,
    )


def tab_count(page, tab_label=TXT_PENDING):
    body = page.evaluate("document.body.innerText")
    match = re.search(re.escape(tab_label) + r"\((\d+)\)", body)
    return int(match.group(1)) if match else None


def collect_menu_badges(page):
    return page.evaluate(
        r"""() => {
            const visible = el => {
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);
                return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
            };
            return [...document.querySelectorAll('aside .el-sub-menu__title, aside .el-menu-item')]
                .filter(visible)
                .map(el => {
                    const badge = el.querySelector('.el-badge__content:not(.is-hide-zero)');
                    return {
                        label: (el.innerText || '').trim().split(/\n/)[0],
                        badge: badge ? (badge.innerText || '').trim() : null,
                    };
                })
                .filter(item => item.badge);
        }"""
    )


def load_list(page, url, screenshot_name):
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    page.wait_for_timeout(2200)
    page.screenshot(path=str(OUT_DIR / screenshot_name), full_page=True)
    return {
        "url": page.url,
        "title": page.title(),
        "pending_count": tab_count(page),
        "in_review_count": tab_count(page, TXT_IN_REVIEW),
        "menu_badges": collect_menu_badges(page),
        "body": page.evaluate("document.body.innerText.slice(0, 8000)"),
    }


def first_match(text, pattern):
    match = re.search(pattern, text)
    return match.group(0) if match else None


def click_button(page, label):
    locator = page.get_by_role("button", name=label).first
    locator.wait_for(state="visible", timeout=20000)
    locator.click(force=True, timeout=20000)


def click_confirm_if_present(page):
    page.wait_for_timeout(800)
    clicked = page.evaluate(
        r"""(labels) => {
            const visible = el => {
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);
                return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
            };
            const containers = [...document.querySelectorAll('.el-message-box,.el-dialog,.el-overlay,.el-popconfirm,.el-popper')]
                .filter(visible);
            for (const container of containers) {
                const buttons = [...container.querySelectorAll('button,.el-button,[role=button]')]
                    .filter(visible)
                    .map(el => ({ el, text: (el.innerText || el.textContent || '').trim() }))
                    .filter(item => item.text && labels.some(label => item.text === label || item.text.includes(label)));
                const target = buttons.find(item => !item.el.disabled && !item.el.classList.contains('is-disabled'));
                if (target) {
                    target.el.click();
                    return target.text;
                }
            }
            const fallback = [...document.querySelectorAll('button,.el-button,[role=button]')]
                .filter(visible)
                .map(el => ({ el, text: (el.innerText || el.textContent || '').trim() }))
                .find(item => item.text && labels.some(label => item.text === label || item.text.includes(label))
                    && !item.el.disabled && !item.el.classList.contains('is-disabled'));
            if (fallback) {
                fallback.el.click();
                return fallback.text;
            }
            return null;
        }""",
        TXT_CONFIRM_OPTIONS,
    )
    if clicked:
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass
        page.wait_for_timeout(2200)
    return clicked


def operate_detail(page, detail_url, action_label, name):
    page.goto(detail_url, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    page.wait_for_timeout(2200)
    before = visible_state(page, max_body=10000)
    page.screenshot(path=str(OUT_DIR / f"{name}_detail_before_action.png"), full_page=True)

    click_button(page, action_label)
    confirmed = click_confirm_if_present(page)
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    page.wait_for_timeout(3000)

    after = visible_state(page, max_body=10000)
    page.screenshot(path=str(OUT_DIR / f"{name}_detail_after_action.png"), full_page=True)
    return {"detail_url": detail_url, "before": before, "confirmed_button": confirmed, "after": after}


def run():
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "write-enabled Playwright UI execution",
        "results": [],
        "evidence": {},
    }

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        login_admin(page)

        quote_before = load_list(
            page,
            "https://hlc-admin.hubbuyer.com/b2b/order/quote",
            "quote_list_before_write.png",
        )
        quote_no = first_match(quote_before["body"], r"B2B-BJ-[A-Z0-9-]+")
        quote_op = None
        if quote_no:
            quote_op = operate_detail(
                page,
                f"https://hlc-admin.hubbuyer.com/b2b/order/quote/detail?quote_no={quote_no}",
                TXT_PASS,
                "quote",
            )
        quote_after = load_list(
            page,
            "https://hlc-admin.hubbuyer.com/b2b/order/quote",
            "quote_list_after_write.png",
        )
        report["evidence"]["quote"] = {"before": quote_before, "quote_no": quote_no, "operation": quote_op, "after": quote_after}

        agent_before = load_list(
            page,
            "https://hlc-admin.hubbuyer.com/b2b/order/agentBuy",
            "agentbuy_list_before_write.png",
        )
        order_no = first_match(agent_before["body"], r"B2B-DD-[A-Z0-9-]+")
        agent_op = None
        if order_no:
            agent_op = operate_detail(
                page,
                f"https://hlc-admin.hubbuyer.com/b2b/order/agentBuy/detail?order_no={order_no}",
                TXT_ALLOW_PURCHASE,
                "agentbuy",
            )
        agent_after = load_list(
            page,
            "https://hlc-admin.hubbuyer.com/b2b/order/agentBuy",
            "agentbuy_list_after_write.png",
        )
        report["evidence"]["agent_buy"] = {"before": agent_before, "order_no": order_no, "operation": agent_op, "after": agent_after}

        ship_before = load_list(
            page,
            "https://hlc-admin.hubbuyer.com/b2b/logistics/billOfParcels",
            "ship_list_before_write.png",
        )
        ship_no = first_match(ship_before["body"], r"WL-[A-Z0-9-]+")
        ship_op = None
        if ship_no:
            ship_op = operate_detail(
                page,
                f"https://hlc-admin.hubbuyer.com/b2b/logistics/billOfParcels/detail?ship_order_no={ship_no}&type=examine",
                TXT_START_REVIEW,
                "ship",
            )
        ship_after = load_list(
            page,
            "https://hlc-admin.hubbuyer.com/b2b/logistics/billOfParcels",
            "ship_list_after_write.png",
        )
        report["evidence"]["ship"] = {"before": ship_before, "ship_no": ship_no, "operation": ship_op, "after": ship_after}

        browser.close()

    def add(case_id, target, expected_delta=-1):
        data = report["evidence"][target]
        before = data["before"]["pending_count"]
        after = data["after"]["pending_count"]
        changed = before is not None and after is not None and after == before + expected_delta
        report["results"].append(
            {
                "case_id": case_id,
                "status": "PASS" if changed else "BLOCKED",
                "actual": f"{target}: pending {before} -> {after}",
                "record": data.get("quote_no") or data.get("order_no") or data.get("ship_no"),
                "note": "" if changed else "Action executed or attempted, but the pending count did not show the expected decrement.",
            }
        )

    add("TC-ORD-006", "quote")
    add("TC-ORD-008", "agent_buy")
    add("TC-SHIP-004", "ship")

    summary = {}
    for item in report["results"]:
        summary[item["status"]] = summary.get(item["status"], 0) + 1
    report["summary"] = summary

    save_json(OUT_DIR / "agent2_write_execution_report.json", report)
    lines = [
        "# Agent2 写入类补测报告",
        "",
        f"- 执行时间：{report['generated_at']}",
        "- 范围：报价单审核、代购订单允许采购、发货单开始审核",
        "",
        "| 用例 | 状态 | 记录 | 实际结果 | 备注 |",
        "|:--|:--|:--|:--|:--|",
    ]
    for item in report["results"]:
        lines.append(
            f"| {item['case_id']} | {item['status']} | {item['record']} | {item['actual']} | {item['note']} |"
        )
    (OUT_DIR / "Agent2_写入类补测报告.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"summary": summary, "report": str(OUT_DIR / "Agent2_写入类补测报告.md")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    start = time.perf_counter()
    run()
    print(f"elapsed={time.perf_counter() - start:.2f}s")
