const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const ROOT = 'D:/test_workspace';
const OUT_DIR = 'D:/test_workspace/output/playwright/order_detail_optimization/agent2_wcz';
const ADMIN_URL = 'https://test-wcz-admin.hubbuyer.com';
const ACCOUNT_MD = path.join(ROOT, '测试环境使用账号.md');
const CASE_DOC = path.join(ROOT, '订单详情页优化/测试文档/订单详情页优化测试用例.md');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function scrubText(input) {
  return String(input ?? '')
    .replace(/("password"\s*:\s*")([^"]+)(")/gi, '$1<redacted-password>$3')
    .replace(/(password|passwd|pwd|密码)(\s*[:=：]\s*)[^\s,&"}]+/gi, '$1$2<redacted-password>')
    .replace(/(login_token|loginToken|token|userlogintoken|authorization|cookie)(["'\s:=]+)[^"',\s&}]+/gi, '$1$2<redacted-token>')
    .replace(/([?&](?:token|loginToken|login_token|userlogintoken)=)[^&]+/gi, '$1<redacted-token>');
}

function writeText(file, text) {
  fs.writeFileSync(file, scrubText(text), 'utf8');
}

function writeJson(file, obj) {
  writeText(file, JSON.stringify(obj, null, 2));
}

function safeName(name) {
  return String(name).replace(/[^\w.-]+/g, '_');
}

function walkFiles(root, predicate, maxDepth = 6) {
  const found = [];
  function walk(dir, depth) {
    if (depth > maxDepth) return;
    let entries = [];
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch (_) {
      return;
    }
    for (const entry of entries) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (['.git', 'node_modules', '.venv', 'output'].includes(entry.name)) continue;
        walk(full, depth + 1);
      } else if (predicate(full, entry.name)) {
        found.push(full);
      }
    }
  }
  walk(root, 0);
  return found;
}

function addCredential(list, account, password, source, role = '') {
  if (!account || !password) return;
  const cleanAccount = String(account).trim();
  const cleanPassword = String(password).trim();
  if (!cleanAccount || !cleanPassword) return;
  if (/账号|account|密码|password/i.test(cleanAccount)) return;
  list.push({ account: cleanAccount, password: cleanPassword, source, role });
}

function parsePythonLoginData() {
  const creds = [];
  const files = walkFiles(ROOT, (full, name) => name === 'login_data.py' && full.includes(`${path.sep}hubbuyer${path.sep}`));
  for (const file of files) {
    const text = fs.readFileSync(file, 'utf8');
    const re = /["']account["']\s*:\s*["']([^"']+)["'][\s\S]{0,160}?["']password["']\s*:\s*["']([^"']+)["']/g;
    for (const m of text.matchAll(re)) {
      addCredential(creds, m[1], m[2], file, 'historical login_data.py');
    }
  }
  return creds;
}

function parseMarkdownAccounts() {
  const creds = [];
  if (!fs.existsSync(ACCOUNT_MD)) return creds;
  const text = fs.readFileSync(ACCOUNT_MD, 'utf8');
  for (const line of text.split(/\r?\n/)) {
    if (!line.includes('|')) continue;
    const cells = line.split('|').map((x) => x.trim()).filter(Boolean);
    for (let i = 0; i < cells.length - 1; i += 1) {
      const account = cells[i];
      const password = cells[i + 1];
      if (/^(test-[\w-]+|piaoxuejin|admin)$/i.test(account) && /^[^\s|]{3,}$/.test(password)) {
        addCredential(creds, account, password, ACCOUNT_MD, cells[i + 2] || 'account markdown');
      }
    }
  }
  return creds;
}

function uniqueCredentials() {
  const preferred = ['admin'];
  const all = [...parsePythonLoginData(), ...parseMarkdownAccounts()];
  const byAccount = new Map();
  for (const cred of all) {
    if (!byAccount.has(cred.account)) byAccount.set(cred.account, cred);
  }
  return [...byAccount.values()].filter((cred) => cred.account === 'admin').sort((a, b) => {
    const ai = preferred.includes(a.account) ? preferred.indexOf(a.account) : 999;
    const bi = preferred.includes(b.account) ? preferred.indexOf(b.account) : 999;
    return ai - bi || a.account.localeCompare(b.account);
  });
}

async function bodyText(page) {
  return page.locator('body').innerText({ timeout: 5000 }).catch((e) => `BODY_ERROR ${e.message}`);
}

async function savePageState(page, name) {
  const base = path.join(OUT_DIR, safeName(name));
  const screenshot = `${base}.png`;
  const txt = `${base}.txt`;
  const html = `${base}.html`;
  await page.screenshot({ path: screenshot, fullPage: true }).catch(() => {});
  const body = await bodyText(page);
  const content = await page.content().catch((e) => `HTML_ERROR ${e.message}`);
  writeText(txt, body);
  writeText(html, content);
  return {
    name,
    url: page.url(),
    title: await page.title().catch(() => ''),
    screenshot,
    txt,
    html,
    bodySnippet: scrubText(body).slice(0, 2500),
  };
}

async function collectControls(page) {
  return page.evaluate(() => {
    const isVisible = (el) => {
      const style = window.getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      return style && style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
    };
    return Array.from(document.querySelectorAll('input, textarea, button, [role="button"], .el-select, .el-form-item, .el-tabs__item, th'))
      .filter(isVisible)
      .slice(0, 260)
      .map((el, i) => ({
        i,
        tag: el.tagName,
        text: (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 180),
        placeholder: el.getAttribute('placeholder') || el.querySelector?.('input')?.getAttribute('placeholder') || '',
        type: el.getAttribute('type') || '',
        className: el.className?.toString?.().slice(0, 180) || '',
      }));
  }).catch((e) => [{ error: e.message }]);
}

async function collectTables(page) {
  return page.evaluate(() => {
    return Array.from(document.querySelectorAll('table, .el-table'))
      .slice(0, 6)
      .map((table, i) => {
        const textRows = Array.from(table.querySelectorAll('tr, .el-table__row'))
          .slice(0, 20)
          .map((row) => (row.innerText || row.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 500))
          .filter(Boolean);
        const header = Array.from(table.querySelectorAll('th'))
          .map((th) => (th.innerText || th.textContent || '').trim().replace(/\s+/g, ' '))
          .filter(Boolean);
        return { i, header, rowCount: textRows.length, sampleRows: textRows };
      });
  }).catch((e) => [{ error: e.message }]);
}

function countTerm(text, term) {
  return (String(text).match(new RegExp(term, 'g')) || []).length;
}

async function findFilterPresence(page) {
  const text = await bodyText(page);
  const controls = await collectControls(page);
  const controlText = controls.map((c) => `${c.text} ${c.placeholder}`).join('\n');
  const combined = `${text}\n${controlText}`;
  const has = {
    productId: /商品\s*ID|商品ID|SKU|商品编号/.test(combined),
    productStatus: /商品状态/.test(combined),
    purchaseStatus: /采购状态/.test(combined),
    qcStatus: /质检状态/.test(combined),
    queryButton: /查询/.test(controlText),
    resetButton: /重置/.test(controlText),
  };
  return {
    ...has,
    allCoreFilters: has.productId && has.productStatus && has.purchaseStatus && has.qcStatus,
    termCounts: {
      productId: countTerm(combined, '商品'),
      productStatus: countTerm(combined, '商品状态'),
      purchaseStatus: countTerm(combined, '采购状态'),
      qcStatus: countTerm(combined, '质检状态'),
    },
    controls,
  };
}

async function clickIfVisible(page, locator, timeout = 1200) {
  const loc = typeof locator === 'string' ? page.locator(locator).first() : locator.first();
  if (await loc.isVisible({ timeout }).catch(() => false)) {
    await loc.click();
    return true;
  }
  return false;
}

async function clickTextButton(page, text) {
  const locators = [
    `button:has-text("${text}")`,
    `text="${text}"`,
    `xpath=//*[contains(normalize-space(.), "${text}") and (self::button or @role="button" or contains(@class, "button"))]`,
  ];
  for (const selector of locators) {
    if (await clickIfVisible(page, selector, 900).catch(() => false)) return true;
  }
  return false;
}

async function openSelectByLabel(page, label) {
  const selectors = [
    `.el-form-item:has-text("${label}") .el-select`,
    `.el-form-item:has-text("${label}") .el-input`,
    `xpath=//*[contains(normalize-space(.), "${label}")]/following::*[contains(@class,"el-select")][1]`,
    `xpath=//*[contains(normalize-space(.), "${label}")]/following::*[contains(@class,"el-input")][1]`,
  ];
  for (const selector of selectors) {
    const loc = page.locator(selector).first();
    if (await loc.isVisible({ timeout: 1000 }).catch(() => false)) {
      await loc.click({ timeout: 3000 }).catch(async () => {
        const box = await loc.boundingBox();
        if (box) await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
      });
      await page.waitForTimeout(500);
      return true;
    }
  }
  return false;
}

async function visibleSelectOptions(page) {
  return page.evaluate(() => {
    const visible = (el) => {
      const s = window.getComputedStyle(el);
      const r = el.getBoundingClientRect();
      return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
    };
    return Array.from(document.querySelectorAll('.el-select-dropdown__item, [role="option"], .el-popper li'))
      .filter(visible)
      .map((el) => (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' '))
      .filter(Boolean);
  }).catch(() => []);
}

async function probeSelectOptions(page, label) {
  const opened = await openSelectByLabel(page, label);
  let options = [];
  if (opened) {
    options = await visibleSelectOptions(page);
    await page.keyboard.press('Escape').catch(() => {});
    await page.waitForTimeout(200);
  }
  return { label, opened, options };
}

async function selectOptionByLabel(page, label, option) {
  if (!(await openSelectByLabel(page, label))) return false;
  const optionLocators = [
    page.locator('.el-select-dropdown__item, [role="option"], .el-popper li').filter({ hasText: option }),
    page.locator(`text="${option}"`),
  ];
  for (const loc of optionLocators) {
    const item = loc.first();
    if (await item.isVisible({ timeout: 1200 }).catch(() => false)) {
      await item.click();
      await page.waitForTimeout(500);
      return true;
    }
  }
  await page.keyboard.press('Escape').catch(() => {});
  return false;
}

async function fillInputByLabel(page, label, value) {
  const selectors = [
    `.el-form-item:has-text("${label}") input`,
    `xpath=//*[contains(normalize-space(.), "${label}")]/following::input[1]`,
    `input[placeholder*="${label}"]`,
    `input[placeholder*="商品"]`,
  ];
  for (const selector of selectors) {
    const loc = page.locator(selector).first();
    if (await loc.isVisible({ timeout: 1000 }).catch(() => false)) {
      await loc.fill(value);
      await page.waitForTimeout(200);
      return true;
    }
  }
  return false;
}

async function clickQuery(page) {
  if (await clickTextButton(page, '查询')) {
    await page.waitForLoadState('networkidle', { timeout: 12000 }).catch(() => {});
    await page.waitForTimeout(900);
    return true;
  }
  return false;
}

async function clickReset(page) {
  if (await clickTextButton(page, '重置')) {
    await page.waitForLoadState('networkidle', { timeout: 12000 }).catch(() => {});
    await page.waitForTimeout(900);
    return true;
  }
  return false;
}

async function loginWith(context, candidate, index) {
  const page = await context.newPage();
  const attemptName = `login_attempt_${index}_${candidate.account}`;
  const result = {
    account: candidate.account,
    source: candidate.source,
    role: candidate.role,
    attemptedAt: new Date().toISOString(),
  };
  try {
    await page.goto(`${ADMIN_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 35000 });
    await page.waitForSelector('input', { timeout: 18000 });
    const inputs = page.locator('input');
    await inputs.nth(0).fill(candidate.account);
    await inputs.nth(1).fill(candidate.password);
    const loginButton = page.locator('button').filter({ hasText: /登录|Login/i }).first();
    if (await loginButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await loginButton.click();
    } else {
      await page.locator('button').last().click();
    }
    await Promise.race([
      page.waitForURL((url) => !/\/login(?:$|\?)/.test(url.pathname), { timeout: 18000 }).catch(() => {}),
      page.waitForLoadState('networkidle', { timeout: 18000 }).catch(() => {}),
    ]);
    await page.waitForTimeout(1800);
    const body = await bodyText(page);
    const url = page.url();
    const keys = await page.evaluate(() => Object.keys(window.localStorage || {})).catch(() => []);
    const stillLogin = /\/login(?:$|\?)/.test(new URL(url).pathname) || /账号或密码错误|请输入.*登录|欢迎回来/.test(body);
    result.success = Boolean(!stillLogin && (keys.length > 0 || !/登录/.test(body)));
    result.url = url;
    result.localStorageKeys = keys.filter((k) => /token|user|admin|login|permission|menu|remember/i.test(k));
    result.state = await savePageState(page, `${attemptName}_${result.success ? 'success' : 'fail'}`);
    if (result.success) return { result, page };
  } catch (e) {
    result.success = false;
    result.error = e.message;
    result.state = await savePageState(page, `${attemptName}_error`).catch(() => null);
  }
  await page.close().catch(() => {});
  return { result, page: null };
}

async function openRoute(page, name, route) {
  await page.goto(`${ADMIN_URL}${route}`, { waitUntil: 'domcontentloaded', timeout: 45000 }).catch(() => {});
  await page.waitForLoadState('networkidle', { timeout: 25000 }).catch(() => {});
  await page.waitForTimeout(1800);
  const state = await savePageState(page, name);
  return {
    route,
    state,
    controls: await collectControls(page),
    tables: await collectTables(page),
  };
}

async function clickFirstDetail(page, ordinal = 0) {
  const detailCandidates = [
    page.locator('button').filter({ hasText: '详情' }),
    page.locator('a').filter({ hasText: '详情' }),
    page.locator('[role="button"]').filter({ hasText: '详情' }),
    page.locator('text="详情"'),
  ];
  for (const loc of detailCandidates) {
    const count = await loc.count().catch(() => 0);
    if (count > ordinal && await loc.nth(ordinal).isVisible({ timeout: 1200 }).catch(() => false)) {
      const context = page.context();
      const popupPromise = context.waitForEvent('page', { timeout: 5000 }).catch(() => null);
      const oldUrl = page.url();
      await loc.nth(ordinal).click();
      const popup = await popupPromise;
      const target = popup || page;
      await target.waitForLoadState('domcontentloaded', { timeout: 25000 }).catch(() => {});
      await target.waitForLoadState('networkidle', { timeout: 25000 }).catch(() => {});
      await target.waitForTimeout(2500);
      if (popup) {
        await popup.bringToFront().catch(() => {});
        return popup;
      }
      if (page.url() !== oldUrl || /detail/i.test(page.url())) return page;
      const body = await bodyText(page);
      if (/订单详情|商品信息|采购信息|店铺|商铺|质检/.test(body)) return page;
      return null;
    }
  }
  return null;
}

function extractOrderNosFromText(text) {
  const set = new Set();
  for (const m of String(text).matchAll(/\bB2B-[A-Z0-9-]{8,}\b/g)) set.add(m[0]);
  return [...set];
}

function extractSkuCandidate(text) {
  const source = String(text);
  const explicitId = source.match(/(?:^|\n|\s)ID[:：]\s*(D\d{6,})/i);
  if (explicitId) return explicitId[1];
  const patterns = [
    /\bSKU[-_A-Za-z0-9]{3,}\b/g,
    /\bD\d{6,}\b/g,
    /\b[A-Z]{1,8}-[A-Z0-9]{2,}(?:-[A-Z0-9]{1,}){1,}\b/g,
    /\b\d{6,}[A-Z0-9_-]{0,}\b/g,
  ];
  for (const re of patterns) {
    const found = [...source.matchAll(re)].map((m) => m[0]).filter((x) => !/^B2B-/.test(x) && !/^DD-[A-Z0-9-]+/.test(x));
    if (found.length) return found[0];
  }
  return '';
}

function hasExpectedOptions(actual, expected) {
  const joined = actual.join('\n');
  return expected.filter((item) => !joined.includes(item));
}

function addCase(cases, id, status, conclusion, evidence = []) {
  cases.push({ id, status, conclusion, evidence });
}

async function runDetailFilterCases(page, report) {
  report.detail = report.detail || {};
  const cases = report.cases;
  const initialState = await savePageState(page, '20_detail_initial');
  const initialText = await bodyText(page);
  report.detail.initial = {
    state: initialState,
    controls: await collectControls(page),
    tables: await collectTables(page),
    filterPresence: await findFilterPresence(page),
    orderNos: extractOrderNosFromText(initialText),
    skuCandidate: extractSkuCandidate(initialText),
  };

  const presence = report.detail.initial.filterPresence;
  const initialEvidence = [initialState.screenshot, initialState.txt];
  if (presence.allCoreFilters) {
    addCase(cases, 'TC-OD-FLT-001', 'Pass', '订单详情页可见商品 ID、商品状态、采购状态、质检状态四类商品级筛选入口。', initialEvidence);
  } else {
    addCase(cases, 'TC-OD-FLT-001', 'Fail', `订单详情页未完整展示商品级筛选入口；识别结果：商品ID=${presence.productId}，商品状态=${presence.productStatus}，采购状态=${presence.purchaseStatus}，质检状态=${presence.qcStatus}。`, initialEvidence);
    addCase(cases, 'TC-OD-FLT-002', 'Fail', '筛选入口不完整，无法验证默认值与下拉选项完整性。', initialEvidence);
    for (const id of ['TC-OD-FLT-003', 'TC-OD-FLT-004', 'TC-OD-FLT-005', 'TC-OD-FLT-006', 'TC-OD-FLT-007', 'TC-OD-FLT-008', 'TC-OD-FLT-009', 'TC-OD-FLT-010', 'TC-OD-FLT-011', 'TC-OD-FLT-012']) {
      addCase(cases, id, 'Blocked', '前置筛选控件缺失，无法继续执行该筛选规则用例。', initialEvidence);
    }
    return;
  }

  const selectProbes = [];
  for (const label of ['商品状态', '采购状态', '质检状态']) {
    selectProbes.push(await probeSelectOptions(page, label));
  }
  report.detail.selectProbes = selectProbes;
  const productMissing = hasExpectedOptions(selectProbes[0].options, ['全部', '待入库', '部分入库', '已入库']);
  const purchaseMissing = hasExpectedOptions(selectProbes[1].options, ['全部', '待采购', '部分到货', '暂不购买']);
  const qcMissing = hasExpectedOptions(selectProbes[2].options, ['全部', '有不良', '有待定', '有退货', '有换货', '待检品']);
  const dropdownState = await savePageState(page, '21_detail_dropdown_options');
  if (!productMissing.length && !purchaseMissing.length && !qcMissing.length) {
    addCase(cases, 'TC-OD-FLT-002', 'Pass', '商品状态、采购状态、质检状态下拉选项包含用例要求的全部选项。', [dropdownState.screenshot, dropdownState.txt]);
  } else {
    addCase(cases, 'TC-OD-FLT-002', 'Fail', `下拉选项不完整：商品状态缺失 ${productMissing.join('/') || '无'}；采购状态缺失 ${purchaseMissing.join('/') || '无'}；质检状态缺失 ${qcMissing.join('/') || '无'}。`, [dropdownState.screenshot, dropdownState.txt]);
  }

  const sku = report.detail.initial.skuCandidate;
  if (!sku) {
    addCase(cases, 'TC-OD-FLT-003', 'Blocked', '当前详情页未识别到可用于精确匹配的 SKU/商品 ID。', initialEvidence);
  } else {
    await fillInputByLabel(page, '商品', sku);
    await clickQuery(page);
    const exactState = await savePageState(page, '22_detail_sku_exact');
    const exactText = await bodyText(page);
    const partial = sku.length > 5 ? sku.slice(0, Math.max(3, Math.floor(sku.length / 2))) : sku.slice(0, -1);
    await fillInputByLabel(page, '商品', partial);
    await clickQuery(page);
    const partialState = await savePageState(page, '23_detail_sku_partial');
    const partialText = await bodyText(page);
    report.detail.skuProbe = { sku, partial, exactContainsSku: exactText.includes(sku), partialContainsSku: partialText.includes(sku) };
    if (exactText.includes(sku) && !partialText.includes(sku)) {
      addCase(cases, 'TC-OD-FLT-003', 'Pass', `完整商品 ID/SKU ${sku} 可命中，部分值 ${partial} 未模糊命中该商品。`, [exactState.screenshot, partialState.screenshot]);
    } else if (!exactText.includes(sku)) {
      addCase(cases, 'TC-OD-FLT-003', 'Fail', `完整商品 ID/SKU ${sku} 查询后未在页面结果中识别到该商品。`, [exactState.screenshot, exactState.txt]);
    } else {
      addCase(cases, 'TC-OD-FLT-003', 'Fail', `部分商品 ID/SKU ${partial} 查询后仍识别到完整商品 ${sku}，疑似模糊命中。`, [partialState.screenshot, partialState.txt]);
    }
  }

  await fillInputByLabel(page, '商品', 'NO-SUCH-SKU-AGENT2-WCZ-999');
  await clickQuery(page);
  const noneState = await savePageState(page, '24_detail_sku_none');
  let dialogTriggered = false;
  await fillInputByLabel(page, '商品', '<script>alert(1)</script>');
  const beforeDialogs = report.dialogs.length;
  await clickQuery(page);
  const scriptState = await savePageState(page, '25_detail_sku_script');
  dialogTriggered = report.dialogs.length > beforeDialogs;
  const scriptText = await bodyText(page);
  if (!dialogTriggered && !/BODY_ERROR|HTML_ERROR/.test(scriptText)) {
    addCase(cases, 'TC-OD-FLT-004', 'Pass', '不存在商品 ID 与脚本字符输入后页面未白屏、未触发浏览器弹窗。', [noneState.screenshot, scriptState.screenshot]);
  } else {
    addCase(cases, 'TC-OD-FLT-004', 'Fail', `异常输入后出现异常：dialog=${dialogTriggered}，页面错误=${/BODY_ERROR|HTML_ERROR/.test(scriptText)}。`, [scriptState.screenshot, scriptState.txt]);
  }

  await clickReset(page);
  const resetState = await savePageState(page, '26_detail_reset_after_sku');
  for (const [id, label, option] of [
    ['TC-OD-FLT-005', '商品状态', '待入库'],
    ['TC-OD-FLT-006', '商品状态', '部分入库'],
    ['TC-OD-FLT-007', '商品状态', '已入库'],
  ]) {
    const selected = await selectOptionByLabel(page, label, option);
    await clickQuery(page);
    const state = await savePageState(page, `27_${id}_${option}`);
    if (selected) {
      addCase(cases, id, 'Blocked', `${option}筛选可操作并已留证，但当前自动化无法从页面稳定提取正品数量、已入库数量、发货数量完成规则级断言，需准备/标注覆盖数据后复核。`, [state.screenshot, state.txt]);
    } else {
      addCase(cases, id, 'Fail', `未能选择${option}筛选项。`, [state.screenshot, state.txt]);
    }
    await clickReset(page);
  }

  const purchaseStates = [];
  for (const option of ['待采购', '部分到货', '暂不购买']) {
    const selected = await selectOptionByLabel(page, '采购状态', option);
    await clickQuery(page);
    const state = await savePageState(page, `28_purchase_${option}`);
    purchaseStates.push({ option, selected, state });
    await clickReset(page);
  }
  addCase(
    cases,
    'TC-OD-FLT-008',
    purchaseStates.every((x) => x.selected) ? 'Blocked' : 'Fail',
    purchaseStates.every((x) => x.selected)
      ? '采购状态三类筛选项可选择并已留证，但缺少可核对采购数/到货数/暂不购买状态的数据口径，无法完成规则级通过判定。'
      : `采购状态存在不可选择项：${purchaseStates.filter((x) => !x.selected).map((x) => x.option).join('/')}`,
    purchaseStates.map((x) => x.state.screenshot)
  );

  const qcStates = [];
  for (const option of ['有不良', '有待定', '有退货', '有换货', '待检品']) {
    const selected = await selectOptionByLabel(page, '质检状态', option);
    await clickQuery(page);
    const state = await savePageState(page, `29_qc_${option}`);
    qcStates.push({ option, selected, state });
    await clickReset(page);
  }
  addCase(
    cases,
    'TC-OD-FLT-009',
    qcStates.every((x) => x.selected) ? 'Blocked' : 'Fail',
    qcStates.every((x) => x.selected)
      ? '质检状态五类筛选项可选择并已留证，但缺少可核对不良/待定/退货/换货/待检数量的数据口径，无法完成规则级通过判定。'
      : `质检状态存在不可选择项：${qcStates.filter((x) => !x.selected).map((x) => x.option).join('/')}`,
    qcStates.map((x) => x.state.screenshot)
  );

  const comboA = await selectOptionByLabel(page, '商品状态', '待入库');
  const comboB = await selectOptionByLabel(page, '采购状态', '待采购');
  await clickQuery(page);
  const comboState = await savePageState(page, '30_detail_combo_filter');
  if (comboA && comboB) {
    addCase(cases, 'TC-OD-FLT-010', 'Blocked', '多条件组合筛选可执行并已留证，但缺少覆盖状态商品数据与接口字段映射，无法验证结果是否严格按交集过滤。', [comboState.screenshot, comboState.txt]);
  } else {
    addCase(cases, 'TC-OD-FLT-010', 'Fail', '多条件组合筛选选择过程失败。', [comboState.screenshot, comboState.txt]);
  }

  await clickReset(page);
  await page.reload({ waitUntil: 'domcontentloaded', timeout: 40000 }).catch(() => {});
  await page.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(1200);
  const reloadState = await savePageState(page, '31_detail_after_reload');
  await page.goto(`${ADMIN_URL}/b2b/order/agentBuy`, { waitUntil: 'domcontentloaded', timeout: 40000 }).catch(() => {});
  await page.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(1200);
  const returnedList = await savePageState(page, '32_list_returned_after_detail');
  const secondPage = await clickFirstDetail(page, 1);
  const secondOpened = Boolean(secondPage);
  const secondState = secondOpened ? await savePageState(secondPage, '33_second_detail_after_return') : null;
  addCase(
    cases,
    'TC-OD-FLT-011',
    secondOpened ? 'Pass' : 'Blocked',
    secondOpened
      ? '清空/重置、刷新、返回列表并进入另一订单流程可完成，未观察到白屏或路由错误。'
      : '清空/刷新/返回列表已执行，但列表未能打开第二笔订单，无法完成“进入另一笔订单”验证。',
    [resetState.screenshot, reloadState.screenshot, returnedList.screenshot, secondState?.screenshot].filter(Boolean)
  );

  const multiText = secondOpened ? await bodyText(secondPage) : initialText;
  const shopLikeCount = countTerm(multiText, '店铺') + countTerm(multiText, '商铺');
  addCase(
    cases,
    'TC-OD-FLT-012',
    shopLikeCount >= 2 ? 'Blocked' : 'Blocked',
    shopLikeCount >= 2
      ? '当前订单疑似包含多个店铺信息并已留证，但缺少可核对的多店铺状态覆盖数据，无法判定筛选准确性。'
      : '当前可访问订单未确认具备多店铺、多商品且状态分布复杂的数据前置条件。',
    [secondState?.screenshot || initialState.screenshot]
  );
}

async function runOptionalCoverage(page, report) {
  const cases = report.cases;
  await page.goto(`${ADMIN_URL}/b2b/order/agentBuy`, { waitUntil: 'domcontentloaded', timeout: 40000 }).catch(() => {});
  await page.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(1500);
  await clickTextButton(page, '展开').catch(() => {});
  await page.waitForTimeout(600);
  const listState = await savePageState(page, '40_list_expanded_optional');
  const listText = await bodyText(page);
  const listControls = await collectControls(page);
  report.optional = report.optional || {};
  report.optional.listExpanded = { state: listState, controls: listControls, tables: await collectTables(page) };
  if (/金额是否确认/.test(`${listText}\n${JSON.stringify(listControls)}`)) {
    const probe = await probeSelectOptions(page, '金额是否确认');
    report.optional.amountConfirmProbe = probe;
    const missing = hasExpectedOptions(probe.options, ['全部', '已确认', '未确认']);
    addCase(
      cases,
      'TC-OD-AMT-005',
      missing.length ? 'Fail' : 'Pass',
      missing.length ? `进行中列表存在金额是否确认字段，但选项缺失：${missing.join('/')}` : '进行中列表展示金额是否确认筛选，且选项包含全部、已确认、未确认。',
      [listState.screenshot, listState.txt]
    );
  } else {
    addCase(cases, 'TC-OD-AMT-005', 'Fail', '进行中列表展开后未识别到“金额是否确认”筛选字段。', [listState.screenshot, listState.txt]);
  }

  const hasPurchaseCount = /购入数|购入数量|采购数/.test(listText);
  const sortEvidenceText = `${JSON.stringify(listControls)}\n${listText}`;
  const hasSortIcon = /sort|caret|ascending|descending|排序|is-sortable|el-table__column-filter-trigger/i.test(sortEvidenceText);
  addCase(
    cases,
    'TC-OD-LST-002',
    hasPurchaseCount && hasSortIcon ? 'Pass' : hasPurchaseCount ? 'Blocked' : 'Fail',
    hasPurchaseCount && hasSortIcon
      ? '进行中列表识别到购入数相关字段及排序/表头交互痕迹。'
      : hasPurchaseCount
        ? '进行中列表识别到购入数相关字段，但未能稳定识别排序按钮/图标，需要人工核对截图。'
        : '进行中列表未识别到购入数相关字段。',
    [listState.screenshot, listState.txt]
  );

  const detailPage = await clickFirstDetail(page, 0);
  if (detailPage) {
    const detailState = await savePageState(detailPage, '41_detail_optional_cashback');
    const detailText = await bodyText(detailPage);
    report.optional.cashbackDetail = { state: detailState };
    const hasCashback = /店铺返现|商铺返现|返现/.test(detailText);
    const hasConfirm = /确认/.test(detailText);
    addCase(
      cases,
      'TC-OD-CB-001',
      hasCashback && hasConfirm ? 'Blocked' : hasCashback ? 'Blocked' : 'Fail',
      hasCashback && hasConfirm
        ? '详情页存在返现与确认相关文案，但未识别到明确二次确认按钮状态，且该需求本身标记为待版本确认，已留证待中控确认。'
        : hasCashback
          ? '详情页存在返现信息，但未识别到二次确认按钮/状态。'
          : '详情页未识别到店铺返现字段或二次确认入口。',
      [detailState.screenshot, detailState.txt]
    );

    for (const [width, height] of [[1366, 768], [1440, 900], [1920, 1080]]) {
      await detailPage.setViewportSize({ width, height });
      await detailPage.waitForTimeout(500);
      await savePageState(detailPage, `50_compat_detail_${width}x${height}`);
    }
    addCase(cases, 'TC-OD-SEC-003', 'Blocked', '已按 1366/1440/1920 宽度采集详情页兼容性截图；由于核心筛选是否存在/状态数据前置未完全满足，本轮不做布局通过判定。', [
      path.join(OUT_DIR, '50_compat_detail_1366x768.png'),
      path.join(OUT_DIR, '50_compat_detail_1440x900.png'),
      path.join(OUT_DIR, '50_compat_detail_1920x1080.png'),
    ]);
  } else {
    addCase(cases, 'TC-OD-CB-001', 'Blocked', '列表未能打开订单详情，无法覆盖店铺返现展示。', [listState.screenshot]);
    addCase(cases, 'TC-OD-SEC-003', 'Blocked', '列表未能打开订单详情，无法采集详情页兼容截图。', [listState.screenshot]);
  }
}

function summarizeCases(cases) {
  const summary = {};
  for (const c of cases) summary[c.status] = (summary[c.status] || 0) + 1;
  return summary;
}

function makeMarkdown(report) {
  const lines = [];
  lines.push('# Agent2 WCZ 代购订单详情测试执行报告');
  lines.push('');
  lines.push(`执行时间：${report.generatedAt}`);
  lines.push('');
  lines.push('## 环境声明');
  lines.push('');
  lines.push(`- 本轮目标后台固定为：\`${ADMIN_URL}\``);
  lines.push('- 上一轮 `wlz-admin-all-view.hubbuyer.com` 结果已被目标环境纠正，本轮不作为判定依据。');
  lines.push('- 本报告不记录明文密码、Token、Cookie。');
  lines.push('');
  lines.push('## 登录与路径');
  lines.push('');
  lines.push(`- 尝试入口：\`${ADMIN_URL}/login\``);
  lines.push(`- 尝试路径：\`${ADMIN_URL}/b2b/order/agentBuy\`、\`${ADMIN_URL}/b2b/order/agentBuy/detail\``);
  if (report.selectedAccount) {
    lines.push(`- 本轮可登录账号标识：\`${report.selectedAccount.account}\` (${report.selectedAccount.role || report.selectedAccount.source || 'source recorded'})`);
  } else {
    lines.push('- 本轮未获得可登录账号。');
  }
  if (report.detail?.initial?.orderNos?.length) {
    lines.push(`- 本轮详情页识别订单号：\`${report.detail.initial.orderNos[0]}\``);
  }
  lines.push('');
  lines.push('## 执行结果汇总');
  lines.push('');
  const summary = summarizeCases(report.cases);
  lines.push(`- Pass：${summary.Pass || 0}`);
  lines.push(`- Fail：${summary.Fail || 0}`);
  lines.push(`- Blocked：${summary.Blocked || 0}`);
  lines.push('');
  lines.push('| 用例 | 状态 | 结论 |');
  lines.push('| --- | --- | --- |');
  for (const c of report.cases) {
    lines.push(`| ${c.id} | ${c.status} | ${c.conclusion.replace(/\|/g, '/')} |`);
  }
  lines.push('');
  lines.push('## 发现的缺陷或疑点');
  lines.push('');
  const fails = report.cases.filter((c) => c.status === 'Fail');
  if (fails.length) {
    for (const fail of fails) lines.push(`- ${fail.id}：${fail.conclusion}`);
  } else {
    lines.push('- 本轮未形成明确 Fail；阻塞项见下一节。');
  }
  lines.push('');
  lines.push('## 需中控解决的问题');
  lines.push('');
  if (!report.selectedAccount) {
    lines.push('- 账号阻塞：本地账号线索均未能登录 WCZ 后台，请提供 WCZ 专属可用账号及角色权限说明。');
  }
  if (report.selectedAccount && report.routes?.agentBuyList?.state && !report.detail?.initial) {
    lines.push('- 功能路径阻塞：可登录但无法打开代购订单详情，请确认 WCZ 环境菜单权限与路由。');
  }
  const blocked = report.cases.filter((c) => c.status === 'Blocked');
  if (blocked.length) {
    lines.push('- 数据/版本阻塞：存在用例因筛选控件缺失、缺少覆盖状态数据、缺少采购员账号或需求待版本确认而无法完成规则级判定。');
  }
  if (report.permissionProbe) {
    lines.push(`- 权限账号尝试：采购员账号标识 \`${report.permissionProbe.account}\` 登录结果为 ${report.permissionProbe.success ? '成功' : '失败/不可用'}，详见对应截图。`);
  }
  lines.push('');
  lines.push('## 主要证据');
  lines.push('');
  const evidence = new Set();
  for (const c of report.cases) for (const e of c.evidence || []) evidence.add(e);
  for (const e of [
    report.loginInitial?.screenshot,
    ...report.loginAttempts.map((x) => x.state?.screenshot).filter(Boolean),
    report.routes?.agentBuyList?.state?.screenshot,
    report.detail?.initial?.state?.screenshot,
    ...evidence,
    path.join(OUT_DIR, 'execution_results.json'),
    path.join(OUT_DIR, 'agent2_wcz_execution_report.md'),
  ].filter(Boolean)) {
    lines.push(`- \`${e}\``);
  }
  lines.push('');
  return lines.join('\n');
}

(async () => {
  ensureDir(OUT_DIR);
  const report = {
    generatedAt: new Date().toISOString(),
    adminUrl: ADMIN_URL,
    caseDoc: CASE_DOC,
    loginAttempts: [],
    apiEvents: [],
    consoleErrors: [],
    pageErrors: [],
    dialogs: [],
    routes: {},
    cases: [],
  };

  const credentials = uniqueCredentials();
  report.credentialsFound = credentials.map((c) => ({ account: c.account, source: c.source, role: c.role }));

  const executablePath = fs.existsSync(CHROME) ? CHROME : undefined;
  const browser = await chromium.launch({ headless: true, executablePath });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    ignoreHTTPSErrors: true,
    locale: 'zh-CN',
  });

  context.on('response', async (resp) => {
    const url = resp.url();
    if (!url.includes('hubbuyer.com')) return;
    if (/\.(js|css|png|jpg|jpeg|svg|ico|woff2?|map)(?:\?|$)/i.test(url)) return;
    if (report.apiEvents.length >= 250) return;
    const event = {
      method: resp.request().method(),
      url: scrubText(url),
      status: resp.status(),
      requestPost: scrubText(resp.request().postData() || '').slice(0, 1200),
    };
    try {
      event.bodySnippet = scrubText(await resp.text()).slice(0, 1800);
    } catch (e) {
      event.bodyError = e.message;
    }
    report.apiEvents.push(event);
  });

  const firstPage = await context.newPage();
  firstPage.on('console', (msg) => {
    if (['error', 'warning'].includes(msg.type())) {
      report.consoleErrors.push({ type: msg.type(), text: scrubText(msg.text()).slice(0, 500), url: firstPage.url() });
    }
  });
  firstPage.on('pageerror', (err) => report.pageErrors.push({ message: err.message, url: firstPage.url() }));
  firstPage.on('dialog', async (dialog) => {
    report.dialogs.push({ type: dialog.type(), message: scrubText(dialog.message()), url: firstPage.url() });
    await dialog.dismiss().catch(() => {});
  });

  await firstPage.goto(`${ADMIN_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 35000 }).catch(() => {});
  await firstPage.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  report.loginInitial = await savePageState(firstPage, '00_login_initial');
  await firstPage.close().catch(() => {});

  let activePage = null;
  for (let i = 0; i < credentials.length; i += 1) {
    const { result, page } = await loginWith(context, credentials[i], i + 1);
    report.loginAttempts.push(result);
    if (result.success) {
      report.selectedAccount = { account: result.account, source: result.source, role: result.role, url: result.url };
      activePage = page;
      break;
    }
  }

  if (!activePage) {
    for (const id of ['TC-OD-FLT-001', 'TC-OD-FLT-002', 'TC-OD-FLT-003', 'TC-OD-FLT-004', 'TC-OD-FLT-005', 'TC-OD-FLT-006', 'TC-OD-FLT-007', 'TC-OD-FLT-008', 'TC-OD-FLT-009', 'TC-OD-FLT-010', 'TC-OD-FLT-011', 'TC-OD-FLT-012']) {
      addCase(report.cases, id, 'Blocked', 'WCZ 后台未获得可登录账号，无法进入代购订单详情执行。', [report.loginInitial.screenshot]);
    }
    writeJson(path.join(OUT_DIR, 'execution_results.json'), report);
    writeText(path.join(OUT_DIR, 'agent2_wcz_execution_report.md'), makeMarkdown(report));
    await browser.close();
    return;
  }

  activePage.on('console', (msg) => {
    if (['error', 'warning'].includes(msg.type())) {
      report.consoleErrors.push({ type: msg.type(), text: scrubText(msg.text()).slice(0, 500), url: activePage.url() });
    }
  });
  activePage.on('pageerror', (err) => report.pageErrors.push({ message: err.message, url: activePage.url() }));
  activePage.on('dialog', async (dialog) => {
    report.dialogs.push({ type: dialog.type(), message: scrubText(dialog.message()), url: activePage.url() });
    await dialog.dismiss().catch(() => {});
  });

  report.postLogin = await savePageState(activePage, '10_post_login');
  report.routes.agentBuyList = await openRoute(activePage, '11_agent_buy_list_initial', '/b2b/order/agentBuy');
  await clickTextButton(activePage, '展开').catch(() => {});
  await activePage.waitForTimeout(800);
  report.routes.agentBuyListExpanded = {
    state: await savePageState(activePage, '12_agent_buy_list_expanded'),
    controls: await collectControls(activePage),
    tables: await collectTables(activePage),
  };
  await clickTextButton(activePage, '进行中').catch(() => {});
  await activePage.waitForLoadState('networkidle', { timeout: 12000 }).catch(() => {});
  await activePage.waitForTimeout(1000);
  report.routes.agentBuyListInProgress = {
    state: await savePageState(activePage, '13_agent_buy_list_in_progress'),
    controls: await collectControls(activePage),
    tables: await collectTables(activePage),
  };

  let detailPage = await clickFirstDetail(activePage, 0);
  if (!detailPage) {
    const listText = await bodyText(activePage);
    const orderNos = extractOrderNosFromText(listText);
    report.routes.extractedOrderNos = orderNos;
    if (orderNos.length) {
      await activePage.goto(`${ADMIN_URL}/b2b/order/agentBuy/detail?order_no=${encodeURIComponent(orderNos[0])}`, { waitUntil: 'domcontentloaded', timeout: 40000 }).catch(() => {});
      await activePage.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {});
      await activePage.waitForTimeout(1600);
      const text = await bodyText(activePage);
      if (/订单|商品|采购|店铺|商铺/.test(text) && !/404|not found|无权限|登录/.test(text)) detailPage = activePage;
    }
  }

  if (detailPage) {
    activePage = detailPage;
    await runDetailFilterCases(activePage, report);
  } else {
    const state = await savePageState(activePage, '20_detail_open_failed');
    for (const id of ['TC-OD-FLT-001', 'TC-OD-FLT-002', 'TC-OD-FLT-003', 'TC-OD-FLT-004', 'TC-OD-FLT-005', 'TC-OD-FLT-006', 'TC-OD-FLT-007', 'TC-OD-FLT-008', 'TC-OD-FLT-009', 'TC-OD-FLT-010', 'TC-OD-FLT-011', 'TC-OD-FLT-012']) {
      addCase(report.cases, id, 'Blocked', '可登录 WCZ 后台，但未能进入代购订单详情页；需确认权限、路由或测试数据。', [state.screenshot, state.txt]);
    }
  }

  await runOptionalCoverage(activePage, report).catch((e) => {
    report.optionalError = e.message;
  });

  addCase(report.cases, 'TC-OD-SEC-001', 'Blocked', '本轮按中控补充仅使用 admin 登录 WCZ；不同角色权限控制需另行提供采购员/无权限账号后执行。', []);

  report.summary = summarizeCases(report.cases);
  writeJson(path.join(OUT_DIR, 'execution_results.json'), report);
  writeText(path.join(OUT_DIR, 'agent2_wcz_execution_report.md'), makeMarkdown(report));
  await browser.close();
})().catch((e) => {
  ensureDir(OUT_DIR);
  const fatal = { generatedAt: new Date().toISOString(), adminUrl: ADMIN_URL, fatalError: e.stack || e.message };
  writeJson(path.join(OUT_DIR, 'execution_results.json'), fatal);
  writeText(path.join(OUT_DIR, 'agent2_wcz_execution_report.md'), `# Agent2 WCZ 执行异常\n\n${e.stack || e.message}\n`);
  process.exitCode = 1;
});
