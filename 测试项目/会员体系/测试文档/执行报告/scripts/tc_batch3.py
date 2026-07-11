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
    print("TC-MG-010/011: VIP到期后降级校验")
    print("=" * 60)
    
    # 1. 查库寻找一个已过期的测试账号
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "helpers"))
    from db_helper import query
    
    expired_user_id = None
    try:
        # 查询过期时间早于当前时间，且不是默认极小值的时间的记录
        print("  Layer 1: 扫描数据库寻找过期 VIP 记录...")
        db_rows = query("SELECT user_uuid, member_expire_at, member_level_uuid FROM b2b_user_role WHERE member_expire_at < NOW() AND member_expire_at > '2024-01-01' ORDER BY member_expire_at DESC LIMIT 1")
        if db_rows:
            expired_user_id = db_rows[0]['user_uuid']
            print(f"  ✅ 发现已过期测试账号: user_uuid={expired_user_id}, expire_at={db_rows[0]['member_expire_at']}")
        else:
            print("  ⚠️ 数据库中未找到近期过期的 VIP 测试账号。")
    except Exception as e:
        print(f"  ⚠️ 数据库查询异常: {e}")

    if not expired_user_id:
        results["TC-MG-010/011"] = "Blocked-ENV (Need Manual DB Expire)"
        print("\nBatch 3 总结: ⚠️ 缺少过期测试账号。请手动使用 Navicat 将某测试账号的 member_expire_at 改为昨天，或直接提供账号。")
        return

    # 2. 如果找到了，进入 Admin 验证
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        
        print("  Layer 2: 登录 Admin 验证前台降级展示...")
        admin_login(page)
        
        page.goto("https://lying-admin.hubbuyer.com/admin/user/list", timeout=30000)
        page.wait_for_timeout(3000)
        
        # 导航至客户信息
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
        
        # 搜索该用户
        try:
            print(f"  在客户列表搜索 user_id={expired_user_id}...")
            # 假设客户列表有输入框可以输入 ID
            inputs = page.locator(".el-input__inner, input[placeholder*='搜索'], input[placeholder*='ID']").all()
            if inputs:
                inputs[0].fill(str(expired_user_id))
                page.keyboard.press("Enter")
                page.wait_for_timeout(2000)
            
            page.screenshot(path=os.path.join(SCREENSHOTS, f"tc_010_user_{expired_user_id}.webp"))
            
            # 检查列表中的等级列是否包含 "VIP" 或是否已变为 "一般会员"/"普通"
            text = page.inner_text("table tbody")
            if "VIP" in text and str(expired_user_id) in text:
                print("  ❌ TC-MG-010/011 Fail: 该过期用户在列表中依然展示为 VIP！")
                results["TC-MG-010/011"] = "Fail"
            else:
                print("  ✅ TC-MG-010/011 Pass: 过期用户未展示 VIP 标识，降级逻辑正常。")
                results["TC-MG-010/011"] = "Pass"
                
        except Exception as e:
            print(f"  ⚠️ Admin 验证异常: {e}")
            results["TC-MG-010/011"] = "Blocked-ENV (Search Failed)"
            
        browser.close()

    print("\n" + "=" * 60)
    for tc, r in results.items():
        print(f"  {'✅' if 'Pass' in r else '❌' if 'Fail' in r else '⚠️'} {tc}: {r}")

if __name__ == "__main__":
    main()
