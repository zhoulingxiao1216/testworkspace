from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    page.goto('https://hlc-admin.hubbuyer.com/', wait_until='domcontentloaded')
    try:
        acct = page.locator('input[name="account"]').first
        pwd = page.locator('input[type="password"]').first
        if acct.count() and pwd.count():
            acct.fill('admin')
            pwd.fill('123333')
            btn = page.get_by_role('button', name='登录')
            if btn.count():
                btn.first.click()
            else:
                page.locator('button[type="submit"]').first.click()
    except Exception:
        pass
    page.wait_for_load_state('networkidle')
    # try clicking 客户信息 menu
    try:
        m = page.locator('text=客户信息').first
        if m.count():
            m.click()
            page.wait_for_load_state('networkidle')
        else:
            page.goto('https://hlc-admin.hubbuyer.com/admin/user/list', wait_until='domcontentloaded')
            page.wait_for_load_state('networkidle')
    except Exception:
        page.goto('https://hlc-admin.hubbuyer.com/admin/user/list', wait_until='domcontentloaded')
        page.wait_for_load_state('networkidle')
    inputs = page.evaluate("() => Array.from(document.querySelectorAll('input,select,button')).map(e=>({tag:e.tagName,name:e.name||'',id:e.id||'',placeholder:e.placeholder||'',text:e.innerText||e.value||''}))")
    print('INPUTS:', inputs[:50])
    rows_count = page.locator('table tbody tr').count()
    print('TABLE ROWS COUNT:', rows_count)
    if rows_count>0:
        print('ROW0 HTML:', page.locator('table tbody tr').first.inner_html()[:1000])
    else:
        # print some page text sample
        print('BODY SAMPLE:', page.locator('body').inner_text()[:1000])
    browser.close()
