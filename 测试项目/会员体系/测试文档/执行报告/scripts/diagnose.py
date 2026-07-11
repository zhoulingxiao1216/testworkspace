import os, sys, time, json
from playwright.sync_api import sync_playwright

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        
        # Login
        page.goto("https://lying-admin.hubbuyer.com/login", timeout=30000)
        page.wait_for_selector("input", timeout=10000)
        inputs = page.query_selector_all("input")
        inputs[0].fill("admin")
        inputs[1].fill("123333")
        page.query_selector("button").click()
        try:
            page.wait_for_url("**/admin/**", timeout=15000)
        except:
            pass
        page.wait_for_timeout(3000)
        
        print(f"Current URL: {page.url}")
        
        # Check all menu items
        menu_items = page.query_selector_all("li, .el-menu-item, a")
        print("Menu items:")
        for item in menu_items:
            text = item.inner_text().strip() if item.inner_text() else ""
            if "客户信息" in text or "定价" in text:
                html = item.evaluate("el => el.outerHTML")
                print(f"  - Text: {text}")
                print(f"    HTML: {html[:200]}")
                
        # For TC-MG-004
        page.goto("https://lying-admin.hubbuyer.com/b2b/member/country", timeout=30000)
        page.wait_for_timeout(3000)
        
        btns = page.query_selector_all("button")
        for b in btns:
            if "编辑" in (b.inner_text() or ""):
                b.click()
                break
        page.wait_for_timeout(3000)
        
        print("\nPricing page DOM (Tabs):")
        tabs = page.query_selector_all(".el-tabs__item, .el-menu-item, [class*='item']")
        for t in tabs:
            txt = t.inner_text().strip() if t.inner_text() else ""
            if "AG_" in txt or "企业" in txt or "一般" in txt:
                print(f"  - Tab: {txt}")
                html = t.evaluate("el => el.outerHTML")
                print(f"    HTML: {html[:200]}")

        browser.close()

if __name__ == "__main__":
    main()
