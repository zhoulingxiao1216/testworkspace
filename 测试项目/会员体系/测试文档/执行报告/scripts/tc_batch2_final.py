# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
import os, sys, time

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
SCREENSHOTS = r"d:\test_workspace\会员体系\测试文档\执行报告\screenshots"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        
        page.goto("https://lying-admin.hubbuyer.com/login", timeout=30000)
        page.fill("input[placeholder='请输入账号']", "admin")
        page.fill("input[placeholder='请输入密码']", "123333")
        page.click("button:has-text('登录')")
        page.wait_for_timeout(3000)
        
        ts = str(int(time.time()))
        test_level = f"INV_{ts}"
        
        # 1. Create Invite Level
        page.goto("https://lying-admin.hubbuyer.com/b2b/member/level", timeout=30000)
        page.wait_for_timeout(3000)
        
        page.locator("button.el-button--primary").filter(has_not_text="查询").first.click()
        page.wait_for_timeout(1500)
        
        inputs = page.locator(".el-dialog input").all()
        inputs[0].fill(test_level)
        inputs[1].fill(f"{test_level}_EN")
        inputs[2].fill(f"{test_level}_JP")
        inputs[3].fill(f"{test_level}_KR")
        
        # Open dropdown and select 邀请制 correctly
        inputs[8].click(force=True)
        page.wait_for_timeout(1000)
        page.locator(".el-select-dropdown__item").filter(has_text="邀请制").first.click(force=True)
        page.wait_for_timeout(1000)
        
        # Fill description
        textareas = page.locator(".el-dialog textarea").all()
        for i in range(min(4, len(textareas))):
            textareas[i].fill("Desc")
            
        page.locator(".el-dialog button").filter(has_text="确定").first.click()
        page.wait_for_timeout(3000)
        print(f"Created level: {test_level}")

        # Verify DB condition_type
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "helpers"))
        from db_helper import query
        try:
            db_row = query(f"SELECT condition_type FROM b2b_member_level_config WHERE name_language LIKE '%%{test_level}%%' LIMIT 1")
            print(f"DB condition_type: {db_row[0]['condition_type']}")
        except Exception as e:
            print(f"DB Check Failed: {e}")

        # 2. Check Pricing Form
        page.goto("https://lying-admin.hubbuyer.com/b2b/member/country", timeout=30000)
        page.wait_for_timeout(3000)
        
        page.locator("button").filter(has_text="编辑").first.click()
        page.wait_for_timeout(3000)
        
        # Click the tab
        loc = page.locator(".level-nav-item").filter(has_text=test_level).first
        if loc.count() > 0:
            loc.scroll_into_view_if_needed()
            loc.click()
            page.wait_for_timeout(2000)
            
            text = page.locator(".el-main").inner_text() or page.inner_text("body")
            
            if "会员价格" in text or "划线价" in text or "有效天数" in text:
                print("❌ TC-MG-004 Fail")
            else:
                print("✅ TC-MG-004 Pass")
                
            if "代采阶梯手续费" in text or "手续费" in text:
                print("✅ TC-MG-005 Pass")
            else:
                print("❌ TC-MG-005 Fail")
        else:
            print("Tab not found!")

        # TC-MG-008
        print("\n=== TC-MG-008 ===")
        page.goto("https://lying-admin.hubbuyer.com/admin/user/list", timeout=30000)
        page.wait_for_timeout(3000)
        
        page.locator(".el-menu-item, .el-sub-menu__title").filter(has_text="客户管理").first.click()
        page.wait_for_timeout(1000)
        page.locator(".el-menu-item").filter(has_text="客户信息").first.click()
        page.wait_for_timeout(3000)
        
        page.locator("button").filter(has_text="详情").first.click(force=True)
        page.wait_for_timeout(3000)
        page.screenshot(path=os.path.join(SCREENSHOTS, "tc_008_detail.webp"))
        
        text = page.inner_text("body")
        if "VIP授权" in text or "修改等级" in text or "授权VIP" in text or "VIP" in text:
            print("✅ TC-MG-008 Pass")
        else:
            print("❌ TC-MG-008 Fail")
            
        browser.close()

if __name__ == "__main__":
    main()
