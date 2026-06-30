const { chromium } = require('playwright');
(async()=>{
  const browser = await chromium.launch({headless:true});
  const page = await browser.newPage({viewport:{width:1366,height:900}});
  page.on('console', msg => console.log('CONSOLE', msg.type(), msg.text().slice(0,200)));
  page.on('response', r => { if (r.url().includes('login') || r.url().includes('auth')) console.log('RESP', r.status(), r.url()); });
  await page.goto('https://lying-admin.hubbuyer.com', {waitUntil:'networkidle', timeout:60000});
  console.log('TITLE', await page.title());
  console.log('URL', page.url());
  console.log('TEXT', (await page.locator('body').innerText({timeout:10000})).slice(0,1000));
  console.log('INPUTS', await page.locator('input').evaluateAll(els => els.map(e => ({type:e.type, placeholder:e.placeholder, name:e.name, id:e.id, autocomplete:e.autocomplete}))));
  await page.screenshot({path:'/mnt/d/test_workspace/会员体系/测试文档/执行报告/screenshots/env_precheck.webp', fullPage:true});
  await browser.close();
})().catch(e=>{ console.error(e); process.exit(1); });
