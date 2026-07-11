from playwright.sync_api import sync_playwright
import os, sys

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

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
        
        page.evaluate("""() => {
            let btns = Array.from(document.querySelectorAll('button'));
            let edit = btns.find(b => b.innerText.includes('编辑'));
            if(edit) edit.click();
        }""")
        page.wait_for_timeout(3000)
        
        html = page.evaluate("""() => {
            let result = "";
            let el = Array.from(document.querySelectorAll('*')).find(e => e.childNodes.length === 1 && e.innerText.includes('会员价格'));
            if(el) result += "Price Parent HTML:\\n" + el.parentElement.parentElement.outerHTML + "\\n";
            
            let step = Array.from(document.querySelectorAll('*')).find(e => e.childNodes.length === 1 && e.innerText.includes('代采阶梯'));
            if(step) result += "Step Parent HTML:\\n" + step.parentElement.parentElement.outerHTML + "\\n";
            return result;
        }""")
        print(html)
        
        # Test locating via text filter
        locs = page.locator(".el-input-number").all()
        print(f"Total el-input-number found: {len(locs)}")
        
        browser.close()

if __name__ == "__main__":
    main()
