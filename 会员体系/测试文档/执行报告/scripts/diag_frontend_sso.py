# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
import os, sys, time

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
SCREENSHOTS = r"d:\test_workspace\会员体系\测试文档\执行报告\screenshots"

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
    print("Frontend SSO Diagnostic: Bypassing login via Admin")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        
        try:
            admin_login(page)
            
            print("  Navigating to customer list...")
            page.goto("https://lying-admin.hubbuyer.com/admin/user/list", timeout=30000)
            page.wait_for_timeout(3000)
            
            page.screenshot(path=os.path.join(SCREENSHOTS, "sso_admin_list.webp"))
            
            print("  Clicking '会员中心' to trigger SSO...")
            btn = page.locator("button").filter(has_text="会员中心").first
            if btn.count() > 0:
                btn.click()
            else:
                page.locator("text=会员中心").first.click()
            
            page.wait_for_timeout(1000)
            
            print("  Clicking '确定' in popconfirm...")
            with page.expect_popup() as popup_info:
                confirm_btn = page.locator(".el-popper button").filter(has_text="确定").first
                if confirm_btn.count() == 0:
                    confirm_btn = page.locator("button").filter(has_text="确定").last
                confirm_btn.click()
            
            frontend_page = popup_info.value
            frontend_page.wait_for_load_state()
            page.wait_for_timeout(5000)
            
            print(f"  SSO successful! Frontend URL: {frontend_page.url}")
            frontend_page.screenshot(path=os.path.join(SCREENSHOTS, "sso_frontend_member_center.webp"), full_page=True)
            
            # Navigate to Pricing Page on the frontend
            print("  Attempting to navigate to pricing/fee page...")
            # We don't know the exact URL, let's look at the DOM or just try /zh/fee
            # Often there's a link to pricing. Let's just print the HTML title.
            print(f"  Frontend Page Title: {frontend_page.title()}")
            
        except Exception as e:
            print(f"Exception: {e}")
            
        browser.close()

if __name__ == "__main__":
    main()
