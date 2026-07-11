# -*- coding: utf-8 -*-
"""
TC-MG-004 & 005
"""
from playwright.sync_api import sync_playwright
import os, sys, time

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
SCREENSHOTS = r"d:\test_workspace\会员体系\测试文档\执行报告\screenshots"

def admin_login(page):
    page.goto("https://lying-admin.hubbuyer.com/login", timeout=30000)
    page.wait_for_selector("input", timeout=10000)
    inputs = page.query_selector_all("input")
    inputs[0].fill("admin")
    inputs[1].fill("123333")
    page.query_selector("button").click()
    try: page.wait_for_url("**/admin/**", timeout=15000)
    except: pass

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        admin_login(page)
        
        ts = str(int(time.time()))
        test_level = f"AG_INV_{ts}"
        
        # 1. Create Invite Level
        page.goto("https://lying-admin.hubbuyer.com/b2b/member/level", timeout=30000)
        page.wait_for_timeout(3000)
        
        for btn in page.query_selector_all("button"):
            cls = btn.get_attribute("class") or ""
            t = btn.inner_text().strip()
            if "primary" in cls and "is-link" not in cls and len(t) >= 4 and t != "查询":
                btn.click()
                break
                
        page.wait_for_timeout(1500)
        inputs = page.query_selector_all(".el-dialog input")
        
        inputs[0].fill(test_level)
        inputs[1].fill(f"{test_level}_EN")
        inputs[2].fill(f"{test_level}_JP")
        inputs[3].fill(f"{test_level}_KR")
        
        inputs[8].click(force=True)
        page.wait_for_timeout(1000)
        page.evaluate("""() => {
            let opts = Array.from(document.querySelectorAll('.el-select-dropdown__item'));
            let inv = opts.find(el => el.innerText.includes('邀请制'));
            if(inv) inv.click();
        }""")
        page.wait_for_timeout(500)
        
        textareas = page.query_selector_all(".el-dialog textarea")
        for i in range(min(4, len(textareas))):
            textareas[i].fill(f"Desc {i}")
            
        page.evaluate("""() => {
            let btns = Array.from(document.querySelectorAll('.el-dialog button'));
            let ok = btns.find(b => b.innerText.includes('确定') || b.innerText.includes('确认') || b.innerText.includes('保存'));
            if(ok) ok.click();
        }""")
        page.wait_for_timeout(3000)
        print(f"Created level: {test_level}")

        # 2. Check Pricing Form
        page.goto("https://lying-admin.hubbuyer.com/b2b/member/country", timeout=30000)
        page.wait_for_timeout(3000)
        
        page.evaluate("""() => {
            let btns = Array.from(document.querySelectorAll('button'));
            let edit = btns.find(b => b.innerText.includes('编辑'));
            if(edit) edit.click();
        }""")
        page.wait_for_timeout(3000)
        
        # Click the tab using JS
        print("Clicking tab...")
        page.evaluate(f"""() => {{
            let tabs = Array.from(document.querySelectorAll('.level-nav-item'));
            let tab = tabs.find(el => el.innerText.includes('{test_level}'));
            if(tab) tab.click();
        }}""")
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(SCREENSHOTS, "tab_invite_level_js.webp"))
        
        text = page.inner_text(".el-main") or page.inner_text("body")
        
        if "会员价格" in text or "划线价" in text or "有效天数" in text:
            print("❌ TC-MG-004 Fail")
        else:
            print("✅ TC-MG-004 Pass")
            
        if "代采阶梯手续费" in text or "手续费" in text:
            print("✅ TC-MG-005 Pass")
        else:
            print("❌ TC-MG-005 Fail")
            
        browser.close()

if __name__ == "__main__":
    main()
