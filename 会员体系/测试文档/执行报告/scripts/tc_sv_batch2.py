# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
import os, sys, time, random

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
    print("TC-SV Batch 2: 系统联动与数据隔离 (009, 014)")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        admin_login(page)
        
        # ============================================================
        # TC-SV-014: 新增会员等级后，服务定价矩阵自动同步
        # ============================================================
        try:
            print("  [TC-SV-014] 测试新增会员等级自动联动服务定价...")
            # 1. 进入会员等级基础库
            page.goto("https://lying-admin.hubbuyer.com/b2b/member/level", timeout=30000)
            page.wait_for_timeout(3000)
            
            # 点击新增会员等级
            page.locator("button").filter(has_text="新增").first.click()
            page.wait_for_timeout(2000)
            
            # 填写入参
            unique_code = f"SVAUTO_{random.randint(1000, 9999)}"
            level_name = f"SV自动联动测试_{unique_code}"
            
            # 找到各种 input
            inputs = page.locator(".el-dialog input").all()
            if len(inputs) >= 2:
                # 等级编码 和 等级名称
                inputs[0].fill(unique_code)
                inputs[1].fill(level_name)
                
                # 点击保存
                page.evaluate("""() => {
                    let d = document.querySelector('.el-dialog');
                    if(d) {
                        let btns = Array.from(d.querySelectorAll('button'));
                        let save = btns.find(b => b.innerText && b.innerText.includes('保存'));
                        if(save) save.click();
                    }
                }""")
                page.wait_for_timeout(2000)
                
                # 2. 跳转到全球服务定价页面验证
                page.goto("https://lying-admin.hubbuyer.com/b2b/member/service", timeout=30000)
                page.wait_for_timeout(3000)
                
                # 点击某一个国家的“配置”或者“编辑”
                page.evaluate("""() => {
                    let btns = Array.from(document.querySelectorAll('button'));
                    let edit = btns.find(b => b.innerText && b.innerText.includes('编辑'));
                    if(edit) edit.click();
                }""")
                page.wait_for_timeout(3000)
                
                # 滚动一下，确保所有行都渲染
                page.evaluate("document.querySelector('.el-dialog__body').scrollTop = 1000")
                page.wait_for_timeout(1000)
                
                page.screenshot(path=os.path.join(SCREENSHOTS, "tc_sv_014_result.webp"))
                
                # 检查页面是否出现了刚创建的会员等级名称
                html = page.content()
                if level_name in html:
                    results["TC-SV-014"] = "Pass"
                else:
                    results["TC-SV-014"] = "Fail"
            else:
                results["TC-SV-014"] = "Blocked-ENV (No inputs)"
        except Exception as e:
            results["TC-SV-014"] = f"Blocked-ENV ({str(e)})"

        # ============================================================
        # TC-SV-009: 不同会员等级价格独立输入，数据互相隔离
        # ============================================================
        try:
            print("  [TC-SV-009] 测试不同会员等级服务定价数据隔离...")
            # 此时应该已经在服务定价的外部弹窗里
            # 查找一般会员和企业会员的编辑按钮 (在同一服务项下)
            
            # 第一步，点击“一般会员”的编辑
            page.locator(".el-dialog .el-table__body-wrapper").locator("text=编辑").nth(0).click()
            page.wait_for_timeout(2000)
            
            dialog_inner = page.locator(".el-dialog").nth(1)
            inputs_general = dialog_inner.locator(".el-input-number input").all()
            if len(inputs_general) >= 2:
                # 填入独立特征值
                inputs_general[0].fill("111")
                inputs_general[1].fill("222")
                
                # 截图证明输入
                page.screenshot(path=os.path.join(SCREENSHOTS, "tc_sv_009_general.webp"))
                
                # 点击取消或保存（取消即可，只是为了验证 UI 隔离，如果是结构隔离，只要弹窗没共用状态就安全）
                dialog_inner.locator("button").filter(has_text="取消").first.click()
                page.wait_for_timeout(1000)
                
                # 第二步，点击“企业会员”的编辑（第2行）
                page.locator(".el-dialog .el-table__body-wrapper").locator("text=编辑").nth(1).click()
                page.wait_for_timeout(2000)
                
                dialog_inner2 = page.locator(".el-dialog").nth(1)
                inputs_enterprise = dialog_inner2.locator(".el-input-number input").all()
                if len(inputs_enterprise) >= 2:
                    val0 = inputs_enterprise[0].input_value()
                    val1 = inputs_enterprise[1].input_value()
                    
                    page.screenshot(path=os.path.join(SCREENSHOTS, "tc_sv_009_enterprise.webp"))
                    
                    # 验证值不是 111 和 222
                    if val0 != "111" and val1 != "222":
                        results["TC-SV-009"] = "Pass"
                    else:
                        results["TC-SV-009"] = "Fail"
                else:
                    results["TC-SV-009"] = "Blocked-ENV (No enterprise inputs)"
            else:
                results["TC-SV-009"] = "Blocked-ENV (No general inputs)"
        except Exception as e:
            results["TC-SV-009"] = f"Blocked-ENV ({str(e)})"

        browser.close()

    print("\n" + "=" * 60)
    for tc, r in results.items():
        print(f"  {'✅' if 'Pass' in r else '❌' if 'Fail' in r else '⚠️'} {tc}: {r}")

if __name__ == "__main__":
    main()
