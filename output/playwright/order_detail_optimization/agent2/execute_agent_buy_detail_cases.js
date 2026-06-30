const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const OUT_DIR = 'D:/test_workspace/output/playwright/order_detail_optimization/agent2';
const ADMIN_URL = 'https://wlz-admin-all-view.hubbuyer.com';
const LOGIN_DATA_PY = 'D:/test_workspace/鍏ㄧ悆绔欏贰妫€鑴氭湰/hubbuyer/config/data/login_data.py';
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function scrubText(text) {
  if (!text) return '';
  return text
    .replace(/([A-Za-z0-9_-]*token[A-Za-z0-9_-]*\s*[:=]\s*)["']?[^"',\s}]+/gi, '$1<redacted>')
    .replace(/(password|pwd|瀵嗙爜)(\s*[:=]\s*)["']?[^"',\s}]+/gi, '$1$2<redacted>');
}

function getAdminCredential() {
  const text = fs.readFileSync(LOGIN_DATA_PY, 'utf8');
  const m = text.match(/"account"\s*:\s*"test-zhou"[\s\S]{0,100}?"password"\s*:\s*"([^"]+)"/);
  if (!m) throw new Error('Cannot locate test-zhou credential in login_data.py');
  return { account: 'test-zhou', password: <redacted-password> };
}

async function screenshot(page, name) {
  const safe = name.replace(/[^\w.-]+/g, '_');
  const p = path.join(OUT_DIR, `${safe}.png`);
  await page.screenshot({ path: p, fullPage: true }).catch(() => {});
  return p;
}

async function saveText(name, value) {
  const safe = name.replace(/[^\w.-]+/g, '_');
  const p = path.join(OUT_DIR, `${safe}.txt`);
  fs.writeFileSync(p, scrubText(value || ''), 'utf8');
  return p;
}

async function bodyText(page) {
  return await page.locator('body').innerText({ timeout: 8000 }).catch((e) => `BODY_ERROR ${e.message}`);
}

async function collectVisibleControls(page) {
  return await page.evaluate(() => Array.from(document.querySelectorAll('input, textarea, button, .el-select, .el-input, [role="button"], a'))
    .filter((el) => {
      const r = el.getBoundingClientRect();
      const style = window.getComputedStyle(el);
      return r.width > 0 && r.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
    })
    .slice(0, 260)
    .map((el, i) => ({
      i,
      tag: el.tagName,
      text: (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 100),
      placeholder: el.getAttribute('placeholder') || el.querySelector?.('input')?.getAttribute('placeholder') || '',
      type: el.getAttribute('type') || '',
      className: String(el.className || '').slice(0, 120)
    }))).catch((e) => [{ error: e.message }]);
}

async function collectTableRows(page) {
  return await page.evaluate(() => {
    const tables = Array.from(document.querySelectorAll('.el-table'));
    return tables.map((table, tableIndex) => {
      const headers = Array.from(table.querySelectorAll('.el-table__header-wrapper th, thead th'))
        .map((x) => (x.innerText || x.textContent || '').trim().replace(/\s+/g, ' '))
        .filter(Boolean);
      const rows = Array.from(table.querySelectorAll('.el-table__body-wrapper tbody tr, tbody tr')).slice(0, 30)
        .map((tr) => Array.from(tr.querySelectorAll('td')).map((td) => (td.innerText || td.textContent || '').trim().replace(/\s+/g, ' ')));
      return { tableIndex, headers, rows };
    });
  }).catch((e) => [{ error: e.message }]);
}

async function attachApiRecorder(page, bucket) {
  const handler = async (resp) => {
    const url = resp.url();
    if (!url.includes('wlz-api-all.test.hubbuyer.com')) return;
    const item = {
      method: resp.request().method(),
      url: url.replace(/([?&](?:token|loginToken|login_token|userlogintoken)=)[^&]+/gi, '$1<redacted>'),
      status: resp.status(),
      requestPost: scrubText(resp.request().postData() || '').slice(0, 1000)
    };
    try {
      const ct = resp.headers()['content-type'] || '';
      if (/json|text/i.test(ct)) {
        item.bodySnippet = scrubText(await resp.text()).slice(0, 1000);
      }
    } catch (_) {}
    bucket.push(item);
  };
  page.on('response', handler);
  return () => page.off('response', handler);
}

async function login(page) {
  const cred = getAdminCredential();
  await page.goto(`${ADMIN_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForSelector('input[placeholder="璇疯緭鍏ヨ处鍙?], input[type="text"]', { timeout: 15000 });
  await page.locator('input').nth(0).fill(cred.account);
  await page.locator('input').nth(1).fill(cred.password);
  await page.locator('button:has-text("鐧诲綍")').click();
  await page.waitForURL((url) => !url.pathname.endsWith('/login'), { timeout: 20000 }).catch(() => {});
  await page.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(1500);
}

async function clickTextIfVisible(page, text) {
  const locator = page.getByText(text, { exact: false }).first();
  if (await locator.isVisible().catch(() => false)) {
    await locator.click().catch(() => {});
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(1500);
    return true;
  }
  return false;
}

async function clickFirstDetail(page) {
  const detail = page.locator('button:has-text("璇︽儏")').first();
  if (!(await detail.isVisible().catch(() => false))) {
    throw new Error('No visible detail button on agent buy list');
  }
  await detail.click();
  await page.waitForLoadState('networkidle', { timeout: 25000 }).catch(() => {});
  await page.waitForTimeout(2500);
}

async function findFilterControls(page) {
  const text = await bodyText(page);
  return {
    hasProductId: /鍟嗗搧\s*ID|SKU|鍟嗗搧ID/i.test(text),
    hasProductStatus: /鍟嗗搧鐘舵€?.test(text),
    hasPurchaseStatus: /閲囪喘鐘舵€?.test(text),
    hasQcStatus: /璐ㄦ鐘舵€?.test(text),
    hasQueryButton: /鏌ヨ/.test(text),
    hasResetButton: /閲嶇疆/.test(text),
    hasOriginalProductInfo: /鍟嗗搧淇℃伅|閲囪喘淇℃伅|SKU|搴楅摵|涓嬪崟鏁皘璐叆鏁皘鍒拌揣鏁皘姝ｅ搧鏁皘鍏ュ簱鏁?.test(text),
    bodySnippet: scrubText(text).slice(0, 2500)
  };
}

async function openSelectNearLabel(page, labelText) {
  const result = { labelText, clicked: false, options: [] };
  const label = page.getByText(labelText, { exact: true }).first();
  if (!(await label.isVisible().catch(() => false))) return result;
  const handle = await label.elementHandle();
  if (!handle) return result;
  const selectHandle = await handle.evaluateHandle((node) => {
    const root = node.closest('.el-form-item') || node.parentElement;
    return root ? root.querySelector('.el-select, .el-select__wrapper, input') : null;
  });
  const el = selectHandle.asElement();
  if (!el) return result;
  await el.click().catch(() => {});
  await page.waitForTimeout(800);
  result.clicked = true;
  result.options = await page.evaluate(() => Array.from(document.querySelectorAll('.el-select-dropdown__item, .el-popper .el-select-dropdown__item'))
    .filter((el) => {
      const r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0;
    })
    .map((el) => (el.innerText || el.textContent || '').trim())
    .filter(Boolean));
  await page.keyboard.press('Escape').catch(() => {});
  return result;
}

async function executeDetailFilterSmoke(page, report) {
  report.detailInitial = {
    url: page.url(),
    screenshot: await screenshot(page, '01_detail_initial'),
    text: await saveText('01_detail_initial', await bodyText(page)),
    controls: await collectVisibleControls(page),
    tables: await collectTableRows(page),
    filterPresence: await findFilterControls(page)
  };

  const labels = ['鍟嗗搧鐘舵€?, '閲囪喘鐘舵€?, '璐ㄦ鐘舵€?];
  report.selectOptions = [];
  for (const label of labels) {
    report.selectOptions.push(await openSelectNearLabel(page, label));
  }
  report.afterDropdownScreenshot = await screenshot(page, '02_detail_dropdown_probe');

  const text = await bodyText(page);
  const skuMatch = text.match(/\b[A-Z0-9]+(?:-[A-Z0-9]+){2,}\b|\bSKU[-_A-Za-z0-9]+\b/i);
  const sku = skuMatch ? skuMatch[0] : '';
  report.skuCandidate = sku;

  if (sku) {
    const skuInput = page.locator('input[placeholder*="鍟嗗搧"], input[placeholder*="SKU"], input[placeholder*="ID"]').first();
    if (await skuInput.isVisible().catch(() => false)) {
      await skuInput.fill(sku);
      await page.locator('button:has-text("鏌ヨ")').first().click().catch(() => {});
      await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
      await page.waitForTimeout(1200);
      report.skuExact = {
        query: sku,
        screenshot: await screenshot(page, '03_detail_sku_exact'),
        text: await saveText('03_detail_sku_exact', await bodyText(page)),
        tables: await collectTableRows(page)
      };

      const partial = sku.length > 4 ? sku.slice(0, Math.max(3, Math.floor(sku.length / 2))) : `${sku}_partial`;
      await skuInput.fill(partial);
      await page.locator('button:has-text("鏌ヨ")').first().click().catch(() => {});
      await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
      await page.waitForTimeout(1200);
      report.skuPartial = {
        query: partial,
        screenshot: await screenshot(page, '04_detail_sku_partial'),
        text: await saveText('04_detail_sku_partial', await bodyText(page)),
        tables: await collectTableRows(page)
      };

      await skuInput.fill('<script>alert(1)</script>');
      await page.locator('button:has-text("鏌ヨ")').first().click().catch(() => {});
      await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
      await page.waitForTimeout(1200);
      report.skuScript = {
        query: '<script>alert(1)</script>',
        screenshot: await screenshot(page, '05_detail_sku_script'),
        text: await saveText('05_detail_sku_script', await bodyText(page)),
        dialogsTriggered: report.dialogsTriggered || [],
        tables: await collectTableRows(page)
      };

      await skuInput.fill('');
      await page.locator('button:has-text("閲嶇疆"), button:has-text("鏌ヨ")').first().click().catch(() => {});
      await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
      await page.waitForTimeout(1200);
      report.resetAfterSku = {
        screenshot: await screenshot(page, '06_detail_reset_after_sku'),
        text: await saveText('06_detail_reset_after_sku', await bodyText(page)),
        tables: await collectTableRows(page)
      };
    }
  }
}

async function main() {
  ensureDir(OUT_DIR);
  const report = {
    generatedAt: new Date().toISOString(),
    adminUrl: ADMIN_URL,
    accountUsed: 'test-zhou',
    apiEvents: [],
    dialogsTriggered: []
  };

  const browser = await chromium.launch({ headless: true, executablePath: CHROME });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, ignoreHTTPSErrors: true });
  const page = await context.newPage();
  page.on('dialog', async (dialog) => {
    report.dialogsTriggered.push({ type: dialog.type(), message: dialog.message() });
    await dialog.dismiss().catch(() => {});
  });
  const detach = await attachApiRecorder(page, report.apiEvents);

  await login(page);
  report.postLogin = {
    url: page.url(),
    screenshot: await screenshot(page, '10_post_login'),
    text: await saveText('10_post_login', await bodyText(page))
  };

  await page.goto(`${ADMIN_URL}/b2b/order/agentBuy`, { waitUntil: 'domcontentloaded', timeout: 40000 });
  await page.waitForLoadState('networkidle', { timeout: 25000 }).catch(() => {});
  await page.waitForTimeout(2000);
  report.listInitial = {
    url: page.url(),
    screenshot: await screenshot(page, '11_agent_buy_list_initial'),
    text: await saveText('11_agent_buy_list_initial', await bodyText(page)),
    controls: await collectVisibleControls(page),
    tables: await collectTableRows(page)
  };

  await clickTextIfVisible(page, '灞曞紑');
  report.listExpanded = {
    url: page.url(),
    screenshot: await screenshot(page, '12_agent_buy_list_expanded'),
    text: await saveText('12_agent_buy_list_expanded', await bodyText(page)),
    controls: await collectVisibleControls(page),
    hasAmountConfirmFilter: /閲戦鏄惁纭/.test(await bodyText(page)),
    tables: await collectTableRows(page)
  };

  await clickTextIfVisible(page, '杩涜涓?);
  report.listInProgress = {
    url: page.url(),
    screenshot: await screenshot(page, '13_agent_buy_list_in_progress'),
    text: await saveText('13_agent_buy_list_in_progress', await bodyText(page)),
    controls: await collectVisibleControls(page),
    tables: await collectTableRows(page)
  };

  await clickFirstDetail(page);
  await executeDetailFilterSmoke(page, report);

  await page.reload({ waitUntil: 'domcontentloaded', timeout: 40000 }).catch(() => {});
  await page.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(1200);
  report.detailAfterRefresh = {
    url: page.url(),
    screenshot: await screenshot(page, '07_detail_after_refresh'),
    text: await saveText('07_detail_after_refresh', await bodyText(page)),
    filterPresence: await findFilterControls(page)
  };

  await page.goto(`${ADMIN_URL}/b2b/order/agentBuy`, { waitUntil: 'domcontentloaded', timeout: 40000 }).catch(() => {});
  await page.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(1200);
  report.returnedList = {
    url: page.url(),
    screenshot: await screenshot(page, '14_returned_agent_buy_list'),
    text: await saveText('14_returned_agent_buy_list', await bodyText(page))
  };

  detach();
  fs.writeFileSync(path.join(OUT_DIR, 'execution_results.json'), JSON.stringify(report, null, 2), 'utf8');
  await context.close().catch(() => {});
  await browser.close().catch(() => {});

  console.log(JSON.stringify({
    accountUsed: report.accountUsed,
    listUrl: report.listInitial.url,
    hasAmountConfirmFilterAfterExpand: report.listExpanded.hasAmountConfirmFilter,
    detailUrl: report.detailInitial?.url,
    filterPresence: report.detailInitial?.filterPresence,
    selectOptions: report.selectOptions,
    skuCandidate: report.skuCandidate,
    artifact: path.join(OUT_DIR, 'execution_results.json')
  }, null, 2));
}

main().catch((e) => {
  console.error(e.stack || e.message || String(e));
  process.exit(1);
});

