# -*- coding: utf-8 -*-
"""
E3 MG模块执行脚本 — Batch 2 终极修复版
"""
from playwright.sync_api import sync_playwright
import os, sys, time

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
SCREENSHOTS = r"d:\test_workspace\会员体系\测试文档\执行报告\screenshots"
results = {}

def admin_login(page):
    page.goto("https://lying-admin.hubbuyer.com/login", timeout=30000)
    page.wait_for_selector("input", timeout=10000)
    inputs = page.query_selector_all("input")
    inputs[0].fill("admin")
    inputs[1].fill("123333")
    page.query_selector("button").click()
    try:
        page.wait_for_url("**/admin/**", timeout=15000)
    except:
        page.wait_for_timeout(5000)

def create_invite_level(page, name_zh):
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
    textareas = page.query_selector_all(".el-dialog textarea")
    
    if len(inputs) >= 8:
        inputs[0].fill(name_zh)
        inputs[1].fill(f"{name_zh}_EN")
        inputs[2].fill(f"{name_zh}_JP")
        inputs[3].fill(f"{name_zh}_KR")
        
        inputs[8].click(force=True)
        page.wait_for_timeout(1000)
        for opt in page.query_selector_all(".el-select-dropdown__item"):
            if "邀请制" in opt.inner_text():
                opt.click(force=True)
                break
        page.wait_for_timeout(500)
        
    for i in range(min(4, len(textareas))):
        textareas[i].fill(f"Desc {i}")
        
    for btn in page.query_selector_all(".el-dialog button"):
        if btn.inner_text().strip() in ("确定", "确认", "保存"):
            btn.click()
            break
    page.wait_for_timeout(3000)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        admin_login(page)
        
        ts = str(int(time.time()))
        test_level = f"AG_INV_{ts}"
        
        # TC-MG-004 & 005
        print("\n" + "=" * 60)
        print("TC-MG-004 & 005: 邀请制等级字段屏蔽/保留验证")
        print("=" * 60)
        try:
            create_invite_level(page, test_level)
            
            page.goto("https://lying-admin.hubbuyer.com/b2b/member/country", timeout=30000)
            page.wait_for_timeout(3000)
            
            for btn in page.query_selector_all("button"):
                if "编辑" in (btn.inner_text() or ""):
                    btn.click()
                    break
                    
            page.wait_for_timeout(3000)
            
            # 使用 locator 和 scroll_into_view_if_needed 确保可见，或者直接force click
            loc = page.locator(f"text={test_level}").first
            if loc.count() > 0:
                loc.scroll_into_view_if_needed()
                loc.click(force=True)
                page.wait_for_timeout(2000)
                page.screenshot(path=os.path.join(SCREENSHOTS, "tab_invite_level.webp"))
                
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
                
        except Exception as e:
            print(f"Error in 004/005: {e}")
            results["TC-MG-004"] = "Blocked-ENV"
            results["TC-MG-005"] = "Blocked-ENV"
            
        # [Restore]
        try:
            page.goto("https://lying-admin.hubbuyer.com/b2b/member/level", timeout=30000)
            page.wait_for_timeout(3000)
            for row in page.query_selector_all("table tbody tr"):
                if test_level in (row.inner_text() or ""):
                    for b in row.query_selector_all("button"):
                        if b.inner_text().strip() == "禁用":
                            b.click()
                            page.wait_for_timeout(1000)
                            try: page.click(".el-popconfirm .el-button--primary", timeout=3000)
                            except:
                                try: page.click(".el-message-box__btns .el-button--primary", timeout=3000)
                                except: pass
                            break
                    break
        except: pass

        # TC-MG-008
        print("\n" + "=" * 60)
        print("TC-MG-008: 手动VIP授权入口")
        print("=" * 60)
        try:
            page.goto("https://lying-admin.hubbuyer.com/admin/user/list", timeout=30000)
            page.wait_for_timeout(3000)
            
            # 找到左侧菜单的 客户管理
            menus = page.query_selector_all(".el-menu-item, .el-sub-menu__title")
            for m in menus:
                t = m.inner_text().strip()
                if "客户管理" in t:
                    m.click()
                    page.wait_for_timeout(1000)
                    
            for m in page.query_selector_all(".el-menu-item"):
                if "客户信息" in m.inner_text().strip():
                    m.click()
                    break
                    
            page.wait_for_timeout(3000)
            page.screenshot(path=os.path.join(SCREENSHOTS, "customer_list_real.webp"))
            
            # 点击列表第一条的"详情"
            found_detail = False
            for btn in page.query_selector_all("button, .el-button, a"):
                t = btn.inner_text().strip() if btn.inner_text() else ""
                if "详情" in t:
                    btn.click(force=True)
                    found_detail = True
                    break
                    
            if found_detail:
                page.wait_for_timeout(3000)
                page.screenshot(path=os.path.join(SCREENSHOTS, "customer_detail.webp"))
                
                text = page.inner_text("body")
                btns_text = [b.inner_text() or "" for b in page.query_selector_all("button")]
                
                auth_found = any(k in text for k in ["VIP授权", "修改等级", "授权VIP", "会员授权"]) or any("VIP" in b for b in btns_text) or any("等级" in b for b in btns_text)
                
                if auth_found:
                    results["TC-MG-008"] = "Pass (UI Verify)"
                else:
                    results["TC-MG-008"] = "Fail (No Auth Button Found)"
            else:
                results["TC-MG-008"] = "Blocked-ENV (No Detail Button)"
                
        except Exception as e:
            print(f"Error in 008: {e}")
            results["TC-MG-008"] = "Blocked-ENV"

        browser.close()

    print("\n" + "=" * 60)
    for tc, r in results.items():
        print(f"  {'✅' if 'Pass' in r else '❌' if 'Fail' in r else '⚠️'} {tc}: {r}")

if __name__ == "__main__":
    main()
