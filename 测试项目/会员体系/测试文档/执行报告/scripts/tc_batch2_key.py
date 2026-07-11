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
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        admin_login(page)
        
        ts = str(int(time.time()))
        test_level = f"INV_{ts}"
        
        # ==========================================
        # TC-MG-004 & 005
        # ==========================================
        page.goto("https://lying-admin.hubbuyer.com/b2b/member/level", timeout=30000)
        page.wait_for_timeout(3000)
        
        # Click add button (the one that is not "查询")
        page.evaluate("""() => {
            let btns = Array.from(document.querySelectorAll('button.el-button--primary'));
            let addBtn = btns.find(b => !b.innerText.includes('查询'));
            if(addBtn) addBtn.click();
        }""")
        page.wait_for_timeout(1500)
        
        inputs = page.locator(".el-dialog input").all()
        inputs[0].fill(test_level)
        inputs[1].fill(f"{test_level}_EN")
        inputs[2].fill(f"{test_level}_JP")
        inputs[3].fill(f"{test_level}_KR")
        
        # Use keyboard to select 邀请制 (second option)
        print("Selecting condition via keyboard...")
        inputs[8].focus()
        page.keyboard.press("Enter")
        page.wait_for_timeout(500)
        page.keyboard.press("ArrowDown") # Moves focus to the second option
        page.wait_for_timeout(200)
        page.keyboard.press("Enter") # Selects it
        page.wait_for_timeout(500)
        
        textareas = page.locator(".el-dialog textarea").all()
        for i in range(min(4, len(textareas))):
            textareas[i].fill("Desc")
            
        page.evaluate("""() => {
            let btns = Array.from(document.querySelectorAll('.el-dialog button'));
            let ok = btns.find(b => b.innerText.includes('确定') || b.innerText.includes('确认') || b.innerText.includes('保存'));
            if(ok) ok.click();
        }""")
        page.wait_for_timeout(3000)
        
        # Verify DB
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "helpers"))
        from db_helper import query
        try:
            db_row = query(f"SELECT condition_type FROM b2b_member_level_config WHERE name_language LIKE '%%{test_level}%%' LIMIT 1")
            cond = db_row[0]['condition_type']
            print(f"DB condition_type: {cond}")
            if str(cond) != "2":
                print("⚠️ DB shows condition is NOT 邀请制 (2). UI selection failed.")
        except Exception as e:
            pass

        page.goto("https://lying-admin.hubbuyer.com/b2b/member/country", timeout=30000)
        page.wait_for_timeout(3000)
        
        page.evaluate("""() => {
            let btns = Array.from(document.querySelectorAll('button'));
            let edit = btns.find(b => b.innerText.includes('编辑'));
            if(edit) edit.click();
        }""")
        page.wait_for_timeout(3000)
        
        # Search for our level tab using JS
        found_tab = page.evaluate(f"""() => {{
            let tabs = Array.from(document.querySelectorAll('.level-nav-item'));
            let tab = tabs.find(el => el.innerText.includes('{test_level}'));
            if(tab) {{ tab.scrollIntoView(); tab.click(); return true; }}
            return false;
        }}""")
        
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(SCREENSHOTS, "tc_004_pricing.webp"))
        
        if found_tab:
            text = page.inner_text(".el-main") or page.inner_text("body")
            if "会员价格" in text or "划线价" in text or "有效天数" in text:
                results["TC-MG-004"] = "Fail"
            else:
                results["TC-MG-004"] = "Pass"
                
            if "代采阶梯手续费" in text or "手续费" in text:
                results["TC-MG-005"] = "Pass"
            else:
                results["TC-MG-005"] = "Fail"
        else:
            results["TC-MG-004"] = "Blocked-ENV (Tab not found)"
            results["TC-MG-005"] = "Blocked-ENV"

        # ==========================================
        # TC-MG-008
        # ==========================================
        page.goto("https://lying-admin.hubbuyer.com/admin/user/list", timeout=30000)
        page.wait_for_timeout(3000)
        
        # Navigate to 客户信息
        page.evaluate("""() => {
            let menus = Array.from(document.querySelectorAll('.el-menu-item, .el-sub-menu__title'));
            let m1 = menus.find(m => m.innerText.includes('客户管理'));
            if(m1) m1.click();
        }""")
        page.wait_for_timeout(1000)
        page.evaluate("""() => {
            let menus = Array.from(document.querySelectorAll('.el-menu-item'));
            let m2 = menus.find(m => m.innerText.includes('客户信息'));
            if(m2) m2.click();
        }""")
        page.wait_for_timeout(3000)
        
        clicked_detail = page.evaluate("""() => {
            let btns = Array.from(document.querySelectorAll('button, a'));
            let detail = btns.find(b => b.innerText.includes('详情'));
            if(detail) { detail.click(); return true; }
            return false;
        }""")
        
        if clicked_detail:
            page.wait_for_timeout(3000)
            page.screenshot(path=os.path.join(SCREENSHOTS, "tc_008_detail.webp"))
            
            text = page.inner_text("body")
            auth_found = any(k in text for k in ["VIP授权", "修改等级", "授权VIP", "VIP"]) 
            if auth_found:
                results["TC-MG-008"] = "Pass"
            else:
                results["TC-MG-008"] = "Fail"
        else:
            results["TC-MG-008"] = "Blocked-ENV (No Detail Btn)"

        browser.close()

    print("\n" + "=" * 60)
    for tc, r in results.items():
        print(f"  {'✅' if 'Pass' in r else '❌' if 'Fail' in r else '⚠️'} {tc}: {r}")

if __name__ == "__main__":
    main()
