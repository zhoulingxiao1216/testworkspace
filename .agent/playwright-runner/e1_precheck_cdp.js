const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const http = require('http');

const chromePath = '/mnt/c/Program Files/Google/Chrome/Application/chrome.exe';
const profile = 'C:\\temp\\hermes-chrome-profile';
const outDir = '/mnt/d/test_workspace/会员体系/测试文档/执行报告/screenshots';
fs.mkdirSync(outDir, { recursive: true });

function sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }
function getJson(url){ return new Promise((resolve,reject)=>{
  http.get(url,res=>{ let data=''; res.on('data',d=>data+=d); res.on('end',()=>{try{resolve(JSON.parse(data))}catch(e){reject(e)}}); }).on('error',reject);
});}

(async () => {
  const args = [
    '--headless=new',
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    '--remote-debugging-port=9222',
    `--user-data-dir=${profile}`,
    'about:blank'
  ];
  const proc = spawn(chromePath, args, { detached: false, stdio: 'ignore' });
  try {
    let ok=false;
    for (let i=0;i<40;i++) {
      try { await getJson('http://127.0.0.1:9222/json/version'); ok=true; break; } catch(e) { await sleep(500); }
    }
    if (!ok) throw new Error('Chrome CDP port not ready');
    const browser = await chromium.connectOverCDP('http://127.0.0.1:9222');
    const context = browser.contexts()[0] || await browser.newContext({ viewport: { width: 1366, height: 768 } });
    const page = await context.newPage();
    const urls = [
      'https://lying-www.hubbuyer.com',
      'https://lying-www.hubbuyer.com/fee',
      'https://lying-b2b.hubbuyer.com',
      'https://lying-admin.hubbuyer.com'
    ];
    const results = [];
    for (const url of urls) {
      const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
      results.push({ url, status: resp ? resp.status() : null, title: await page.title(), finalUrl: page.url() });
    }
    await page.screenshot({ path: path.join(outDir, 'env_precheck.webp'), fullPage: true });
    await browser.close();
    console.log(JSON.stringify(results, null, 2));
  } finally {
    try { proc.kill(); } catch(e) {}
  }
})();
