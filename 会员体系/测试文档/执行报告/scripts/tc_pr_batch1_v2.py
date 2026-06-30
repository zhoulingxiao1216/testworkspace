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
        
        page.locator("button").filter(has_text="编辑").first.click()
        page.wait_for_timeout(3000)
        
        # TC-PR-011
        try:
            # 确保至少有一个套餐
            add_pkg = page.locator("button").filter(has_text="添加套餐")
            if add_pkg.count() > 0 and add_pkg.first.is_visible():
                add_pkg.first.click(force=True)
                page.wait_for_timeout(1000)
            
            inputs = page.locator(".el-input-number input").all()
            print(f"  Total .el-input-number inputs: {len(inputs)}")
            
            # 根据分析，前几个 input 分别是：
            # 0: 国家排序
            # 1: 等级排序
            # 2: 起购金额
            # 3: 套餐 1 天数
            # 4: 套餐 1 会员价格
            # 5: 套餐 1 划线价
            # 6: 套餐 1 预计月省
            if len(inputs) > 5:
                inputs[4].fill("500")
                inputs[5].fill("100")
                
                page.locator("button").filter(has_text="保存").first.click()
                page.wait_for_timeout(1500)
                page.screenshot(path=os.path.join(SCREENSHOTS, "tc_pr_011_result.webp"))
                
                error_011 = page.evaluate("Array.from(document.querySelectorAll('.el-message')).map(e => e.innerText).join(' ')")
                html = page.content()
                if "el-form-item__error" in html or "小于" in error_011 or "大于" in error_011 or "失败" in error_011:
                    results["TC-PR-011"] = "Pass"
                else:
                    results["TC-PR-011"] = "Fail"
            else:
                results["TC-PR-011"] = "Blocked-ENV (Not enough inputs)"
        except Exception as e:
            print(f"Error in TC-PR-011: {e}")
            results["TC-PR-011"] = "Blocked-ENV"

        page.reload()
        page.wait_for_timeout(4000)
        
        # 重新点击编辑按钮进入详情页
        page.locator("button").filter(has_text="编辑").first.click()
        page.wait_for_timeout(3000)

        # TC-PR-009 / 010
        try:
            add_step = page.locator("button").filter(has_text="添加阶梯")
            if add_step.count() > 0:
                add_step.first.click(force=True)
                page.wait_for_timeout(500)
                add_step.first.click(force=True)
                page.wait_for_timeout(1000)
            
            inputs = page.locator(".el-input-number input").all()
            print(f"  Inputs after adding steps: {len(inputs)}")
            
            if len(inputs) >= 6:
                # 第一行（倒挂）：100 ~ 50
                inputs[-6].fill("100")
                inputs[-5].fill("50")
                inputs[-4].fill("10")
                
                page.locator("button").filter(has_text="保存").first.click()
                page.wait_for_timeout(1000)
                page.screenshot(path=os.path.join(SCREENSHOTS, "tc_pr_009_result.webp"))
                
                error_009 = page.evaluate("Array.from(document.querySelectorAll('.el-message')).map(e => e.innerText).join(' ')")
                html = page.content()
                if "el-form-item__error" in html or "大小" in error_009 or "不能" in error_009 or "大于" in error_009 or "失败" in error_009:
                    results["TC-PR-009"] = "Pass"
                else:
                    results["TC-PR-009"] = "Fail"
                
                # 第二行（重叠）：0~50, 40~100
                inputs[-6].fill("0")
                inputs[-5].fill("50")
                
                inputs[-3].fill("40")
                inputs[-2].fill("100")
                inputs[-1].fill("10")
                
                page.locator("button").filter(has_text="保存").first.click()
                page.wait_for_timeout(1000)
                page.screenshot(path=os.path.join(SCREENSHOTS, "tc_pr_010_result.webp"))
                
                error_010 = page.evaluate("Array.from(document.querySelectorAll('.el-message')).map(e => e.innerText).join(' ')")
                html = page.content()
                if "el-form-item__error" in html or "交叉" in error_010 or "重叠" in error_010 or "包含" in error_010 or "失败" in error_010:
                    results["TC-PR-010"] = "Pass"
                else:
                    results["TC-PR-010"] = "Fail"
            else:
                results["TC-PR-009"] = "Blocked-ENV (Not enough step inputs)"
                results["TC-PR-010"] = "Blocked-ENV"
        except Exception as e:
            print(f"Error in TC-PR-009/010: {e}")
            results["TC-PR-009"] = "Blocked-ENV"
            results["TC-PR-010"] = "Blocked-ENV"

        browser.close()

    print("\n" + "=" * 60)
    for tc, r in results.items():
        print(f"  {'✅' if 'Pass' in r else '❌' if 'Fail' in r else '⚠️'} {tc}: {r}")

if __name__ == "__main__":
    main()
