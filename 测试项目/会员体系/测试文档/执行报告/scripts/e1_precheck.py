"""
E1 环境预检脚本 (Layer 2 - Playwright Headless)
检查项: URL可达性 / Admin登录 / B2B登录 / 截图
"""
from playwright.sync_api import sync_playwright
import os, sys, io, json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SCREENSHOTS = r"d:\test_workspace\会员体系\测试文档\执行报告\screenshots"
os.makedirs(SCREENSHOTS, exist_ok=True)

TARGETS = {
    "admin": "https://lying-admin.hubbuyer.com",
    "b2b": "https://lying-b2b.hubbuyer.com",
    "www": "https://lying-www.hubbuyer.com",
}

ADMIN_CRED = {"user": "admin", "pass": "123333"}
B2B_CRED = {"user": "359901314@qq.com", "pass": "123456"}

results = {}

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        # === Check 1: URL Reachability ===
        print("=" * 60)
        print("[E1-1] URL 可达性检查")
        print("=" * 60)
        for name, url in TARGETS.items():
            try:
                resp = page.goto(url, wait_until="domcontentloaded", timeout=15000)
                status = resp.status if resp else "N/A"
                title = page.title()
                ok = status == 200 or status == 301 or status == 302
                results[f"url_{name}"] = "Pass" if ok else "Fail"
                print(f"  [{name}] {url}")
                print(f"    Status: {status} | Title: {title} | {'✅ Pass' if ok else '❌ Fail'}")
                page.screenshot(path=os.path.join(SCREENSHOTS, f"env_url_{name}.webp"))
            except Exception as e:
                results[f"url_{name}"] = "Fail"
                print(f"  [{name}] {url}")
                print(f"    ❌ Fail: {e}")

        # === Check 2: Admin Login ===
        print("\n" + "=" * 60)
        print("[E1-2] Admin 登录验证")
        print("=" * 60)
        try:
            page.goto("https://lying-admin.hubbuyer.com/login", wait_until="networkidle", timeout=20000)
            page.wait_for_selector("input", timeout=10000)
            inputs = page.query_selector_all("input")
            
            # 填入凭证
            inputs[0].fill(ADMIN_CRED["user"])
            inputs[1].fill(ADMIN_CRED["pass"])
            
            # 点击登录
            btn = page.query_selector("button")
            if btn:
                btn.click()
            
            # 等待跳转
            page.wait_for_timeout(3000)
            page.wait_for_load_state("networkidle", timeout=15000)
            
            current_url = page.url
            is_login_page = "/login" in current_url
            
            if not is_login_page:
                results["admin_login"] = "Pass"
                print(f"  ✅ 登录成功! 跳转至: {current_url}")
                
                # 提取 Cookies 供后续使用
                cookies = context.cookies()
                cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
                print(f"  Cookies 数量: {len(cookies)}")
                
                # 保存 cookies 到文件供 Layer 1 API 使用
                cookie_file = os.path.join(SCREENSHOTS, "..", "scripts", "helpers", "admin_cookies.json")
                os.makedirs(os.path.dirname(cookie_file), exist_ok=True)
                with open(cookie_file, 'w') as f:
                    json.dump(cookies, f, ensure_ascii=False)
                print(f"  Cookies 已保存至 admin_cookies.json")
            else:
                results["admin_login"] = "Fail"
                print(f"  ❌ 登录失败，仍在登录页: {current_url}")
            
            page.screenshot(path=os.path.join(SCREENSHOTS, "env_admin_login.webp"))
        except Exception as e:
            results["admin_login"] = "Fail"
            print(f"  ❌ Admin 登录异常: {e}")
            page.screenshot(path=os.path.join(SCREENSHOTS, "env_admin_login_error.webp"))

        # === Check 3: 核心管理页面可达 ===
        print("\n" + "=" * 60)
        print("[E1-3] 核心管理页面可达性")
        print("=" * 60)
        admin_pages = {
            "会员等级基础库": "https://lying-admin.hubbuyer.com/b2b/member/level",
            "全球会员定价": "https://lying-admin.hubbuyer.com/b2b/member/country",
            "全球服务定价": "https://lying-admin.hubbuyer.com/b2b/member/service",
        }
        for name, url in admin_pages.items():
            try:
                page.goto(url, wait_until="networkidle", timeout=15000)
                page.wait_for_timeout(2000)
                current = page.url
                title = page.title()
                # 如果被重定向回登录页说明 session 丢失
                if "/login" in current:
                    results[f"page_{name}"] = "Fail"
                    print(f"  [{name}] ❌ Session 丢失，被重定向至登录页")
                else:
                    results[f"page_{name}"] = "Pass"
                    print(f"  [{name}] ✅ 可达 | URL: {current}")
                safe_name = name.replace("/", "_")
                page.screenshot(path=os.path.join(SCREENSHOTS, f"env_page_{safe_name}.webp"))
            except Exception as e:
                results[f"page_{name}"] = "Fail"
                print(f"  [{name}] ❌ 异常: {e}")

        browser.close()

    # === Gate Decision ===
    print("\n" + "=" * 60)
    print("[E1] GATE DECISION")
    print("=" * 60)
    all_pass = all(v == "Pass" for v in results.values())
    for k, v in results.items():
        symbol = "✅" if v == "Pass" else "❌"
        print(f"  {symbol} {k}: {v}")
    
    if all_pass:
        print("\n🟢 环境预检通过，进入队列编排")
    else:
        print("\n🔴 环境预检存在失败项，请查看详情")
    
    return 0 if all_pass else 1

if __name__ == "__main__":
    sys.exit(main())
