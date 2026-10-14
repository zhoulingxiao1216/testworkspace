import { chromium } from 'playwright';

const account = process.env.WO_TEST_ACCOUNT || '';
const password = process.env.WO_TEST_PASSWORD || '';
const label = process.env.WO_TEST_LABEL || 'account';

if (!account || !password) {
  throw new Error('Missing WO_TEST_ACCOUNT or WO_TEST_PASSWORD');
}

const browser = await chromium.launch({
  headless: true,
  executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
});

const context = await browser.newContext({ ignoreHTTPSErrors: true });
const page = await context.newPage();
const responses = [];
const pageErrors = [];
const consoleErrors = [];

const flattenMenuMatches = (nodes) => {
  const matches = [];
  const stack = Array.isArray(nodes) ? [...nodes] : [];
  while (stack.length) {
    const node = stack.shift() || {};
    const text = [node.name, node.title, node.path, node.component].filter(Boolean).join(' ');
    if (/工单|work.?order|代购订单/i.test(text)) {
      matches.push({
        id: node.id,
        name: node.name || node.title || '',
        path: node.path || '',
        component: node.component || '',
      });
    }
    if (Array.isArray(node.children)) stack.push(...node.children);
  }
  return matches.slice(0, 80);
};

page.setDefaultTimeout(8_000);
page.on('pageerror', (error) => pageErrors.push(error.message));
page.on('console', (message) => {
  if (message.type() === 'error') consoleErrors.push(message.text());
});

page.on('response', async (response) => {
  const url = response.url();
  if (!/\/admin\/login\/login|workOrder/i.test(url)) return;
  const item = { url, status: response.status() };
  try {
    const body = await response.json();
    item.code = body?.code;
    item.msg = body?.msg;
    if (/\/admin\/login\/login/i.test(url)) {
      item.dataKeys = Object.keys(body?.data || {}).filter((key) => !/token/i.test(key));
      item.menuMatches = flattenMenuMatches(body?.data?.admin_menu_tree_list_data);
      item.buttonPermissions = Object.keys(body?.data?.admin_menu_button_data || {})
        .filter((key) => /工单|work.?order/i.test(key))
        .slice(0, 80);
    }
  } catch {
    // Non-JSON responses only need URL and HTTP status evidence.
  }
  responses.push(item);
});

try {
  await page.goto('https://main-admin.hubbuyer.com/login', {
    waitUntil: 'domcontentloaded',
    timeout: 30_000,
  });
  await page.getByPlaceholder('请输入账号').fill(account);
  await page.getByPlaceholder('请输入密码').fill(password);
  await page.getByRole('button', { name: '登录' }).click();
  await page.waitForTimeout(5_000);

  const bodyText = await page.locator('body').innerText().catch(() => '');
  const workOrderTexts = await page.locator('a,button,.el-menu-item,.el-sub-menu__title')
    .allInnerTexts()
    .then((items) => items.filter((text) => /工单|代购订单|订单管理/.test(text)).slice(0, 80))
    .catch(() => []);
  const links = await page.locator('a[href]')
    .evaluateAll((items) => items
      .map((item) => ({ text: item.textContent?.trim() || '', href: item.getAttribute('href') || '' }))
      .filter((item) => /工单|work.?order|代购订单/i.test(`${item.text} ${item.href}`))
      .slice(0, 80))
    .catch(() => []);

  await page.screenshot({
    path: `D:/test_workspace/output/playwright/work-order-${label}-after-login.png`,
    fullPage: false,
  });

  console.log(JSON.stringify({
    label,
    url: page.url(),
    title: await page.title(),
    loginSucceeded: !page.url().includes('/login'),
    body: bodyText.slice(0, 3_000),
    workOrderTexts,
    links,
    responses,
    pageErrors,
    consoleErrors: consoleErrors.slice(0, 30),
  }, null, 2));
} finally {
  await browser.close();
}
