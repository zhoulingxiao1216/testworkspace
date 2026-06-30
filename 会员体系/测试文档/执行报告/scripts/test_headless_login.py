"""
Layer 2 验证脚本：Playwright 无头模式登录 Admin 后台
用途：验证 Playwright headless 可正常工作，且不抢占键鼠焦点
"""
from playwright.sync_api import sync_playwright
import os, sys

SCREENSHOTS_DIR = r"d:\test_workspace\会员体系\测试文档\执行报告\screenshots"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def main():
    console_logs = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        
        # Console 监听
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        
        # Step 1: 打开登录页
        print("[Step 1] 导航到 Admin 登录页...")
        page.goto("https://lying-admin.hubbuyer.com", wait_until="networkidle", timeout=30000)
        print(f"  Title: {page.title()}")
        print(f"  URL: {page.url}")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "test_headless_step1.webp"))
        print("  截图已保存: test_headless_step1.webp")
        
        # Step 2: 输入账号密码
        print("[Step 2] 输入登录凭证...")
        try:
            # 尝试常见的登录表单选择器
            page.wait_for_selector("input", timeout=10000)
            inputs = page.query_selector_all("input")
            print(f"  发现 {len(inputs)} 个 input 元素")
            
            for i, inp in enumerate(inputs):
                input_type = inp.get_attribute("type") or "text"
                input_name = inp.get_attribute("name") or inp.get_attribute("placeholder") or "unknown"
                print(f"  input[{i}]: type={input_type}, name={input_name}")
            
            # 尝试填写
            if len(inputs) >= 2:
                inputs[0].fill("admin")
                inputs[1].fill("123333")
                print("  凭证已填入")
                page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "test_headless_step2.webp"))
                print("  截图已保存: test_headless_step2.webp")
            
            # Step 3: 点击登录按钮
            print("[Step 3] 查找并点击登录按钮...")
            login_btn = page.query_selector("button[type='submit']") or page.query_selector("button")
            if login_btn:
                login_btn.click()
                page.wait_for_load_state("networkidle", timeout=15000)
                print(f"  登录后 URL: {page.url}")
                page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "test_headless_step3.webp"))
                print("  截图已保存: test_headless_step3.webp")
            else:
                print("  未找到登录按钮，跳过点击")
                
        except Exception as e:
            print(f"  操作异常: {e}")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "test_headless_error.webp"))
        
        # Step 4: 输出 Console 日志
        print(f"\n[Console] 共捕获 {len(console_logs)} 条日志:")
        for log in console_logs[:10]:
            print(f"  {log}")
        
        # 提取 Cookie 供 Layer 1 使用
        cookies = context.cookies()
        print(f"\n[Cookies] 共 {len(cookies)} 条:")
        for c in cookies[:5]:
            print(f"  {c['name']}: {c['value'][:20]}...")
        
        browser.close()
    
    print("\n=== Playwright 无头模式验证完成 ===")
    print("整个过程中没有弹出任何浏览器窗口，键鼠未被抢占。")

if __name__ == "__main__":
    main()
