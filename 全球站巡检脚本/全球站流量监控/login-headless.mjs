#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import { loadConfig } from "./check-traffic.mjs";

async function ensureDir(dirPath) {
  await fs.mkdir(dirPath, { recursive: true });
}

async function wait(ms) {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

async function bodyText(page) {
  try {
    return await page.locator("body").innerText({ timeout: 5000 });
  } catch {
    return "";
  }
}

async function isLoggedIn(page, config) {
  const url = page.url();
  if (/login|passport|login\.taobao\.com|member\.1688\.com/i.test(url)) {
    return false;
  }
  const text = await bodyText(page);
  if (text.includes(config.parse?.label || "应用流量")) {
    return true;
  }
  return text.includes(config.appName) || text.includes(config.appKey);
}

function buildLaunchOptions(config) {
  const browserConfig = config.browser || {};
  const args = Array.isArray(browserConfig.args) ? [...browserConfig.args] : [];
  if (process.platform !== "win32" && process.getuid?.() === 0 && !args.includes("--no-sandbox")) {
    args.push("--no-sandbox");
  }
  if (!args.includes("--disable-dev-shm-usage")) {
    args.push("--disable-dev-shm-usage");
  }

  const options = {
    headless: true,
    viewport: { width: 1366, height: 900 },
    locale: "zh-CN",
    args
  };
  if (browserConfig.executablePath) {
    options.executablePath = browserConfig.executablePath;
  } else if (browserConfig.channel) {
    options.channel = browserConfig.channel;
  }
  return options;
}

async function main() {
  const config = await loadConfig();
  const loginDir = path.resolve(config.logs.dir, "login");
  const screenshotPath = path.join(loginDir, "login-page.png");
  const statusPath = path.join(loginDir, "login-status.json");
  const maxMinutes = Number(process.env.MONITOR_LOGIN_TIMEOUT_MINUTES || 10);
  const intervalMs = Number(process.env.MONITOR_LOGIN_SCREENSHOT_INTERVAL_MS || 10000);
  const deadline = Date.now() + maxMinutes * 60 * 1000;

  await ensureDir(config.browserProfileDir);
  await ensureDir(loginDir);

  const { chromium } = await import("playwright");
  const context = await chromium.launchPersistentContext(
    config.browserProfileDir,
    buildLaunchOptions(config)
  );
  const page = context.pages()[0] || await context.newPage();
  page.setDefaultNavigationTimeout(config.timeouts.navigationMs);

  await page.goto(config.consoleUrl, {
    waitUntil: "domcontentloaded",
    timeout: config.timeouts.navigationMs
  });

  console.log("无界面登录已启动。");
  console.log(`登录页截图: ${screenshotPath}`);
  console.log("请在宝塔文件管理中打开该图片，用手机扫码登录。");
  console.log(`脚本会等待 ${maxMinutes} 分钟，并每 ${Math.round(intervalMs / 1000)} 秒刷新一次截图。`);

  let loggedIn = false;
  while (Date.now() < deadline) {
    await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
    const status = {
      checkedAt: new Date().toISOString(),
      url: page.url(),
      screenshot: screenshotPath,
      loggedIn: false
    };
    await fs.writeFile(statusPath, JSON.stringify(status, null, 2), "utf8");

    if (await isLoggedIn(page, config)) {
      loggedIn = true;
      status.loggedIn = true;
      status.url = page.url();
      await fs.writeFile(statusPath, JSON.stringify(status, null, 2), "utf8");
      break;
    }
    await wait(intervalMs);
  }

  await context.close();

  if (!loggedIn) {
    console.log("登录等待超时。请重新执行 npm run login:headless 获取新的二维码截图。");
    process.exit(1);
  }

  console.log("登录成功，browser-profile 已保存。");
  console.log("现在可以执行: MONITOR_NOTIFY_ENABLED=true npm run inspect:bt");
}

main().catch((error) => {
  console.error(`无界面登录失败: ${error.message}`);
  process.exit(1);
});
