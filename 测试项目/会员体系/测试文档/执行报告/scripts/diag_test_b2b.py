# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
import os, sys, time

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
SCREENSHOTS = r"d:\test_workspace\会员体系\测试文档\执行报告\screenshots"

def main():
    print("=" * 60)
    print("Frontend Diagnostic: test-b2b.hubbuyer.com")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        
        try:
            print("  Navigating to test-b2b frontend login...")
            page.goto("https://test-b2b.hubbuyer.com/login", timeout=30000)
            page.wait_for_timeout(3000)
            page.screenshot(path=os.path.join(SCREENSHOTS, "testb2b_login_page.webp"))
            
            # Fill credentials
            print("  Filling credentials for 369901314@qq.com (Japan)...")
            inputs = page.locator("input").all()
            if len(inputs) >= 2:
                inputs[0].fill("369901314@qq.com")
                inputs[1].fill("123456")
                
                # Click login
                page.evaluate("""() => {
                    let btns = Array.from(document.querySelectorAll('button'));
                    let login = btns.find(b => b.innerText && (b.innerText.includes('登录') || b.innerText.includes('Login')));
                    if(login) login.click();
                }""")
                page.wait_for_timeout(4000)
                
                page.screenshot(path=os.path.join(SCREENSHOTS, "testb2b_login_result.webp"))
                print("  Login attempted, screenshot saved.")
                
            else:
                print("  Could not find login inputs.")
                
        except Exception as e:
            print(f"Exception: {e}")
            
        browser.close()

if __name__ == "__main__":
    main()
