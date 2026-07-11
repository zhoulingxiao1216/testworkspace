"""
Layer 2: 会员等级基础库页面 DOM 探索
目的：发现页面选择器，为后续用例执行脚本提供基础
"""
from playwright.sync_api import sync_playwright
import os, sys, io, json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SCREENSHOTS = r"d:\test_workspace\会员体系\测试文档\执行报告\screenshots"
os.makedirs(SCREENSHOTS, exist_ok=True)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # --- 登录 ---
        page.goto("https://lying-admin.hubbuyer.com/login", wait_until="networkidle", timeout=20000)
        inputs = page.query_selector_all("input")
        inputs[0].fill("admin")
        inputs[1].fill("123333")
        page.query_selector("button").click()
        page.wait_for_timeout(3000)
        page.wait_for_load_state("networkidle")
        print(f"[Login] 登录成功: {page.url}")

        # --- 导航至会员等级基础库 ---
        page.goto("https://lying-admin.hubbuyer.com/b2b/member/level", wait_until="networkidle", timeout=15000)
        page.wait_for_timeout(2000)
        print(f"[Navigate] 当前页面: {page.url}")
        page.screenshot(path=os.path.join(SCREENSHOTS, "explore_member_level_full.webp"), full_page=True)

        # --- DOM 结构分析 ---
        print("\n=== 页面标题与面包屑 ===")
        breadcrumbs = page.query_selector_all(".ant-breadcrumb span, .el-breadcrumb span, nav span")
        for bc in breadcrumbs[:10]:
            print(f"  面包屑: {bc.inner_text()}")

        print("\n=== 表格/列表结构 ===")
        tables = page.query_selector_all("table")
        print(f"  发现 {len(tables)} 个 table 元素")
        for i, table in enumerate(tables[:3]):
            headers = table.query_selector_all("th")
            header_texts = [h.inner_text().strip() for h in headers]
            print(f"  Table[{i}] 列头: {header_texts}")
            rows = table.query_selector_all("tbody tr")
            print(f"  Table[{i}] 数据行数: {len(rows)}")
            # 打印前3行的内容
            for j, row in enumerate(rows[:3]):
                cells = row.query_selector_all("td")
                cell_texts = [c.inner_text().strip()[:30] for c in cells]
                print(f"    Row[{j}]: {cell_texts}")

        print("\n=== 按钮 ===")
        buttons = page.query_selector_all("button")
        for btn in buttons[:15]:
            text = btn.inner_text().strip()
            classes = btn.get_attribute("class") or ""
            disabled = btn.get_attribute("disabled")
            if text:
                print(f"  按钮: '{text}' | class={classes[:50]} | disabled={disabled}")

        print("\n=== 输入框 ===")
        all_inputs = page.query_selector_all("input, textarea, select")
        for inp in all_inputs[:15]:
            tag = inp.evaluate("el => el.tagName")
            itype = inp.get_attribute("type") or ""
            placeholder = inp.get_attribute("placeholder") or ""
            name = inp.get_attribute("name") or ""
            value = inp.input_value() if tag == "INPUT" or tag == "TEXTAREA" else ""
            print(f"  <{tag}> type={itype} name={name} placeholder={placeholder} value={value[:30]}")

        print("\n=== 对话框/模态框 ===")
        modals = page.query_selector_all(".ant-modal, .el-dialog, [role='dialog']")
        print(f"  发现 {len(modals)} 个模态框")

        print("\n=== 关键区域截图 ===")
        # 尝试点击"新增"按钮查看表单
        add_btns = page.query_selector_all("button")
        add_btn = None
        for btn in add_btns:
            text = btn.inner_text().strip()
            if "新增" in text or "添加" in text or "新建" in text or "Add" in text:
                add_btn = btn
                print(f"  找到新增按钮: '{text}'")
                break
        
        if add_btn:
            add_btn.click()
            page.wait_for_timeout(1500)
            page.screenshot(path=os.path.join(SCREENSHOTS, "explore_member_level_add_form.webp"), full_page=True)
            print("  已截取新增表单截图")
            
            # 分析弹出的表单
            print("\n=== 新增表单结构 ===")
            # 检查模态框
            modals = page.query_selector_all(".ant-modal-content, .el-dialog, [role='dialog'], .ant-drawer-content")
            print(f"  弹出框数量: {len(modals)}")
            
            form_inputs = page.query_selector_all(".ant-modal input, .ant-modal textarea, .ant-modal select, .el-dialog input, .ant-drawer input, .ant-drawer textarea")
            print(f"  表单内输入框: {len(form_inputs)}")
            for fi in form_inputs[:20]:
                tag = fi.evaluate("el => el.tagName")
                itype = fi.get_attribute("type") or ""
                placeholder = fi.get_attribute("placeholder") or ""
                label_text = fi.evaluate("""el => {
                    const label = el.closest('.ant-form-item, .el-form-item');
                    return label ? label.querySelector('label')?.innerText || '' : '';
                }""")
                print(f"    <{tag}> type={itype} placeholder='{placeholder}' label='{label_text}'")
            
            # 检查 Tab/标签切换（多语种）
            tabs = page.query_selector_all(".ant-tabs-tab, .el-tabs__item, [role='tab']")
            if tabs:
                print(f"\n  发现 {len(tabs)} 个语种Tab:")
                for tab in tabs:
                    print(f"    Tab: '{tab.inner_text().strip()}'")
            
            # 关闭弹窗
            close_btns = page.query_selector_all(".ant-modal-close, .el-dialog__close, [aria-label='Close']")
            if close_btns:
                close_btns[0].click()
                page.wait_for_timeout(500)

        # --- 导航至全球会员定价页面 ---
        print("\n\n=== 全球会员定价页面 DOM 探索 ===")
        page.goto("https://lying-admin.hubbuyer.com/b2b/member/country", wait_until="networkidle", timeout=15000)
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(SCREENSHOTS, "explore_member_country_full.webp"), full_page=True)
        
        # 国家选择器
        print("\n=== 国家/Tab ===")
        tabs = page.query_selector_all(".ant-tabs-tab, .el-tabs__item, [role='tab']")
        for tab in tabs[:10]:
            print(f"  Tab: '{tab.inner_text().strip()}'")
        
        # 左侧国家列表
        sidebar_items = page.query_selector_all(".ant-menu-item, .el-menu-item, [class*='country'], [class*='sidebar'] li")
        if sidebar_items:
            print(f"\n  侧栏菜单项: {len(sidebar_items)}")
            for item in sidebar_items[:10]:
                print(f"    '{item.inner_text().strip()[:30]}'")

        browser.close()
    
    print("\n✅ DOM 探索完成")

if __name__ == "__main__":
    main()
