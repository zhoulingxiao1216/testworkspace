const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const urls = [
    'https://lying-www.hubbuyer.com',
    'https://lying-www.hubbuyer.com/fee',
    'https://lying-b2b.hubbuyer.com',
    'https://lying-admin.hubbuyer.com'
  ];
  const outDir = path.join(process.cwd(), 'output', 'playwright', 'agent2_precheck');
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, ignoreHTTPSErrors: true });
  const page = await context.newPage();
  const results = [];
  for (const url of urls) {
    let status = null, title = '', finalUrl = '', error = '';
    try {
      const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
      status = resp ? resp.status() : null;
      await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(()=>{});
      title = await page.title();
      finalUrl = page.url();
    } catch (e) {
      error = e.message;
      finalUrl = page.url();
      title = await page.title().catch(()=> '');
    }
    results.push({ url, status, title, finalUrl, error });
  }

  const admin = { loginAttempted: false, loginSuccess: false, reason: '', screenshot: '', finalUrl: '', title: '', cookies: 0, storageKeys: [] };
  try {
    admin.loginAttempted = true;
    const resp = await page.goto('https://lying-admin.hubbuyer.com', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(()=>{});
    admin.title = await page.title();
    // Identify likely login controls.
    const info = await page.evaluate(() => {
      const inputs = [...document.querySelectorAll('input')].map((el, i) => ({
        i,
        type: el.type || '',
        name: el.getAttribute('name') || '',
        id: el.id || '',
        placeholder: el.getAttribute('placeholder') || '',
        autocomplete: el.getAttribute('autocomplete') || '',
        visible: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length)
      }));
      const buttons = [...document.querySelectorAll('button')].map((el, i) => ({i, text: (el.innerText||el.textContent||'').trim(), type: el.type || '', visible: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length)}));
      return {inputs, buttons, bodyText: document.body.innerText.slice(0,1000)};
    });

    const userSelectors = [
      'input[name="username"]','input[name="userName"]','input[name="account"]','input[name="email"]','input[id*="user" i]','input[placeholder*="账号"]','input[placeholder*="用户"]','input[placeholder*="邮箱"]','input[type="text"]'
    ];
    const passSelectors = ['input[type="password"]','input[name="password"]','input[placeholder*="密码"]'];
    async function firstVisible(selectors) {
      for (const s of selectors) {
        const loc = page.locator(s).filter({ hasNotText: '' }).first();
        try { if (await loc.count() && await loc.isVisible({timeout:1000})) return loc; } catch(e) {}
      }
      return null;
    }
    const user = await firstVisible(userSelectors);
    const pass = await firstVisible(passSelectors);
    if (!user || !pass) {
      admin.reason = '未找到可见账号/密码输入框；页面控件信息：' + JSON.stringify(info).slice(0,2000);
      const p = path.join(outDir, 'env_login_page.webp');
      await page.screenshot({ path: p, fullPage: true, type: 'webp', quality: 80 });
      admin.screenshot = p;
    } else {
      await user.click(); await user.fill('admin');
      await pass.click(); await pass.fill('123333');
      const before = page.url();
      const loginText = /登录|登 录|Login|Sign in|提交|确定/;
      let clicked = false;
      const btns = page.getByRole('button', { name: loginText });
      if (await btns.count()) { await btns.first().click(); clicked = true; }
      else {
        const submit = page.locator('button[type="submit"], input[type="submit"]').first();
        if (await submit.count()) { await submit.click(); clicked = true; }
        else { await pass.press('Enter'); clicked = true; }
      }
      await page.waitForLoadState('networkidle', { timeout: 20000 }).catch(()=>{});
      await page.waitForTimeout(3000);
      admin.finalUrl = page.url();
      admin.title = await page.title();
      const cookies = await context.cookies();
      admin.cookies = cookies.length;
      admin.storageKeys = await page.evaluate(() => Object.keys(localStorage).concat(Object.keys(sessionStorage).map(k=>'session:'+k))).catch(()=>[]);
      const body = await page.locator('body').innerText({timeout:5000}).catch(()=> '');
      const hasLoginForm = await page.locator('input[type="password"]').count().catch(()=>0);
      const hasError = /密码错误|账号.*错误|用户名.*错误|验证码|captcha|失败|invalid|error|Incorrect/i.test(body);
      admin.loginSuccess = (admin.finalUrl !== before || hasLoginForm === 0) && !hasError && (cookies.length > 0 || admin.storageKeys.length > 0);
      if (!admin.loginSuccess) {
        admin.reason = `登录后仍未确认有效会话。finalUrl=${admin.finalUrl}; hasPasswordInputs=${hasLoginForm}; cookies=${cookies.length}; storageKeys=${admin.storageKeys.length}; pageText=${body.slice(0,800)}`;
        const p = path.join(outDir, 'env_login_page.webp');
        await page.screenshot({ path: p, fullPage: true, type: 'webp', quality: 80 });
        admin.screenshot = p;
      } else {
        const p = path.join(outDir, 'env_precheck.webp');
        await page.screenshot({ path: p, fullPage: true, type: 'webp', quality: 80 });
        admin.screenshot = p;
      }
    }
  } catch (e) {
    admin.reason = e.stack || e.message;
    try {
      const p = path.join(outDir, 'env_login_page.webp');
      await page.screenshot({ path: p, fullPage: true, type: 'webp', quality: 80 });
      admin.screenshot = p;
    } catch (_) {}
  }
  console.log(JSON.stringify({ results, admin }, null, 2));
  await browser.close();
})();
