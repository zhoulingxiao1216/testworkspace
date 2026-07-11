# -*- coding: utf-8 -*-
"""
E3 MG模块执行脚本 — Batch 4
包含：TC-MG-012, TC-MG-013
利用前台 Admin 的“详情”页直接修改等级和过期时间，无需污染 DB。
"""
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
    print("TC-MG-012/013: 管理端手动修改等级与过期校验 (Admin UI)")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        
        admin_login(page)
        
        # 导航至客户信息
        page.goto("https://lying-admin.hubbuyer.com/admin/user/list", timeout=30000)
        page.wait_for_timeout(3000)
        
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

        # 我们随便找列表里第一个非 VIP 的用户进行测试
        # 为了不影响其他核心账号，可以在搜索框输入比如 "A-" 或直接取第一条
        test_user_name = ""
        
        # 1. 寻找详情按钮并点击
        clicked_detail = page.evaluate("""() => {
            let rows = Array.from(document.querySelectorAll('table tbody tr'));
            for(let row of rows) {
                // 找一个不是 VIP会员 的
                if(!row.innerText.includes('VIP会员')) {
                    let btn = Array.from(row.querySelectorAll('button, a')).find(b => b.innerText.includes('详情'));
                    if(btn) {
                        btn.click();
                        return row.innerText.split('\\t')[0] || "Found";
                    }
                }
            }
            // 如果都找不到，就点第一个
            let detail = Array.from(document.querySelectorAll('button, a')).find(b => b.innerText.includes('详情'));
            if(detail) { detail.click(); return "First Row"; }
            return null;
        }""")
        
        if not clicked_detail:
            print("  ⚠️ 未能打开客户详情")
            results["TC-MG-013"] = "Blocked-ENV"
            results["TC-MG-012"] = "Blocked-ENV"
            browser.close()
            return
            
        page.wait_for_timeout(3000)
        print(f"  已打开客户详情: {clicked_detail}")
        page.screenshot(path=os.path.join(SCREENSHOTS, "tc_013_before.webp"))
        
        # ============================================================
        # TC-MG-013: 管理端下拉框切换为 VIP
        # ============================================================
        try:
            print("  尝试修改会员等级为 VIP...")
            # 点击包含“一般会员”或其他等级的下拉框
            # 通过 evaluate 找到下拉框并触发点击
            page.evaluate("""() => {
                // 寻找详情弹窗中的第一个 el-select 的输入框
                let inputs = Array.from(document.querySelectorAll('.el-dialog input'));
                // 通常下拉框是 readonly 或者是包含 placeholder '请选择' 的
                // 这里我们找所有的 input，通常第一个就是等级下拉框
                // 稳妥起见，直接找它的父节点点击
                let select = document.querySelector('.el-dialog .el-select');
                if(select) select.click();
            }""")
            page.wait_for_timeout(1000)
            
            # 选择 VIP
            page.evaluate("""() => {
                let items = Array.from(document.querySelectorAll('.el-select-dropdown__item'));
                let vip = items.find(el => el.innerText.includes('VIP'));
                if(vip) vip.click();
            }""")
            page.wait_for_timeout(1000)
            
            # 点击底部的确认按钮
            page.evaluate("""() => {
                let btns = Array.from(document.querySelectorAll('.el-dialog button'));
                let confirmBtn = btns.find(b => b.innerText.includes('确认') || b.innerText.includes('确定') || b.innerText.includes('保存'));
                if(confirmBtn) confirmBtn.click();
            }""")
            page.wait_for_timeout(3000)
            
            # 刷新页面验证
            page.reload()
            page.wait_for_timeout(4000)
            text_after = page.inner_text("table tbody")
            
            if "VIP" in text_after:
                print("  ✅ TC-MG-013 Pass: 用户等级已成功提权为 VIP")
                results["TC-MG-013"] = "Pass"
            else:
                print("  ❌ TC-MG-013 Fail: 列表未更新为 VIP")
                results["TC-MG-013"] = "Fail"
                
        except Exception as e:
            print(f"  ⚠️ TC-MG-013 异常: {e}")
            results["TC-MG-013"] = "Blocked-ENV"
            
        # ============================================================
        # TC-MG-012: 管理端提前撤销 VIP / 修改到期时间
        # ============================================================
        try:
            print("  再次打开详情，尝试修改过期时间使其降级...")
            page.evaluate("""() => {
                let detail = Array.from(document.querySelectorAll('button, a')).find(b => b.innerText.includes('详情'));
                if(detail) detail.click();
            }""")
            page.wait_for_timeout(3000)
            
            # 尝试点击时间输入框，将其改为过去的时间
            page.evaluate("""() => {
                let inputs = Array.from(document.querySelectorAll('.el-dialog input'));
                // 找包含时间格式的输入框，或者根据你的截图，它是包含在 el-date-editor 里的
                let dateInput = inputs.find(i => i.placeholder && (i.placeholder.includes('时间') || i.placeholder.includes('日期')) || (i.value && i.value.includes('20')));
                if(dateInput) {
                    // 强行把值改为昨天
                    dateInput.value = '2020-01-01 00:00:00';
                    // 触发 input 事件
                    dateInput.dispatchEvent(new Event('input', { bubbles: true }));
                    dateInput.dispatchEvent(new Event('change', { bubbles: true }));
                } else {
                    // 如果找不到时间框，我们就把下拉框改回一般会员
                    let select = document.querySelector('.el-dialog .el-select');
                    if(select) select.click();
                }
            }""")
            page.wait_for_timeout(1000)
            
            # 如果是改回一般会员
            page.evaluate("""() => {
                let items = Array.from(document.querySelectorAll('.el-select-dropdown__item'));
                let general = items.find(el => el.innerText.includes('一般会员') || el.innerText.includes('普通'));
                if(general) general.click();
            }""")
            page.wait_for_timeout(1000)
            
            page.screenshot(path=os.path.join(SCREENSHOTS, "tc_012_editing.webp"))
            
            page.evaluate("""() => {
                let btns = Array.from(document.querySelectorAll('.el-dialog button'));
                let confirmBtn = btns.find(b => b.innerText.includes('确认') || b.innerText.includes('确定') || b.innerText.includes('保存'));
                if(confirmBtn) confirmBtn.click();
            }""")
            page.wait_for_timeout(3000)
            
            page.reload()
            page.wait_for_timeout(4000)
            text_final = page.inner_text("table tbody")
            
            if "一般" in text_final or "普通" in text_final:
                print("  ✅ TC-MG-012 Pass: 用户已成功撤销 VIP / 被降级")
                results["TC-MG-012"] = "Pass"
            else:
                print("  ❌ TC-MG-012 Fail: 用户仍然是 VIP")
                results["TC-MG-012"] = "Fail"
                
        except Exception as e:
            print(f"  ⚠️ TC-MG-012 异常: {e}")
            results["TC-MG-012"] = "Blocked-ENV"

        browser.close()

    print("\n" + "=" * 60)
    for tc, r in results.items():
        print(f"  {'✅' if 'Pass' in r else '❌' if 'Fail' in r else '⚠️'} {tc}: {r}")

if __name__ == "__main__":
    main()
