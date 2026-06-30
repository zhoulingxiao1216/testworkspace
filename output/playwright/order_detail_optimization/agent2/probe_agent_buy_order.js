const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const OUT_DIR = 'D:/test_workspace/output/playwright/order_detail_optimization/agent2';
const ADMIN_URL = 'https://wlz-admin-all-view.hubbuyer.com';
const ACCOUNT_MD = 'D:/test_workspace/娴嬭瘯鐜浣跨敤璐﹀彿.md';
const LOGIN_DATA_PY = 'D:/test_workspace/鍏ㄧ悆绔欏贰妫€鑴氭湰/hubbuyer/config/data/login_data.py';
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function scrubText(text) {
  if (!text) return '';
  return text
    .replace(/([A-Za-z0-9_-]*token[A-Za-z0-9_-]*\s*[:=]\s*)["']?[^"',\s}]+/gi, '$1<redacted>')
    .replace(/(password|pwd|瀵嗙爜)(\s*[:=]\s*)["']?[^"',\s}]+/gi, '$1$2<redacted>')
    .slice(0, 4000);
}

function parseMarkdownAccounts() {
  const out = [];
  const text = fs.existsSync(ACCOUNT_MD) ? fs.readFileSync(ACCOUNT_MD, 'utf8') : '';
  for (const line of text.split(/\r?\n/)) {
    const cols = line.split('|').map((s) => s.trim()).filter(Boolean);
    if (cols.length < 2) continue;
    if (['璐﹀彿', '娴嬭瘯闇€姹?, '鍦板尯'].includes(cols[0]) || cols[0].includes('---')) continue;
    const account = cols[0];
    const password = <redacted-password>
    const role = cols[2] || '';
    if (!account || !password || account.includes('脳') || password.includes('鍚庣画')) continue;
    if (password.length > 30) continue;
    out.push({ account, password, role: role || 'from 娴嬭瘯鐜浣跨敤璐﹀彿.md' });
  }
  return out;
}

function parsePythonLoginData() {
  const out = [];
  const text = fs.existsSync(LOGIN_DATA_PY) ? fs.readFileSync(LOGIN_DATA_PY, 'utf8') : '';
  const accountMatches = [...text.matchAll(/"account"\s*:\s*"([^"]+)"[\s\S]{0,80}?"password"\s*:\s*"([^"]+)"/g)];
  for (const m of accountMatches) {
    out.push({ account: m[1], password: <redacted-password>, role: 'from login_data.py' });
  }
  return out;
}

function uniqueCandidates() {
  const preferred = ['test-cgy', 'test-zhou', 'test-ywy', 'test-khjl', 'test-鍛?, 'piaoxuejin', 'admin'];
  const all = [...parseMarkdownAccounts(), ...parsePythonLoginData()]
    .filter((x) => x.account && x.password);
  all.sort((a, b) => {
    const ia = preferred.indexOf(a.account);
    const ib = preferred.indexOf(b.account);
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
  });
  const seen = new Set();
  return all.filter((x) => {
    const key = `${x.account}\n${x.password}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

async function savePageState(page, name) {
  const fileSafe = name.replace(/[^\w.-]+/g, '_');
  const screenshot = path.join(OUT_DIR, `${fileSafe}.png`);
  const htmlPath = path.join(OUT_DIR, `${fileSafe}.html`);
  const txtPath = path.join(OUT_DIR, `${fileSafe}.txt`);
  await page.screenshot({ path: screenshot, fullPage: true }).catch(() => {});
  const body = await page.locator('body').innerText({ timeout: 5000 }).catch((e) => `BODY_ERROR ${e.message}`);
  const html = await page.content().catch((e) => `HTML_ERROR ${e.message}`);
  fs.writeFileSync(txtPath, scrubText(body), 'utf8');
  fs.writeFileSync(htmlPath, scrubText(html), 'utf8');
  return { screenshot, txtPath, htmlPath, body: scrubText(body) };
}

async function loginWith(page, candidate) {
  await page.goto(`${ADMIN_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForSelector('input[placeholder="璇疯緭鍏ヨ处鍙?], input[type="text"]', { timeout: 15000 });
  const inputs = page.locator('input');
  await inputs.nth(0).fill(candidate.account);
  await inputs.nth(1).fill(candidate.password);
  await page.locator('button:has-text("鐧诲綍")').click();
  await Promise.race([
    page.waitForLoadState('networkidle', { timeout: 12000 }).catch(() => {}),
    page.waitForURL((url) => !url.pathname.endsWith('/login'), { timeout: 12000 }).catch(() => {})
  ]);
  await page.waitForTimeout(2000);
  const url = page.url();
  const body = await page.locator('body').innerText({ timeout: 5000 }).catch(() => '');
  const keys = await page.evaluate(() => Object.keys(window.localStorage || {})).catch(() => []);
  const stillLogin = /\/login(?:$|\?)/.test(url) || body.includes('璇疯緭鍏ユ偍鐨勫笎鎴蜂俊鎭櫥褰曠郴缁?);
  const hasLoginMarker = keys.some((k) => /token|user|admin|login/i.test(k)) || !stillLogin;
  return {
    account: candidate.account,
    role: candidate.role,
    success: Boolean(hasLoginMarker && !stillLogin),
    url,
    localStorageKeys: keys.filter((k) => /token|user|admin|login|permission|menu/i.test(k)),
    bodySnippet: scrubText(body).slice(0, 800)
  };
}

async function collectControls(page) {
  return await page.evaluate(() => {
    const controls = Array.from(document.querySelectorAll('input, textarea, button, .el-select, .el-input, [role="button"], a'))
      .slice(0, 200)
      .map((el, i) => ({
        i,
        tag: el.tagName,
        text: (el.innerText || el.textContent || '').trim().slice(0, 80),
        placeholder: el.getAttribute('placeholder') || el.querySelector?.('input')?.getAttribute('placeholder') || '',
        type: el.getAttribute('type') || '',
        aria: el.getAttribute('aria-label') || '',
        className: String(el.className || '').slice(0, 100)
      }));
    return controls;
  }).catch((e) => [{ error: e.message }]);
}

async function openRoute(page, routeName, routePath) {
  const apiEvents = [];
  const onResponse = async (resp) => {
    const url = resp.url();
    if (!url.includes('hubbuyer.com') || /\.(js|css|png|jpg|svg|ico|woff|map)(?:\?|$)/i.test(url)) return;
    const event = {
      url: url.replace(/([?&](?:token|loginToken|login_token|userlogintoken)=)[^&]+/gi, '$1<redacted>'),
      status: resp.status(),
      method: resp.request().method()
    };
    try {
      const ct = resp.headers()['content-type'] || '';
      if (/json|text/i.test(ct)) {
        const text = await resp.text();
        event.bodySnippet = scrubText(text).slice(0, 600);
      }
    } catch (_) {}
    apiEvents.push(event);
  };
  page.on('response', onResponse);
  await page.goto(`${ADMIN_URL}${routePath}`, { waitUntil: 'domcontentloaded', timeout: 40000 }).catch(() => {});
  await page.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(3000);
  page.off('response', onResponse);
  const state = await savePageState(page, `route_${routeName}`);
  const controls = await collectControls(page);
  return {
    routeName,
    routePath,
    finalUrl: page.url(),
    title: await page.title().catch(() => ''),
    bodySnippet: state.body.slice(0, 2000),
    artifacts: { screenshot: state.screenshot, txt: state.txtPath, html: state.htmlPath },
    controls,
    apiEvents
  };
}

async function main() {
  ensureDir(OUT_DIR);
  const results = {
    generatedAt: new Date().toISOString(),
    adminUrl: ADMIN_URL,
    candidatesTried: [],
    selectedAccount: null,
    routes: []
  };
  const browser = await chromium.launch({ headless: true, executablePath: CHROME });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    ignoreHTTPSErrors: true
  });
  const page = await context.newPage();
  await openRoute(page, 'login_initial', '/login').catch(() => {});

  for (const candidate of uniqueCandidates()) {
    const attemptPage = await context.newPage();
    const result = await loginWith(attemptPage, candidate).catch((e) => ({
      account: candidate.account,
      role: candidate.role,
      success: false,
      error: e.message
    }));
    results.candidatesTried.push({
      account: result.account,
      role: result.role,
      success: result.success,
      url: result.url,
      error: result.error,
      bodySnippet: result.bodySnippet
    });
    await savePageState(attemptPage, `login_attempt_${candidate.account}_${result.success ? 'success' : 'fail'}`).catch(() => {});
    if (result.success) {
      results.selectedAccount = {
        account: result.account,
        role: result.role,
        postLoginUrl: result.url,
        localStorageKeys: result.localStorageKeys
      };
      await page.close().catch(() => {});
      pageRef = attemptPage;
      break;
    }
    await attemptPage.close().catch(() => {});
  }

  const activePage = results.selectedAccount
    ? context.pages().find((p) => !p.isClosed() && !/\/login(?:$|\?)/.test(p.url())) || context.pages()[0]
    : null;

  if (activePage) {
    const routes = [
      ['admin_user_list', '/admin/user/list'],
      ['b2b_user_list', '/b2b/user/list'],
      ['agent_buy_list', '/b2b/order/agentBuy'],
      ['agent_buy_detail_plain', '/b2b/order/agentBuy/detail']
    ];
    for (const [name, routePath] of routes) {
      const routeResult = await openRoute(activePage, name, routePath).catch((e) => ({
        routeName: name,
        routePath,
        error: e.message
      }));
      results.routes.push(routeResult);
    }
  }

  fs.writeFileSync(path.join(OUT_DIR, 'probe_results.json'), JSON.stringify(results, null, 2), 'utf8');
  await context.close().catch(() => {});
  await browser.close().catch(() => {});
  console.log(JSON.stringify({
    selectedAccount: results.selectedAccount ? {
      account: results.selectedAccount.account,
      role: results.selectedAccount.role,
      postLoginUrl: results.selectedAccount.postLoginUrl
    } : null,
    candidatesTried: results.candidatesTried.map((x) => ({ account: x.account, role: x.role, success: x.success, url: x.url, error: x.error })),
    routes: results.routes.map((x) => ({ routeName: x.routeName, finalUrl: x.finalUrl, error: x.error, snippet: (x.bodySnippet || '').slice(0, 120) }))
  }, null, 2));
}

main().catch((e) => {
  console.error(e.stack || e.message || String(e));
  process.exit(1);
});

