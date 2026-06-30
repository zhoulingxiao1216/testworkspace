const fs = require('fs');
const { chromium } = require('playwright');

const OUT = 'D:/test_workspace/output/playwright/order_detail_optimization/agent2';
const ADMIN = 'https://wlz-admin-all-view.hubbuyer.com';
const LOGIN_DATA = 'D:/test_workspace/全球站巡检脚本/hubbuyer/config/data/login_data.py';
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';

const text = fs.readFileSync(LOGIN_DATA, 'utf8');
const pw = text.match(/"account"\s*:\s*"test-zhou"[\s\S]{0,100}?"password"\s*:\s*"([^"]+)"/)[1];

async function login(page) {
  await page.goto(`${ADMIN}/login`, { waitUntil: 'domcontentloaded' });
  await page.locator('input').nth(0).fill('test-zhou');
  await page.locator('input').nth(1).fill(pw);
  await page.locator('button:has-text("登录")').click();
  await page.waitForURL((u) => !u.pathname.endsWith('/login'), { timeout: 20000 }).catch(() => {});
  await page.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {});
}

(async () => {
  const orderNo = process.argv[2] || 'B2B-DD-KOR8-260519-145';
  const id = process.argv[3] || '406';
  const urls = [
    `/b2b/order/agentBuy/detail?order_no=${orderNo}`,
    `/b2b/order/agentBuy/detail?orderNo=${orderNo}`,
    `/b2b/order/agentBuy/detail?id=${id}`,
    `/b2b/order/agentBuy/detail?order_id=${id}`,
    `/b2b/order/agentBuy/detail?order_no=${orderNo}&id=${id}`,
    `/b2b/order/agentBuy/detail?order_no=${orderNo}&status=110`
  ];
  const browser = await chromium.launch({ headless: true, executablePath: CHROME });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 }, ignoreHTTPSErrors: true });
  const page = await ctx.newPage();
  await login(page);
  const results = [];
  for (let i = 0; i < urls.length; i++) {
    const api = [];
    const handler = async (resp) => {
      const url = resp.url();
      if (!url.includes('wlz-api-all.test.hubbuyer.com')) return;
      api.push({
        method: resp.request().method(),
        status: resp.status(),
        url,
        post: resp.request().postData() || '',
        body: await resp.text().catch(() => '')
      });
    };
    page.on('response', handler);
    await page.goto(`${ADMIN}${urls[i]}`, { waitUntil: 'domcontentloaded', timeout: 30000 }).catch(() => {});
    await page.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {});
    await page.waitForTimeout(2000);
    page.off('response', handler);
    const body = await page.locator('body').innerText({ timeout: 8000 }).catch((e) => e.message);
    const name = `variant_${i + 1}`;
    await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: true }).catch(() => {});
    fs.writeFileSync(`${OUT}/${name}.txt`, body, 'utf8');
    results.push({ variant: urls[i], finalUrl: page.url(), bodySnippet: body.slice(0, 1200), api: api.map((x) => ({ method: x.method, status: x.status, url: x.url, post: x.post.slice(0, 500), body: x.body.slice(0, 500) })) });
  }
  fs.writeFileSync(`${OUT}/detail_url_variants.json`, JSON.stringify(results, null, 2), 'utf8');
  console.log(JSON.stringify(results.map((x) => ({ variant: x.variant, finalUrl: x.finalUrl, snippet: x.bodySnippet.slice(0, 160), api: x.api.map((a) => a.url.split('hubbuyer.com')[1]) })), null, 2));
  await ctx.close();
  await browser.close();
})().catch((e) => {
  console.error(e.stack || e.message);
  process.exit(1);
});
