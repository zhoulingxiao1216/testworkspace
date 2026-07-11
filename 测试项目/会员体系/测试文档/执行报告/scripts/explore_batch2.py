import os, sys, time, json
from playwright.sync_api import sync_playwright

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
SCREENSHOTS = r"d:\test_workspace\会员体系\测试文档\执行报告\screenshots"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        
        # Login
        page.goto("https://lying-admin.hubbuyer.com/login", timeout=30000)
        page.fill("input[placeholder='请输入账号']", "admin")
        page.fill("input[placeholder='请输入密码']", "123333")
        page.click("button:has-text('登录')")
        page.wait_for_timeout(3000)
        
        # 1. 检查新增弹窗中的"成为条件"选项
        page.goto("https://lying-admin.hubbuyer.com/b2b/member/level", timeout=30000)
        page.wait_for_timeout(2000)
        
        # Click add button
        btns = page.query_selector_all("button")
        for btn in btns:
            cls = btn.get_attribute("class") or ""
            t = btn.inner_text().strip()
            if "primary" in cls and "is-link" not in cls and len(t) >= 4 and t != "查询":
                btn.click()
                break
                
        page.wait_for_timeout(1000)
        
        # 找到成为条件的下拉框并点击
        # 使用 force=True 来穿透 overlay
        inputs = page.query_selector_all(".el-dialog input")
        if len(inputs) > 8:
            print("Clicking condition dropdown...")
            inputs[8].click(force=True)
            page.wait_for_timeout(1000)
            
            # 获取所有选项
            options = page.query_selector_all(".el-select-dropdown__item")
            print(f"找到 {len(options)} 个下拉选项:")
            for opt in options:
                print(f"  - '{opt.inner_text().strip()}'")
                
        # 2. 检查 全球会员定价
        print("\n--- 全球会员定价 ---")
        page.goto("https://lying-admin.hubbuyer.com/b2b/member/country", timeout=30000)
        page.wait_for_timeout(3000)
        page.screenshot(path=os.path.join(SCREENSHOTS, "explore_pricing_tab.webp"))
        
        # Check tabs
        tabs = page.query_selector_all(".el-tabs__item")
        print(f"Tabs:")
        for t in tabs:
            print(f"  - '{t.inner_text().strip()}'")
            
        # 查找里面的输入框和表单
        labels = page.query_selector_all(".el-form-item__label")
        print("Form labels:")
        for lbl in labels:
            print(f"  - '{lbl.inner_text().strip()}'")
            
        browser.close()

if __name__ == "__main__":
    main()
