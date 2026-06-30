# -*- coding: utf-8 -*-
import os, sys, time
from playwright.sync_api import sync_playwright
import urllib.parse
import re

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

SCREENSHOTS = r"d:\test_workspace\会员体系\测试文档\执行报告\screenshots"

TEST_ACCOUNTS = [
    {"email": "369901314@qq.com", "currency": "JPY", "desc": "TC-FI-005"},
    {"email": "dyzlxmay@qq.com", "currency": "USD", "desc": "TC-FI-006"}
]

def run_multi_currency_test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        admin_page = context.new_page()
        
        results = {}
        
        print("\n============================================================")
        print("TC-FI Batch 3: 跨国货币战争 (Multi-Currency & Financials)")
        print("============================================================")
        
        print("\n[Admin] 正在静默登录管理后台...")
        admin_page.goto("https://lying-admin.hubbuyer.com/login", timeout=30000)
        admin_page.wait_for_timeout(2000)
        
        print("  [Admin] Login...")
        inputs = admin_page.locator("input").all()
        if len(inputs) >= 2:
            inputs[0].fill("admin")
            inputs[1].fill("123333")
        admin_page.locator("button").filter(has_text="登录").click()
        admin_page.wait_for_timeout(3000)
        
        for account in TEST_ACCOUNTS:
            email = account["email"]
            currency = account["currency"]
            tc_id = account["desc"]
            print(f"\n============================================================")
            print(f" 开始执行账号: {email} | 货币: {currency} | 目标用例: {tc_id}")
            print(f"============================================================")
            
            admin_page.goto("https://lying-admin.hubbuyer.com/admin/user/list", timeout=30000)
            admin_page.wait_for_timeout(3000)
            
            print(f"  [SSO] Searching for: {email}...")
            
            expand_btn = admin_page.locator("text=展开").first
            if expand_btn.count() > 0:
                expand_btn.click()
                admin_page.wait_for_timeout(1000)
                
            email_input = admin_page.locator("input[placeholder*='邮箱']").first
            if email_input.count() > 0:
                email_input.fill(email)
            else:
                inputs = admin_page.locator("input.el-input__inner").all()
                for inp in inputs:
                    try:
                        inp.fill(email)
                    except:
                        pass
                    
            admin_page.locator("button").filter(has_text="查询").first.click()
            admin_page.wait_for_timeout(3000)
            
            row = admin_page.locator("tr.el-table__row").filter(has_text=email).first
            if row.count() == 0:
                print(f"  ❌ {tc_id}: Blocked (Account {email} not found)")
                results[f"{tc_id}_{currency}"] = "Fail (Account not found)"
                continue
            
            with admin_page.expect_popup() as popup_info:
                btn = row.locator("button").filter(has_text="前台").first
                if btn.count() > 0:
                    btn.click()
                else:
                    row.locator("text=会员中心").first.click()
                
                admin_page.wait_for_timeout(1000)
                confirm_btn = admin_page.locator(".el-popper button").filter(has_text="确定").first
                if confirm_btn.count() == 0:
                    confirm_btn = admin_page.locator("button").filter(has_text="确定").last
                confirm_btn.click()
            
            frontend_page = popup_info.value
            frontend_page.wait_for_load_state()
            frontend_page.wait_for_timeout(5000)
            
            print(f"  [TC-CL-CART] 导航至购物车...")
            frontend_page.goto("https://lying-b2b.hubbuyer.com/user/cart/index", timeout=30000)
            frontend_page.wait_for_timeout(5000)
            
            btn = frontend_page.locator("text=Agree").last
            if btn.count() > 0:
                btn.click(force=True)
                frontend_page.wait_for_timeout(1000)
            
            try:
                frontend_page.evaluate("document.querySelectorAll('.el-checkbox').forEach(cb => cb.click())")
                frontend_page.wait_for_timeout(2000)
            except Exception as e:
                print(f"  Warning: Select All error: {e}")
            
            print(f"  [TC-CO] 尝试获取 Checkout Token...")
            try:
                frontend_page.locator("text=Next Step").last.click(timeout=5000, force=True)
            except Exception as e:
                print(f"  Warning: First Next Step click failed: {e}")
            
            frontend_page.wait_for_timeout(5000)
            
            parsed = urllib.parse.urlparse(frontend_page.url)
            query = urllib.parse.parse_qs(parsed.query)
            if 'ids' in query:
                ids_str = query['ids'][0]
                confirm_url = f"https://lying-b2b.hubbuyer.com/user/order/confirm?cart_detail_ids={urllib.parse.quote(ids_str)}&source_type=cart"
                print(f"  [TC-CO] URL Fallback 注入: 跳转至结算台...")
                frontend_page.goto(confirm_url)
                frontend_page.wait_for_timeout(8000)
            
            frontend_page.screenshot(path=os.path.join(SCREENSHOTS, f"tc_fi_{currency}_checkout.webp"), full_page=True)
            
            html = frontend_page.content()
            
            if currency == "JPY":
                match = re.search(r'JPY\s*[\d,]+\.\d+', html)
                if match:
                    print(f"  ❌ {tc_id}: Fail (JPY contains decimal places: {match.group(0)})")
                    results[f"{tc_id}_{currency}"] = "Fail (Decimals in JPY)"
                else:
                    print(f"  ✅ {tc_id}: Pass (JPY is properly integer rounded)")
                    results[f"{tc_id}_{currency}"] = "Pass"
            elif currency == "USD":
                match = re.search(r'USD\s*[\d,]+\.\d{2}', html)
                if match:
                    print(f"  ✅ {tc_id}: Pass (USD has correct 2 decimal places: {match.group(0)})")
                    results[f"{tc_id}_{currency}"] = "Pass"
                else:
                    print(f"  ❌ {tc_id}: Fail (USD decimal precision missing/incorrect)")
                    results[f"{tc_id}_{currency}"] = "Fail (Missing Decimals)"
            
            frontend_page.close()
            print("  Session ended, switching to next account...")

        print("\n============================================================")
        for k, v in results.items():
            icon = "✅" if "Pass" in v else "❌"
            print(f"  {icon} {k}: {v}")
            
        browser.close()

if __name__ == "__main__":
    run_multi_currency_test()
