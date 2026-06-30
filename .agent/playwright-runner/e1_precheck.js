const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const chromePath = '/mnt/c/Program Files/Google/Chrome/Application/chrome.exe';
const outDir = '/mnt/d/test_workspace/会员体系/测试文档/执行报告/screenshots';
fs.mkdirSync(outDir, { recursive: true });

(async () => {
  const browser = await chromium.launch({
    executablePath: chromePath,
    headless: true,
    args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
  });
  const page = await browser.newPage({ viewport: { width: 1366, height: 768 } });
  const urls = [
    'https://lying-www.hubbuyer.com',
    'https://lying-www.hubbuyer.com/fee',
    'https://lying-b2b.hubbuyer.com',
    'https://lying-admin.hubbuyer.com'
  ];
  const results = [];
  for (const url of urls) {
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    results.push({ url, status: resp ? resp.status() : null, title: await page.title() });
  }
  await page.screenshot({ path: path.join(outDir, 'env_precheck.webp'), fullPage: true });
  await browser.close();
  console.log(JSON.stringify(results, null, 2));
})();
