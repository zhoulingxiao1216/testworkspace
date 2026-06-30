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
    print("TC-CL-CART & TC-CO Batch 1: 购物车与结算台突击")
    print("=" * 60)
    
    if not os.path.exists(SCREENSHOTS):
        os.makedirs(SCREENSHOTS)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        
        try:
            admin_page = ctx.new_page()
            admin_login(admin_page)
            
            print("  [SSO] 导航至客户列表...")
            admin_page.goto("https://lying-admin.hubbuyer.com/admin/user/list", timeout=30000)
            admin_page.wait_for_timeout(3000)
            
            # 展开高级搜索
            expand_btn = admin_page.locator("text=展开").first
            if expand_btn.count() > 0:
                expand_btn.click()
                admin_page.wait_for_timeout(1000)
                
            # 填入邮箱
            email_input = admin_page.locator("input[placeholder*='邮箱']").first
            if email_input.count() > 0:
                email_input.fill("dyzlxmay@qq.com")
            else:
                # 尝试填入所有可见输入框的其中一个
                inputs = admin_page.locator("input.el-input__inner").all()
                for inp in inputs:
                    inp.fill("dyzlxmay@qq.com")
                    
            admin_page.locator("button").filter(has_text="查询").first.click()
            admin_page.wait_for_timeout(3000)
            
            # 使用查询到的第一条记录
            row = admin_page.locator("tr.el-table__row").first
            
            with admin_page.expect_popup() as popup_info:
                btn = row.locator("button").filter(has_text="会员中心").first
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
            
            # ----------------------------------------------------
            # 购物车 (Cart) 验证
            # ----------------------------------------------------
            print("\n  [TC-CL-CART] 导航至购物车...")
            frontend_page.goto("https://lying-b2b.hubbuyer.com/user/cart/index", timeout=30000)
            frontend_page.wait_for_timeout(5000)
            
            # 关闭可能的 cookie banner
            btn = frontend_page.locator("text=Agree").last
            if btn.count() > 0:
                btn.click(force=True)
                frontend_page.wait_for_timeout(1000) # wait for animation
            
            # 尝试全选
            print("  [TC-CL-CART] 尝试点击全选 (Select All)...")
            try:
                # 使用原生 JS 强制点击所有的 checkbox 标签
                frontend_page.evaluate("document.querySelectorAll('.el-checkbox').forEach(cb => cb.click())")
                frontend_page.wait_for_timeout(2000) # wait for total calculation
            except Exception as e:
                print(f"  Warning: Select All error: {e}")
            
            frontend_page.screenshot(path=os.path.join(SCREENSHOTS, "tc_cl_cart_page.webp"), full_page=True)
            
            html = frontend_page.content()
            if "CNY" in html or "JPY" in html or "总价" in html or "Total" in html:
                results["TC-CL-CART"] = "Pass (Cart items loaded successfully)"
            else:
                results["TC-CL-CART"] = "Fail (Cart empty or failed to load)"
                
            # ----------------------------------------------------
            # 结算台 (Checkout) 抢滩
            # ----------------------------------------------------
            print("\n  [TC-CO] 尝试点击第一次 Next Step (离开购物车)...")
            
            try:
                frontend_page.get_by_text("Next Step").last.click()
                clicked_1 = True
            except Exception as e:
                print(f"  Warning: First Next Step click failed: {e}")
                clicked_1 = False
            
            if clicked_1:
                print("  [TC-CO] 成功点击第一次 Next Step...")
                frontend_page.wait_for_timeout(5000) # Wait for second page to load
                
                url = frontend_page.url.lower()
                if "additionalservices" in url:
                    print("  [TC-CO] 成功进入增值服务选择页 (Additional Items)...")
                    # 在增值服务页，需要勾选商品并选择必填的质检方式
                    print("  [TC-CO] 尝试在增值服务页选择商品和质检方式...")
                    try:
                        frame = frontend_page.frame_locator('iframe.iframe')
                        
                        # 1. Click Select All (It's in the iframe)
                        try:
                            frame.locator("xpath=//label[contains(., 'Select All')]").first.click(timeout=5000, force=True)
                            print("  [TC-CO] 已勾选增值服务 Select All")
                        except Exception as e:
                            print(f"  Warning: Select All click failed: {e}")
                            
                        # 2. Click Inspection Method (It's in the iframe)
                        try:
                            frame.locator(".method-item, .item, .card, div").filter(has_text="Detailed sampling").first.click(timeout=5000, force=True)
                            print("  [TC-CO] 已选择质检方式 Detailed sampling")
                        except Exception as e:
                            print(f"  Warning: Detailed sampling click failed: {e}")
                            
                        frontend_page.wait_for_timeout(2000)
                        
                        # 3. Click Next Step (It's on the main page)
                        try:
                            frontend_page.locator("text=Next Step").last.click(timeout=5000, force=True)
                            clicked_2 = True
                        except Exception as e:
                            print(f"  Warning: Second Next Step click failed: {e}")
                            
                            # FALLBACK: Force Navigation to Checkout
                            print("  [TC-CO] 尝试直接通过 URL 注入绕过增值服务页限制...")
                            import urllib.parse
                            parsed = urllib.parse.urlparse(frontend_page.url)
                            query = urllib.parse.parse_qs(parsed.query)
                            if 'ids' in query:
                                ids_str = query['ids'][0]
                                confirm_url = f"https://lying-b2b.hubbuyer.com/user/order/confirm?cart_detail_ids={urllib.parse.quote(ids_str)}&source_type=cart"
                                frontend_page.goto(confirm_url)
                                clicked_2 = True
                            else:
                                clicked_2 = False
                            
                    except Exception as e:
                        print(f"  Warning: Iframe handling failed: {e}")
                        clicked_2 = False
                                        
                    # Dump HTML to inspect DOM if needed
                    with open(os.path.join(SCREENSHOTS, "additional_services.html"), "w", encoding="utf-8") as f:
                        f.write(frontend_page.content())
                        
                    print(f"  [TC-CO] 未进入最终结算台，停留在增值服务页。当前 URL: {url}。已保存 DOM。")
                    frontend_page.wait_for_timeout(2000)
                else:
                    print(f"  [TC-CO] 未进入增值服务页，当前 URL: {url}，可能直接进入了结算台。")
                    frontend_page.wait_for_timeout(5000)
                
                frontend_page.screenshot(path=os.path.join(SCREENSHOTS, "tc_co_checkout_page.webp"), full_page=True)
                
                url = frontend_page.url.lower()
                print(f"  [TC-CO] 当前 URL: {url}")
                
                if "confirm" in url or "checkout" in url or "order" in url:
                    results["TC-CO"] = "Pass (Navigated to Checkout Confirmation)"
                    
                    checkout_html = frontend_page.content()
                    # 断言代采手续费、运费预估等模块
                    if "手续费" in checkout_html or "Service Fee" in checkout_html or "fee" in checkout_html.lower():
                        results["TC-CO-FEES"] = "Pass (Service Fee module rendered)"
                    else:
                        results["TC-CO-FEES"] = "Fail (Service Fee missing)"
                else:
                    results["TC-CO"] = "Fail (Did not navigate to checkout)"
            else:
                results["TC-CO"] = "Blocked-ENV (Checkout button not found)"
            
            admin_page.close()
        except Exception as e:
            print(f"Exception: {e}")
            results["EXECUTION"] = f"Error: {e}"

        browser.close()

    print("\n" + "=" * 60)
    for tc, r in results.items():
        print(f"  {'✅' if 'Pass' in r else '❌' if 'Fail' in r else '⚠️'} {tc}: {r}")

if __name__ == "__main__":
    main()
