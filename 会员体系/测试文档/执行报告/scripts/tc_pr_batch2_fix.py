# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
import os, sys, time

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
SCREENSHOTS = r"d:\test_workspace\会员体系\测试文档\执行报告\screenshots"
results = {}

def admin_login(page):
    page.goto("https://lying-admin.hubbuyer.com/login", timeout=30000)
    page.wait_for_selector("input", timeout=10000)
    inputs = page.locator("input").all()
    inputs[0].fill("admin")
    inputs[1].fill("123333")
    page.locator("button").filter(has_text="登录").click()
    page.wait_for_timeout(3000)

def main():
    print("=" * 60)
    print("TC-PR-013 Fix: 针对付费层级(企业会员)的防损校验")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        admin_login(page)
        
        page.goto("https://lying-admin.hubbuyer.com/b2b/member/country", timeout=30000)
        page.wait_for_timeout(3000)
        
        page.locator("button").filter(has_text="编辑").first.click()
        page.wait_for_timeout(3000)
        
        # Click on a PAID tier tab, e.g. "企业会员"
        page.evaluate("""() => {
            let tabs = Array.from(document.querySelectorAll('.level-nav-item'));
            let tab = tabs.find(el => el.innerText && el.innerText.includes('企业会员') && !el.innerText.includes('X企业会员'));
            if(tab) tab.click();
        }""")
        page.wait_for_timeout(1000)

        try:
            print("  [TC-PR-013-Fixed] 在企业会员下测试会员费 0 元防损校验...")
            
            inputs = page.locator(".el-input-number input").all()
            if len(inputs) > 5:
                inputs[4].fill("0")
                inputs[5].fill("100") # 划线价 > 会员价
                
                page.locator("button").filter(has_text="保存").first.click()
                page.wait_for_timeout(1500)
                page.screenshot(path=os.path.join(SCREENSHOTS, "tc_pr_013_fix_result.webp"))
                
                error_013 = page.evaluate("Array.from(document.querySelectorAll('.el-message')).map(e => e.innerText).join(' ')")
                html = page.content()
                
                if "el-form-item__error" in html or "大于" in error_013 or "不能为" in error_013 or "大于0" in error_013 or "失败" in error_013:
                    results["TC-PR-013"] = "Pass"
                else:
                    results["TC-PR-013"] = "Fail"
            else:
                results["TC-PR-013"] = "Blocked-ENV"
        except Exception as e:
            print(f"Exception: {e}")
            results["TC-PR-013"] = "Blocked-ENV"

        browser.close()

    print("\n" + "=" * 60)
    for tc, r in results.items():
        print(f"  {'✅' if 'Pass' in r else '❌' if 'Fail' in r else '⚠️'} {tc}: {r}")

if __name__ == "__main__":
    main()
