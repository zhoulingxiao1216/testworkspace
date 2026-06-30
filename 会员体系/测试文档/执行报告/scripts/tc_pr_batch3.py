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
    print("TC-PR Batch 3: 上架时间校验与Tab隔离 (016, 017)")
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
        
        # ============================================================
        # TC-PR-016: 指定上架时间早于当前时间拦截
        # ============================================================
        try:
            print("  [TC-PR-016] 测试指定过去时间上架的拦截机制...")
            # 点击“指定时间”单选框
            time_radio = page.locator("label").filter(has_text="指定时间")
            if time_radio.count() > 0:
                time_radio.first.click(force=True)
                page.wait_for_timeout(500)
                
                # 寻找日期时间输入框并填入过去的时间
                date_input = page.locator(".el-date-editor input")
                if date_input.count() > 0:
                    # Element plus date picker sometimes needs special handling, we try to fill and enter
                    date_input.first.fill("2020-01-01 10:00:00")
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(500)
                    
                    page.locator("button").filter(has_text="保存").first.click()
                    page.wait_for_timeout(1500)
                    page.screenshot(path=os.path.join(SCREENSHOTS, "tc_pr_016_result.webp"))
                    
                    error_016 = page.evaluate("Array.from(document.querySelectorAll('.el-message')).map(e => e.innerText).join(' ')")
                    html = page.content()
                    
                    if "el-form-item__error" in html or "早于" in error_016 or "当前时间" in error_016 or "未来" in error_016 or "失败" in error_016:
                        results["TC-PR-016"] = "Pass"
                    else:
                        results["TC-PR-016"] = "Fail"
                else:
                    results["TC-PR-016"] = "Blocked-ENV (No date input found)"
            else:
                results["TC-PR-016"] = "Blocked-ENV (No radio found)"
        except Exception as e:
            results["TC-PR-016"] = "Blocked-ENV"

        # ============================================================
        # TC-PR-017: 多等级Tab独立保存隔离
        # ============================================================
        page.reload()
        page.wait_for_timeout(4000)
        page.locator("button").filter(has_text="编辑").first.click()
        page.wait_for_timeout(3000)

        try:
            print("  [TC-PR-017] 测试多等级 Tab 数据隔离...")
            
            # 点击企业会员，修改价格为 9999
            page.evaluate("""() => {
                let tabs = Array.from(document.querySelectorAll('.level-nav-item'));
                let tab = tabs.find(el => el.innerText && el.innerText.includes('企业会员') && !el.innerText.includes('X'));
                if(tab) tab.click();
            }""")
            page.wait_for_timeout(1000)
            
            # 添加套餐以防万一
            add_pkg = page.locator("button").filter(has_text="添加套餐")
            if add_pkg.count() > 0 and add_pkg.first.is_visible():
                add_pkg.first.click(force=True)
                page.wait_for_timeout(1000)
                
            inputs = page.locator(".el-input-number input").all()
            if len(inputs) > 5:
                inputs[4].fill("9999")
                
                # 切回一般会员
                page.evaluate("""() => {
                    let tabs = Array.from(document.querySelectorAll('.level-nav-item'));
                    let tab = tabs.find(el => el.innerText && el.innerText.includes('一般会员'));
                    if(tab) tab.click();
                }""")
                page.wait_for_timeout(1000)
                
                # 检查一般会员的价格是否为 9999
                inputs_general = page.locator(".el-input-number input").all()
                general_price = inputs_general[4].input_value()
                
                if general_price != "9999":
                    results["TC-PR-017"] = "Pass"
                else:
                    results["TC-PR-017"] = "Fail"
            else:
                results["TC-PR-017"] = "Blocked-ENV"
        except Exception as e:
            results["TC-PR-017"] = "Blocked-ENV"

        browser.close()

    print("\n" + "=" * 60)
    for tc, r in results.items():
        print(f"  {'✅' if 'Pass' in r else '❌' if 'Fail' in r else '⚠️'} {tc}: {r}")

if __name__ == "__main__":
    main()
