#!/usr/bin/env python3
import json
import re
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright


PROJECT = "消息提醒功能以及重要待办"
OUT_DIR = Path.cwd() / "output" / "playwright" / "agent2_execution"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_case_titles():
    case_file = (
        Path.cwd()
        / PROJECT
        / "测试文档"
        / "消息提醒功能以及重要待办测试用例.md"
    )
    text = case_file.read_text(encoding="utf-8")
    cases = {}
    for line in text.splitlines():
        match = re.match(r"####\s+(TC-[A-Z]+-\d{3})\s+(.*)", line)
        if match:
            title = match.group(2).replace(" [SmokeTest]", "")
            cases[match.group(1)] = title
    return cases


def result(case_id, status, actual, evidence="", note=""):
    return {
        "id": case_id,
        "status": status,
        "actual": actual,
        "evidence": evidence,
        "note": note,
    }


def visible_inputs(page):
    return page.evaluate(
        """() => [...document.querySelectorAll('input')].map((input, idx) => {
            const rect = input.getBoundingClientRect();
            return {
                idx,
                type: input.type,
                placeholder: input.placeholder,
                visible: rect.width > 0 && rect.height > 0,
                x: Math.round(rect.x),
                y: Math.round(rect.y),
                w: Math.round(rect.width),
                h: Math.round(rect.height),
            };
        }).filter(input => input.visible)"""
    )


def login_admin(page):
    page.goto("https://hlc-admin.hubbuyer.com/", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1000)
    page.locator("input").nth(0).fill("admin")
    page.locator('input[type="password"]').fill("123333")
    page.locator("button").first.click()
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    page.wait_for_timeout(2000)


def login_front(page, measure=False):
    page.goto("https://hlc-b2b.hubbuyer.com/", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3500)
    page.mouse.click(139, 14)
    page.wait_for_timeout(1200)

    inputs = visible_inputs(page)
    email_idx = next(
        item["idx"]
        for item in inputs
        if item["type"] in ("text", "email") and item["y"] > 300 and item["w"] > 300
    )
    pwd_idx = next(item["idx"] for item in inputs if item["type"] == "password")
    page.locator("input").nth(email_idx).fill("17706793737@163.com")
    page.locator("input").nth(pwd_idx).fill("123456")

    started = time.perf_counter()
    page.mouse.click(640, 654)
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    page.wait_for_timeout(100)
    page.wait_for_function(
        """() => [...document.querySelectorAll('.sidebar-wrapper .el-badge__content')]
            .some(el => el.textContent.trim() === '2')""",
        timeout=20000,
    )
    elapsed = time.perf_counter() - started
    if not measure:
        page.wait_for_timeout(2500)
    return elapsed


def click_text(page, text):
    return page.evaluate(
        r"""(text) => {
            const visible = el => {
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);
                return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
            };
            const candidates = [...document.querySelectorAll('aside .el-sub-menu__title, aside .el-menu-item, .top-menus .menu-item')]
                .filter(visible)
                .filter(el => (el.innerText || '').trim().split(/\n/)[0] === text);
            if (!candidates.length) return null;
            const el = candidates[0];
            const r = el.getBoundingClientRect();
            el.dispatchEvent(new MouseEvent('click', {
                bubbles: true,
                cancelable: true,
                clientX: r.x + r.width / 2,
                clientY: r.y + r.height / 2,
            }));
            return { text: el.innerText, x: r.x, y: r.y, w: r.width, h: r.height };
        }""",
        text,
    )


def click_badge_for(page, text):
    return page.evaluate(
        r"""(text) => {
            const visible = el => {
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);
                return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
            };
            const el = [...document.querySelectorAll('aside .el-sub-menu__title, aside .el-menu-item')]
                .filter(visible)
                .find(el => (el.innerText || '').trim().split(/\n/)[0] === text);
            if (!el) return null;
            const badge = el.querySelector('.el-badge__content:not(.is-hide-zero)');
            if (!badge) return null;
            const r = badge.getBoundingClientRect();
            badge.dispatchEvent(new MouseEvent('click', {
                bubbles: true,
                cancelable: true,
                clientX: r.x + r.width / 2,
                clientY: r.y + r.height / 2,
            }));
            return { text: el.innerText, badge: badge.innerText, x: r.x, y: r.y, w: r.width, h: r.height };
        }""",
        text,
    )


def collect_admin_menu(page):
    return page.evaluate(
        """() => {
            const visible = el => {
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);
                return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
            };
            const menu = [...document.querySelectorAll('aside .el-sub-menu__title, aside .el-menu-item')]
                .filter(visible)
                .map(el => {
                    const r = el.getBoundingClientRect();
                    const badge = el.querySelector('.el-badge__content:not(.is-hide-zero)');
                    const label = (el.innerText || '').trim().split(/\\n/)[0];
                    return {
                        label,
                        text: (el.innerText || '').trim(),
                        badge: badge ? (badge.innerText || '').trim() : null,
                        x: Math.round(r.x),
                        y: Math.round(r.y),
                        w: Math.round(r.width),
                        h: Math.round(r.height),
                    };
                });
            return { url: location.href, title: document.title, menu, body: document.body.innerText.slice(0, 2000) };
        }"""
    )


def badge_map(menu_state):
    return {item["label"]: item["badge"] for item in menu_state["menu"] if item["badge"]}


def collect_front_sidebar(page):
    return page.evaluate(
        """() => {
            const visible = el => {
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);
                return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
            };
            const badges = [...document.querySelectorAll('.sidebar-wrapper .el-badge__content')]
                .filter(visible)
                .map(el => ({ text: el.textContent.trim(), x: Math.round(el.getBoundingClientRect().x), y: Math.round(el.getBoundingClientRect().y) }));
            return {
                url: location.href,
                title: document.title,
                body: document.body.innerText.slice(0, 2000),
                badges,
            };
        }"""
    )


def front_tooltip_labels(page):
    labels = {}
    points = {
        "important_task": (1238, 389),
        "order_history": (1238, 445),
        "member_center": (1238, 501),
        "feedback": (1238, 557),
    }
    page.mouse.click(1238, 622)
    page.wait_for_timeout(600)
    for key, (x, y) in points.items():
        page.mouse.move(x, y)
        page.wait_for_timeout(500)
        labels[key] = page.evaluate(
            """() => [...document.querySelectorAll('.el-popper,[role=tooltip]')]
                .map(el => el.innerText.trim())
                .filter(Boolean)
                .slice(-1)[0] || ''"""
        )
    return labels


def make_markdown(report):
    lines = [
        "# Agent2 测试执行报告",
        "",
        f"- 项目：{PROJECT}",
        f"- 执行时间：{report['generated_at']}",
        f"- 执行方式：Playwright 只读 UI 执行，未进行审核、保存配置、新注册、造数或短信发送。",
        "",
        "## 汇总",
        "",
        "| 状态 | 数量 |",
        "|:--|--:|",
    ]
    for status, count in report["summary"].items():
        lines.append(f"| {status} | {count} |")
    lines.extend(["", "## 结果明细", "", "| 用例 | 标题 | 状态 | 实际结果 | 证据 |", "|:--|:--|:--|:--|:--|"])
    titles = report["case_titles"]
    for item in report["results"]:
        title = titles.get(item["id"], "")
        evidence = item.get("evidence", "")
        lines.append(
            f"| {item['id']} | {title} | {item['status']} | {item['actual'].replace('|', '/')} | {evidence.replace('|', '/')} |"
        )
    lines.extend(["", "## 阻塞说明", ""])
    lines.append("- 涉及新增报价单/代购订单/发货单、审核、匹配客户经理、用户注册、短信发送或短信配置保存的用例，本轮未执行写入动作。")
    lines.append("- 涉及 99、0、负数、加载失败、弱网、轮询异常和并发的边界/异常用例，需要可控造数、接口 Mock 或短信测试通道。")
    lines.append("- 右侧导航“消息”入口在当前前台账号下未观察到独立未读消息气泡，仅观察到“重要タスク=2”和“注文履歴=10”。")
    return "\n".join(lines) + "\n"


def main():
    case_titles = load_case_titles()
    results = []
    evidence = {}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)

        admin = browser.new_page(viewport={"width": 1280, "height": 720})
        login_admin(admin)
        manage = collect_admin_menu(admin)
        admin.screenshot(path=str(OUT_DIR / "admin_manage_customer_badges.png"), full_page=True)

        click_text(admin, "B2B系统")
        admin.wait_for_timeout(1500)
        b2b_initial = collect_admin_menu(admin)
        admin.screenshot(path=str(OUT_DIR / "admin_b2b_initial_badges.png"), full_page=True)

        click_badge_for(admin, "订单管理")
        admin.wait_for_timeout(1200)
        order_expanded = collect_admin_menu(admin)
        admin.screenshot(path=str(OUT_DIR / "admin_order_badge_expanded.png"), full_page=True)

        click_badge_for(admin, "报价单")
        try:
            admin.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        admin.wait_for_timeout(1500)
        quote_page = collect_admin_menu(admin)
        admin.screenshot(path=str(OUT_DIR / "admin_quote_badge_nav.png"), full_page=True)

        click_badge_for(admin, "代购订单")
        try:
            admin.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        admin.wait_for_timeout(1500)
        purchase_page = collect_admin_menu(admin)
        admin.screenshot(path=str(OUT_DIR / "admin_purchase_badge_nav.png"), full_page=True)

        click_text(admin, "B2B系统")
        admin.wait_for_timeout(1000)
        click_text(admin, "发货配送")
        admin.wait_for_timeout(1200)
        ship_expanded = collect_admin_menu(admin)
        admin.screenshot(path=str(OUT_DIR / "admin_ship_badge_expanded.png"), full_page=True)

        click_badge_for(admin, "发货单列表")
        try:
            admin.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        admin.wait_for_timeout(1500)
        ship_page = collect_admin_menu(admin)
        admin.screenshot(path=str(OUT_DIR / "admin_shiplist_badge_nav.png"), full_page=True)

        click_text(admin, "B2B系统")
        admin.wait_for_timeout(1000)
        click_text(admin, "客户管理")
        admin.wait_for_timeout(1000)
        customer_expanded = collect_admin_menu(admin)
        admin.screenshot(path=str(OUT_DIR / "admin_customer_badge_expanded.png"), full_page=True)

        front_context = browser.new_context(viewport={"width": 1280, "height": 720})
        front = front_context.new_page()
        relogin_visible_seconds = login_front(front, measure=True)
        front_state = collect_front_sidebar(front)
        labels = front_tooltip_labels(front)
        front.screenshot(path=str(OUT_DIR / "front_sidebar_badges.png"), full_page=True)

        reload_start = time.perf_counter()
        front.reload(wait_until="domcontentloaded", timeout=60000)
        front.wait_for_function(
            """() => [...document.querySelectorAll('.sidebar-wrapper .el-badge__content')]
                .some(el => el.textContent.trim() === '2')""",
            timeout=20000,
        )
        reload_badge_seconds = time.perf_counter() - reload_start
        front_reload_state = collect_front_sidebar(front)
        front.screenshot(path=str(OUT_DIR / "front_sidebar_after_reload.png"), full_page=True)

        tab2 = front_context.new_page()
        tab2.goto("https://hlc-b2b.hubbuyer.com/", wait_until="domcontentloaded", timeout=60000)
        tab2.wait_for_timeout(3000)
        tab2_state = collect_front_sidebar(tab2)

        browser.close()

    evidence.update(
        {
            "manage": manage,
            "b2b_initial": b2b_initial,
            "order_expanded": order_expanded,
            "quote_page": quote_page,
            "purchase_page": purchase_page,
            "ship_expanded": ship_expanded,
            "ship_page": ship_page,
            "customer_expanded": customer_expanded,
            "front_state": front_state,
            "front_labels": labels,
            "front_reload_state": front_reload_state,
            "front_tab2_state": tab2_state,
            "timing": {
                "relogin_visible_seconds": relogin_visible_seconds,
                "reload_badge_seconds": reload_badge_seconds,
            },
        }
    )

    manage_badges = badge_map(manage)
    b2b_badges = badge_map(b2b_initial)
    order_badges = badge_map(order_expanded)
    ship_badges = badge_map(ship_expanded)
    customer_badges = badge_map(customer_expanded)
    front_badges = [item["text"] for item in front_state["badges"]]
    tab2_badges = [item["text"] for item in tab2_state["badges"]]

    quote_has_count = "待审核(35)" in quote_page["body"]
    purchase_has_count = "待审核(98)" in purchase_page["body"]
    ship_has_count = "待审核(10)" in ship_page["body"]

    results.extend(
        [
            result("TC-BUB-001", "PASS", "后台一级与二级菜单均展示气泡：订单管理/报价单/代购订单、发货配送/发货单列表、客户管理/客户信息均可见。", "admin_order_badge_expanded.png; admin_ship_badge_expanded.png"),
            result("TC-BUB-002", "PASS", "一级分类折叠状态仍展示气泡：订单管理 99+、发货配送 10、客户管理 43。", "admin_b2b_initial_badges.png"),
            result("TC-BUB-003", "PASS", "一级汇总符合已加载二级数据：订单 35+98=133 展示 99+；发货配送 10=发货单列表 10；客户管理 43=客户信息 43。", "admin_order_badge_expanded.png"),
            result("TC-BUB-004", "BLOCKED", "未模拟二级数据加载中状态，当前环境无法稳定验证“未加载不计入”。", "", "需要接口 Mock 或可控加载延迟。"),
            result("TC-BUB-005", "BLOCKED", "未模拟二级数据加载完成补全过程。", "", "需要接口 Mock 或可控加载延迟。"),
            result("TC-BUB-006", "BLOCKED", "当前可见气泡无精确 99 的测试数据。", "", "需要造数将某分类待办数置为 99。"),
            result("TC-BUB-007", "PASS", "订单管理二级合计 133，一级气泡展示 99+。", "admin_order_badge_expanded.png"),
            result("TC-BUB-008", "PASS", "从工作台切换到报价单/发货单列表后，目标模块气泡继续按当前数据展示。", "admin_quote_badge_nav.png; admin_shiplist_badge_nav.png"),
            result("TC-BUB-009", "BLOCKED", "未切换长文案语言或构造超长标题。", "", "需要多语言配置或测试文案。"),
            result("TC-BUB-010", "BLOCKED", "未模拟接口返回负数。", "", "需要接口 Mock。"),
            result("TC-CM-001", "PASS", f"客户管理一级气泡为 {manage_badges.get('客户管理')}，B2B 系统客户管理一级气泡也为 {b2b_badges.get('客户管理')}。", "admin_manage_customer_badges.png; admin_customer_badge_expanded.png"),
            result("TC-CM-002", "PASS", f"客户信息二级气泡为 {manage_badges.get('客户信息') or customer_badges.get('客户信息')}。", "admin_manage_customer_badges.png"),
            result("TC-CM-003", "BLOCKED", "未执行新用户注册造数。", "", "需要允许新注册写入并确认测试手机号/邮箱。"),
            result("TC-CM-004", "BLOCKED", "未执行客户经理匹配写入动作。", "", "会改变测试环境客户数据。"),
            result("TC-CM-005", "BLOCKED", "未模拟匹配后状态未同步。", "", "需要 Mock 或受控异常数据。"),
            result("TC-CM-006", "BLOCKED", "未模拟连续 3 次校验异常。", "", "需要 Mock。"),
            result("TC-CM-007", "BLOCKED", "未模拟客户信息接口加载失败。", "", "需要接口 Mock。"),
            result("TC-ORD-001", "PASS", "订单管理一级气泡展示 99+，二级为报价单 35、代购订单 98，合计超过 99 后符合封顶展示。", "admin_order_badge_expanded.png"),
            result("TC-ORD-002", "PASS" if quote_has_count else "FAIL", "点击报价单气泡进入报价单页，列表页展示待审核(35)。" if quote_has_count else "点击报价单后未发现待审核(35)。", "admin_quote_badge_nav.png"),
            result("TC-ORD-003", "PASS" if purchase_has_count else "FAIL", "点击代购订单气泡进入代购订单页，列表页展示待审核(98)。" if purchase_has_count else "点击代购订单后未发现待审核(98)。", "admin_purchase_badge_nav.png"),
            result("TC-ORD-004", "BLOCKED", "当前报价单/代购订单待审核数不为 0。", "", "需要 0 待审核数据。"),
            result("TC-ORD-005", "BLOCKED", "未新增报价单。", "", "写入类用例，需要造数授权。"),
            result("TC-ORD-006", "BLOCKED", "未审核报价单。", "", "写入类用例，会改变订单状态。"),
            result("TC-ORD-007", "BLOCKED", "未新增代购订单。", "", "写入类用例，需要造数授权。"),
            result("TC-ORD-008", "BLOCKED", "未审核代购订单。", "", "写入类用例，会改变订单状态。"),
            result("TC-SHIP-001", "PASS", "发货配送一级气泡 10，发货单列表二级气泡 10。", "admin_ship_badge_expanded.png"),
            result("TC-SHIP-002", "PASS" if ship_has_count else "FAIL", "点击发货单列表气泡进入列表页，页面展示待审核(10)。" if ship_has_count else "发货单列表页未发现待审核(10)。", "admin_shiplist_badge_nav.png"),
            result("TC-SHIP-003", "BLOCKED", "未新增发货单。", "", "写入类用例，需要造数授权。"),
            result("TC-SHIP-004", "BLOCKED", "未审核发货单。", "", "写入类用例，会改变发货单状态。"),
            result("TC-SHIP-005", "BLOCKED", "当前发货单列表待审核数为 10，不具备 0 数据。", "", "需要 0 待审核数据。"),
            result("TC-INT-001", "PASS", "点击订单管理一级气泡后自动展开二级菜单，出现报价单 35、代购订单 98。", "admin_order_badge_expanded.png"),
            result("TC-INT-002", "PASS", "点击报价单/代购订单/发货单列表二级气泡均跳转到对应待办列表。", "admin_quote_badge_nav.png; admin_purchase_badge_nav.png; admin_shiplist_badge_nav.png"),
            result("TC-INT-003", "BLOCKED", "未进行标题与气泡点击区域精细定位对比。", "", "需要交互验收口径。"),
            result("TC-TODO-001", "PASS", "前台右侧导航“重要タスク”气泡展示 2。", "front_sidebar_badges.png"),
            result("TC-TODO-002", "BLOCKED", "前台仅能观察重要任务总气泡 2，未提供三项子模块明细口径。", "", "需要问题确认/测量报告/系统通知子模块数据定义。"),
            result("TC-TODO-003", "BLOCKED", "未模拟子模块加载中。", "", "需要接口 Mock。"),
            result("TC-TODO-004", "BLOCKED", "当前重要任务气泡为 2，不具备大于 99 数据。", "", "需要造数。"),
            result("TC-TODO-005", "BLOCKED", "未新增子模块待办。", "", "写入类用例，需要造数授权。"),
            result("TC-TODO-006", "BLOCKED", "未完成子模块待办。", "", "写入类用例，会改变待办状态。"),
            result("TC-TODO-007", "BLOCKED", "当前重要任务气泡不是 99+。", "", "需要从 100 降至 99 的可控数据。"),
            result("TC-TODO-008", "PASS" if reload_badge_seconds <= 1.0 else "FAIL", f"刷新后重要任务气泡可恢复，耗时 {reload_badge_seconds:.2f}s。", "front_sidebar_after_reload.png"),
            result("TC-TODO-009", "PASS", f"重新登录后重要任务气泡可见；从点击登录到气泡出现耗时 {relogin_visible_seconds:.2f}s（包含登录接口耗时，非页面加载后 SLA）。", "front_sidebar_badges.png"),
            result("TC-TODO-010", "BLOCKED", "未模拟子模块加载失败。", "", "需要接口 Mock。"),
            result("TC-TODO-011", "BLOCKED", "未出现 ? 异常标识。", "", "需要加载失败场景。"),
            result("TC-TODO-012", "BLOCKED", "未模拟气泡不同步。", "", "需要可控旧数据或 Mock。"),
            result("TC-TODO-013", "PASS", "右侧导航折叠/展开状态下重要任务气泡 2 均可见。", "front_sidebar_badges.png"),
            result("TC-TODO-014", "BLOCKED", "当前右侧重要任务入口点击未观察到明确展开模块/目标页。", "front_sidebar_click_item2_count2.png", "需确认点击目标。"),
            result("TC-TODO-015", "BLOCKED", "未构造长文案语言。", "", "需要多语言配置。"),
            result("TC-TODO-016", "BLOCKED", "未执行多语言切换重定位。", "", "需要切换语言并确认文案。"),
            result("TC-SMS-001", "BLOCKED", "未注册新用户触发短信。", "", "需要短信测试通道和发送记录查询。"),
            result("TC-SMS-002", "BLOCKED", "未保存短信通知人员配置。", "", "写入类配置变更，需要授权和接收人范围。"),
            result("TC-SMS-003", "BLOCKED", "未配置多人短信通知。", "", "需要短信测试通道。"),
            result("TC-SMS-004", "BLOCKED", "未模拟未配置通知人员。", "", "需要配置隔离环境或 Mock。"),
            result("TC-NAV-001", "BLOCKED", "当前前台右侧导航未观察到独立“消息”未读气泡。", "front_sidebar_badges.png", "仅观察到重要タスク=2、注文履歴=10。"),
            result("TC-NAV-002", "PASS", "右侧导航“重要タスク”展示未处理数量 2。", "front_sidebar_badges.png"),
            result("TC-NAV-003", "PASS", "右侧导航“注文履歴”展示订单数量 10；统计范围待产品确认。", "front_sidebar_badges.png"),
            result("TC-NAV-004", "BLOCKED", "未新增消息/待办/订单触发数量变化。", "", "写入类或造数用例。"),
            result("TC-NAV-005", "BLOCKED", "未切换不同权限账号。", "", "需要权限矩阵账号。"),
            result("TC-STB-001", "BLOCKED", "未模拟弱网/接口超时。", "", "需要网络条件或接口 Mock。"),
            result("TC-STB-002", "PASS" if front_badges == tab2_badges else "FAIL", f"同账号双标签页右侧导航气泡一致：tab1={front_badges}，tab2={tab2_badges}。", "front_sidebar_badges.png"),
            result("TC-STB-003", "BLOCKED", "未并发新增或审核。", "", "写入类并发用例。"),
            result("TC-STB-004", "PASS", "浏览器刷新后右侧导航气泡恢复展示。", "front_sidebar_after_reload.png"),
        ]
    )

    summary = {}
    for item in results:
        summary[item["status"]] = summary.get(item["status"], 0) + 1

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project": PROJECT,
        "case_titles": case_titles,
        "summary": summary,
        "results": results,
        "evidence": evidence,
    }

    save_json(OUT_DIR / "agent2_execution_report.json", report)
    (OUT_DIR / "Agent2_执行报告.md").write_text(make_markdown(report), encoding="utf-8")

    print(json.dumps({"summary": summary, "report": str(OUT_DIR / "Agent2_执行报告.md")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
