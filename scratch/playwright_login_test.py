#!/usr/bin/env python3
import re
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT_DIR = Path.cwd() / 'output' / 'playwright' / 'agent2_login'
OUT_DIR.mkdir(parents=True, exist_ok=True)

def try_login(p, url, account, password, name):
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    result = {"target": url, "account": account, "success": False, "reason": None, "cookies": [], "storage_keys": []}
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        page.wait_for_timeout(500)

        # Try common account selectors
        account_selectors = ['input[name="account"]', 'input[name="username"]', 'input[name="userName"]', 'input[type="email"]', 'input[type="text"]']
        pass_selectors = ['input[type="password"]', 'input[name="password"]']

        def first_visible(selectors):
            for s in selectors:
                loc = page.locator(s)
                try:
                    if loc.count() and loc.first.is_visible():
                        return loc.first
                except Exception:
                    continue
            return None

        user = first_visible(account_selectors)
        pwd = first_visible(pass_selectors)

        if not user or not pwd:
            result['reason'] = '账号或密码输入框未找到'
            page.screenshot(path=str(OUT_DIR / f'{name}_no_inputs.png'), full_page=True)
            return result

        user.click(); user.fill(account)
        pwd.click(); pwd.fill(password)

        # Try to click login button
        login_clicked = False
        try:
            btn = page.get_by_role('button', name=re.compile(r'登录|Login|Sign in|提交|确定', re.I))
            if btn.count():
                btn.first.click()
                login_clicked = True
        except Exception:
            pass

        if not login_clicked:
            try:
                submit = page.locator('button[type="submit"], input[type="submit"]').first
                if submit and submit.count():
                    submit.click(); login_clicked = True
            except Exception:
                pass

        if not login_clicked:
            # fallback: press Enter in password
            try:
                pwd.press('Enter'); login_clicked = True
            except Exception:
                pass

        page.wait_for_load_state('networkidle', timeout=20000)
        page.wait_for_timeout(1500)

        result['final_url'] = page.url
        # collect cookies and storage
        result['cookies'] = context.cookies()
        try:
            result['storage_keys'] = page.evaluate('() => Object.keys(localStorage).concat(Object.keys(sessionStorage).map(k=>"session:"+k))')
        except Exception:
            result['storage_keys'] = []

        # heuristics for success
        password_inputs = page.locator('input[type="password"]').count()
        body_text = page.locator('body').inner_text()[:2000]
        has_error = bool(re.search(r'密码错误|账号.*错误|用户名.*错误|验证码|captcha|失败|invalid|error|Incorrect', body_text, re.I))

        if (len(result['cookies'])>0 or len(result['storage_keys'])>0 or password_inputs==0) and not has_error:
            result['success'] = True
        else:
            result['reason'] = f'登录后未检测到会话或发生错误; cookies={len(result["cookies"])}, storage={len(result["storage_keys"])}, pwd_inputs={password_inputs}, has_error={has_error}'
            page.screenshot(path=str(OUT_DIR / f'{name}_failed.png'), full_page=True)

        # always save post-login screenshot
        page.screenshot(path=str(OUT_DIR / f'{name}_post.png'), full_page=True)
        return result
    except Exception as e:
        result['reason'] = str(e)
        try:
            page.screenshot(path=str(OUT_DIR / f'{name}_error.png'), full_page=True)
        except Exception:
            pass
        return result
    finally:
        try:
            context.close()
            browser.close()
        except Exception:
            pass

def main():
    with sync_playwright() as p:
        results = []
        # admin
        admin_url = 'https://hlc-admin.hubbuyer.com/'
        results.append(try_login(p, admin_url, 'admin', '123333', 'admin'))
        # front
        front_url = 'https://hlc-b2b.hubbuyer.com/'
        results.append(try_login(p, front_url, '17706793737@163.com', '123456', 'front'))
        out = {'results': results}
        print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
