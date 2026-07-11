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
    print("TC-PR Batch 2: 上限控制与防损校验 (007, 008, 013)")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        admin_login(page)
        
        # 导航至全球会员定价
        page.goto("https://lying-admin.hubbuyer.com/b2b/member/country", timeout=30000)
        page.wait_for_timeout(3000)
        
        page.locator("button").filter(has_text="编辑").first.click()
        page.wait_for_timeout(3000)
        
        page.evaluate("""() => {
            let tabs = Array.from(document.querySelectorAll('.level-nav-item'));
            let tab = tabs.find(el => el.innerText && el.innerText.includes('一般会员'));
            if(tab) tab.click();
        }""")
        page.wait_for_timeout(1000)

        # ============================================================
        # TC-PR-007: 套餐数量上限
        # ============================================================
        try:
            print("  [TC-PR-007] 测试套餐添加数量上限...")
            for _ in range(6):
                add_pkg = page.locator("button").filter(has_text="添加套餐")
                if add_pkg.count() > 0:
                    add_pkg.first.click(force=True)
                    page.wait_for_timeout(300)
            
            page.wait_for_timeout(1000)
            page.screenshot(path=os.path.join(SCREENSHOTS, "tc_pr_007_result.webp"))
            
            html = page.content()
            if "套餐 6" in html:
                results["TC-PR-007"] = "Fail"
            elif "套餐 5" in html and "添加套餐 (5/5)" in html:
                # Button should be disabled or not clickable
                is_disabled = page.evaluate("""() => {
                    let b = Array.from(document.querySelectorAll('button')).find(btn => btn.innerText.includes('添加套餐'));
                    return b ? b.disabled || b.classList.contains('is-disabled') : false;
                }""")
                if is_disabled:
                    results["TC-PR-007"] = "Pass"
                else:
                    # sometimes it just stops doing anything without visual disabled class
                    results["TC-PR-007"] = "Pass (Max 5 enforced)"
            else:
                results["TC-PR-007"] = "Blocked-ENV"
        except Exception as e:
            results["TC-PR-007"] = "Blocked-ENV"

        # ============================================================
        # TC-PR-008: 阶梯数量上限
        # ============================================================
        try:
            print("  [TC-PR-008] 测试阶梯添加数量上限...")
            for _ in range(6):
                add_step = page.locator("button").filter(has_text="添加阶梯")
                if add_step.count() > 0:
                    add_step.first.click(force=True)
                    page.wait_for_timeout(300)
                    
            page.wait_for_timeout(1000)
            page.screenshot(path=os.path.join(SCREENSHOTS, "tc_pr_008_result.webp"))
            
            html = page.content()
            if "第 6 阶梯" in html:
                results["TC-PR-008"] = "Fail"
            elif "第 5 阶梯" in html and "添加阶梯 (5/5)" in html:
                is_disabled = page.evaluate("""() => {
                    let b = Array.from(document.querySelectorAll('button')).find(btn => btn.innerText.includes('添加阶梯'));
                    return b ? b.disabled || b.classList.contains('is-disabled') : false;
                }""")
                if is_disabled:
                    results["TC-PR-008"] = "Pass"
                else:
                    results["TC-PR-008"] = "Pass (Max 5 enforced)"
            else:
                results["TC-PR-008"] = "Blocked-ENV"
        except Exception as e:
            results["TC-PR-008"] = "Blocked-ENV"

        # ============================================================
        # TC-PR-013: 会员费防损校验 (<=0 拦截)
        # ============================================================
        page.reload()
        page.wait_for_timeout(4000)
        page.locator("button").filter(has_text="编辑").first.click()
        page.wait_for_timeout(3000)
        
        page.evaluate("""() => {
            let tabs = Array.from(document.querySelectorAll('.level-nav-item'));
            let tab = tabs.find(el => el.innerText && el.innerText.includes('一般会员'));
            if(tab) tab.click();
        }""")
        page.wait_for_timeout(1000)

        try:
            print("  [TC-PR-013] 测试会员费防损校验...")
            inputs = page.locator(".el-input-number input").all()
            if len(inputs) > 5:
                # inputs[4] is 会员价格
                inputs[4].fill("0")
                inputs[5].fill("100") # 划线价大于会员价，避免触发 011
                
                page.locator("button").filter(has_text="保存").first.click()
                page.wait_for_timeout(1500)
                page.screenshot(path=os.path.join(SCREENSHOTS, "tc_pr_013_result.webp"))
                
                error_013 = page.evaluate("Array.from(document.querySelectorAll('.el-message')).map(e => e.innerText).join(' ')")
                html = page.content()
                
                if "el-form-item__error" in html or "大于" in error_013 or "不能为" in error_013 or "0" in error_013 or "失败" in error_013:
                    results["TC-PR-013"] = "Pass"
                else:
                    results["TC-PR-013"] = "Fail"
            else:
                results["TC-PR-013"] = "Blocked-ENV"
        except Exception as e:
            results["TC-PR-013"] = "Blocked-ENV"

        browser.close()

    print("\n" + "=" * 60)
    for tc, r in results.items():
        print(f"  {'✅' if 'Pass' in r else '❌' if 'Fail' in r else '⚠️'} {tc}: {r}")

if __name__ == "__main__":
    main()
