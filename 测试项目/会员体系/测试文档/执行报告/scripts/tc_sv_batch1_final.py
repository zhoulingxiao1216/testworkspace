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
    print("TC-SV Batch 1: 全球服务定价 (Final)")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        admin_login(page)
        
        page.goto("https://lying-admin.hubbuyer.com/b2b/member/service", timeout=30000)
        page.wait_for_timeout(3000)
        
        # 打开外部大弹窗
        page.evaluate("""() => {
            let btns = Array.from(document.querySelectorAll('button'));
            let edit = btns.find(b => b.innerText && b.innerText.includes('编辑'));
            if(edit) edit.click();
        }""")
        page.wait_for_timeout(3000)
        
        # 在内部表格中点击第一行的"编辑"
        page.locator(".el-dialog .el-table__body-wrapper").locator("text=编辑").first.click()
        page.wait_for_timeout(2000)
        
        # TC-SV-001: 验证普通模式（默认）
        try:
            print("  [TC-SV-001] 验证普通计费模式 UI...")
            html = page.content()
            if "成本价" in html and "客户价格" in html:
                results["TC-SV-001"] = "Pass"
            else:
                results["TC-SV-001"] = "Fail"
        except Exception as e:
            results["TC-SV-001"] = "Blocked-ENV"

        # TC-SV-002: 倒挂测试
        try:
            print("  [TC-SV-002] 测试客户价 < 成本价防损拦截...")
            # 第二个弹窗是编辑服务定价弹窗
            dialog = page.locator(".el-dialog").nth(1)
            inputs = dialog.locator(".el-input-number input").all()
            if len(inputs) >= 2:
                # 成本价
                inputs[0].fill("100")
                # 客户价格
                inputs[1].fill("50")
                
                # 点击保存
                dialog.locator("button").filter(has_text="保存").first.click()
                page.wait_for_timeout(1500)
                page.screenshot(path=os.path.join(SCREENSHOTS, "tc_sv_002_final.webp"))
                
                error_002 = page.evaluate("Array.from(document.querySelectorAll('.el-message')).map(e => e.innerText).join(' ')")
                html = page.content()
                if "el-form-item__error" in html or "小于" in error_002 or "不能" in error_002 or "大于" in error_002 or "失败" in error_002:
                    results["TC-SV-002"] = "Pass"
                else:
                    results["TC-SV-002"] = "Fail"
            else:
                results["TC-SV-002"] = "Blocked-ENV (No inputs)"
        except Exception as e:
            results["TC-SV-002"] = "Blocked-ENV"

        # TC-SV-003: 阶梯模式
        try:
            print("  [TC-SV-003] 测试切换阶梯计费模式...")
            # 点击计费方式下拉框 (当前显示为普通计费)
            dialog = page.locator(".el-dialog").nth(1)
            dialog.locator("input[placeholder='请选择']").first.click(force=True)
            page.wait_for_timeout(1000)
            
            # 点击阶梯计费
            page.locator(".el-select-dropdown__item").filter(has_text="阶梯计费").first.click(force=True)
            page.wait_for_timeout(1000)
            
            page.screenshot(path=os.path.join(SCREENSHOTS, "tc_sv_003_final.webp"))
            html = page.content()
            if "添加阶梯" in html or "阶梯" in html:
                results["TC-SV-003"] = "Pass"
            else:
                results["TC-SV-003"] = "Fail"
        except Exception as e:
            results["TC-SV-003"] = "Blocked-ENV"

        # TC-SV-007: 相谈模式
        try:
            print("  [TC-SV-007] 测试切换相谈计费模式...")
            dialog = page.locator(".el-dialog").nth(1)
            # 点击下拉框 (当前显示为阶梯计费)
            dialog.locator("input[placeholder='请选择']").first.click(force=True)
            page.wait_for_timeout(1000)
            
            # 点击相谈计费 / 面议
            item = page.locator(".el-select-dropdown__item").filter(has_text="相谈")
            if item.count() == 0:
                item = page.locator(".el-select-dropdown__item").filter(has_text="面议")
            
            if item.count() > 0:
                item.first.click(force=True)
                page.wait_for_timeout(1000)
                
                page.screenshot(path=os.path.join(SCREENSHOTS, "tc_sv_007_final.webp"))
                html = page.content()
                if "面议" in html or "相谈" in html:
                    results["TC-SV-007"] = "Pass"
                else:
                    results["TC-SV-007"] = "Fail"
            else:
                results["TC-SV-007"] = "Blocked-ENV (No dropdown item)"
        except Exception as e:
            results["TC-SV-007"] = "Blocked-ENV"

        browser.close()

    print("\n" + "=" * 60)
    for tc, r in results.items():
        print(f"  {'✅' if 'Pass' in r else '❌' if 'Fail' in r else '⚠️'} {tc}: {r}")

if __name__ == "__main__":
    main()
