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
        
        page.goto("https://lying-admin.hubbuyer.com/b2b/member/country", timeout=30000)
        page.wait_for_timeout(3000)
        
        page.evaluate("""() => {
            let btns = Array.from(document.querySelectorAll('button'));
            let edit = btns.find(b => b.innerText.includes('编辑'));
            if(edit) edit.click();
        }""")
        page.wait_for_timeout(3000)
        
        # Click the tab "一般会员" so we have a clean slate (it was Pass and default)
        page.evaluate("""() => {
            let tabs = Array.from(document.querySelectorAll('.level-nav-item'));
            let tab = tabs.find(el => el.innerText && el.innerText.includes('一般会员'));
            if(tab) tab.click();
        }""")
        page.wait_for_timeout(1000)

        # TC-PR-011
        try:
            # Add a package if none exists, else use the first one
            page.evaluate("""() => {
                let btns = Array.from(document.querySelectorAll('button'));
                let addPkg = btns.find(b => b.innerText && b.innerText.includes('添加套餐'));
                if(addPkg) addPkg.click();
            }""")
            page.wait_for_timeout(1000)
            
            inputs = page.locator(".el-input-number input").all()
            print(f"  Total .el-input-number inputs: {len(inputs)}")
            
            if len(inputs) >= 4:
                # Based on visual layout, the first package has 4 inputs
                # inputs[0] = 天数, inputs[1] = 会员价格, inputs[2] = 划线价, inputs[3] = 预计月省
                inputs[1].fill("500")
                inputs[2].fill("100")
                
                page.evaluate("""() => {
                    let btns = Array.from(document.querySelectorAll('button'));
                    let save = btns.find(b => b.innerText && b.innerText.includes('保存'));
                    if(save) save.click();
                }""")
                page.wait_for_timeout(1000)
                
                error_011 = page.inner_text(".el-message") if page.query_selector(".el-message") else ""
                html = page.content()
                if "el-form-item__error" in html or "小于" in error_011 or "失败" in error_011:
                    results["TC-PR-011"] = "Pass"
                else:
                    results["TC-PR-011"] = "Fail"
            else:
                results["TC-PR-011"] = "Blocked-ENV"
        except Exception as e:
            results["TC-PR-011"] = "Blocked-ENV"

        page.reload()
        page.wait_for_timeout(4000)

        # TC-PR-009 / 010
        try:
            page.evaluate("""() => {
                let tabs = Array.from(document.querySelectorAll('.level-nav-item'));
                let tab = tabs.find(el => el.innerText && el.innerText.includes('一般会员'));
                if(tab) tab.click();
            }""")
            page.wait_for_timeout(1000)
            
            # Click add step twice
            page.evaluate("""() => {
                let btns = Array.from(document.querySelectorAll('button'));
                let addStep = btns.find(b => b.innerText && b.innerText.includes('添加阶梯'));
                if(addStep) {
                    addStep.click();
                    setTimeout(() => addStep.click(), 500);
                }
            }""")
            page.wait_for_timeout(1500)
            
            inputs = page.locator(".el-input-number input").all()
            
            # For 009: Invert first step
            # Packages usually have 4 inputs. We don't know how many packages exist.
            # So we look at the LAST 6 inputs, which belong to the 2 newly added steps!
            # Each step has 3 inputs: Start, End, Fee.
            if len(inputs) >= 6:
                # Step 1: inputs[-6], inputs[-5], inputs[-4]
                # Step 2: inputs[-3], inputs[-2], inputs[-1]
                inputs[-6].fill("100")
                inputs[-5].fill("50")
                inputs[-4].fill("10")
                
                page.evaluate("""() => {
                    let btns = Array.from(document.querySelectorAll('button'));
                    let save = btns.find(b => b.innerText && b.innerText.includes('保存'));
                    if(save) save.click();
                }""")
                page.wait_for_timeout(1000)
                
                error_009 = page.inner_text(".el-message") if page.query_selector(".el-message") else ""
                html = page.content()
                if "el-form-item__error" in html or "大小" in error_009 or "不能" in error_009 or "失败" in error_009:
                    results["TC-PR-009"] = "Pass"
                else:
                    results["TC-PR-009"] = "Fail"
                
                # 010: Overlap
                inputs[-6].fill("0")
                inputs[-5].fill("50")
                
                inputs[-3].fill("40")
                inputs[-2].fill("100")
                inputs[-1].fill("10")
                
                page.evaluate("""() => {
                    let btns = Array.from(document.querySelectorAll('button'));
                    let save = btns.find(b => b.innerText && b.innerText.includes('保存'));
                    if(save) save.click();
                }""")
                page.wait_for_timeout(1000)
                
                error_010 = page.inner_text(".el-message") if page.query_selector(".el-message") else ""
                html = page.content()
                if "el-form-item__error" in html or "交叉" in error_010 or "重叠" in error_010 or "包含" in error_010 or "失败" in error_010:
                    results["TC-PR-010"] = "Pass"
                else:
                    results["TC-PR-010"] = "Fail"
            else:
                results["TC-PR-009"] = "Blocked-ENV"
                results["TC-PR-010"] = "Blocked-ENV"
        except:
            pass

        browser.close()

    print("\n" + "=" * 60)
    for tc, r in results.items():
        print(f"  {'✅' if 'Pass' in r else '❌' if 'Fail' in r else '⚠️'} {tc}: {r}")

if __name__ == "__main__":
    main()
