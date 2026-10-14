#!/usr/bin/env node
import fs from "node:fs/promises";
import { existsSync } from "node:fs";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DEFAULT_CONFIG = {
  consoleUrl: "https://open.1688.com/console",
  appDetailUrl: "https://open.1688.com/develop/app/detail?appKey=9466082",
  appKey: "9466082",
  appName: "樱花代购さくら代行",
  threshold: 300000,
  unit: "次/天",
  browserProfileDir: "./browser-profile",
  headless: false,
  browser: {
    channel: "chrome",
    executablePath: "",
    viewport: null,
    args: ["--disable-gpu"]
  },
  timeouts: {
    navigationMs: 45000,
    pageReadyMs: 15000,
    settleMs: 3000,
    notifyMs: 10000
  },
  retry: {
    attempts: 2,
    intervalMs: 3000
  },
  parse: {
    label: "应用流量",
    allowGlobalRatioFallback: false
  },
  logs: {
    dir: "./logs",
    trafficLog: "./logs/traffic.log",
    latestResult: "./logs/latest-result.json",
    screenshotDir: "./logs/screenshots",
    screenshotOnFailure: true
  },
  notify: {
    enabled: false,
    type: "wecom",
    webhookUrlEnv: "MONITOR_WEBHOOK_URL",
    onlyOnWarning: false
  }
};

const FAILURE_SCREENSHOT_MESSAGES = new Set([
  "login_required",
  "parse_failed",
  "network_error",
  "runtime_error"
]);

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function isPlainObject(value) {
  return Object.prototype.toString.call(value) === "[object Object]";
}

function mergeDeep(base, override) {
  const output = clone(base);
  for (const [key, value] of Object.entries(override || {})) {
    if (isPlainObject(value) && isPlainObject(output[key])) {
      output[key] = mergeDeep(output[key], value);
    } else {
      output[key] = value;
    }
  }
  return output;
}

async function readJsonIfExists(filePath) {
  if (!filePath || !existsSync(filePath)) {
    return {};
  }
  const raw = await fs.readFile(filePath, "utf8");
  return JSON.parse(raw);
}

function parseBoolean(value) {
  if (value === undefined || value === null || value === "") {
    return undefined;
  }
  return ["1", "true", "yes", "y", "on"].includes(String(value).toLowerCase());
}

function resolveProjectPath(value) {
  if (!value) {
    return value;
  }
  return path.isAbsolute(value) ? value : path.resolve(__dirname, value);
}

function applyEnvOverrides(config) {
  const result = clone(config);
  if (process.env.MONITOR_APP_KEY) {
    result.appKey = process.env.MONITOR_APP_KEY;
  }
  if (process.env.MONITOR_APP_NAME) {
    result.appName = process.env.MONITOR_APP_NAME;
  }
  if (process.env.MONITOR_APP_DETAIL_URL) {
    result.appDetailUrl = process.env.MONITOR_APP_DETAIL_URL;
  }
  if (process.env.MONITOR_CONSOLE_URL) {
    result.consoleUrl = process.env.MONITOR_CONSOLE_URL;
  }
  if (process.env.MONITOR_THRESHOLD) {
    result.threshold = Number(process.env.MONITOR_THRESHOLD);
  }
  if (process.env.MONITOR_BROWSER_PROFILE_DIR) {
    result.browserProfileDir = process.env.MONITOR_BROWSER_PROFILE_DIR;
  }
  if (process.env.MONITOR_CHROME_PATH) {
    result.browser.executablePath = process.env.MONITOR_CHROME_PATH;
  }
  const headless = parseBoolean(process.env.MONITOR_HEADLESS);
  if (headless !== undefined) {
    result.headless = headless;
  }
  const notifyEnabled = parseBoolean(process.env.MONITOR_NOTIFY_ENABLED);
  if (notifyEnabled !== undefined) {
    result.notify.enabled = notifyEnabled;
  }
  return result;
}

function applyLocalSecrets(config, secrets) {
  const result = clone(config);
  if (!secrets || Object.keys(secrets).length === 0) {
    return result;
  }

  if (secrets.monitor_notify_enabled !== undefined) {
    result.notify.enabled = Boolean(secrets.monitor_notify_enabled);
  }
  if (secrets.monitor_webhook_url) {
    result.notify.webhookUrl = secrets.monitor_webhook_url;
  }
  if (secrets.monitor_notify_only_on_warning !== undefined) {
    result.notify.onlyOnWarning = Boolean(secrets.monitor_notify_only_on_warning);
  }
  return result;
}

function normalizeConfig(config) {
  const result = clone(config);
  result.threshold = Number(result.threshold);
  result.headless = Boolean(result.headless);
  result.browserProfileDir = resolveProjectPath(result.browserProfileDir);
  result.logs.dir = resolveProjectPath(result.logs.dir);
  result.logs.trafficLog = resolveProjectPath(result.logs.trafficLog);
  result.logs.latestResult = resolveProjectPath(result.logs.latestResult);
  result.logs.screenshotDir = resolveProjectPath(result.logs.screenshotDir);

  if (!result.appDetailUrl && result.appKey) {
    result.appDetailUrl = `https://open.1688.com/develop/app/detail?appKey=${encodeURIComponent(result.appKey)}`;
  }
  if (!result.appKey) {
    throw new Error("配置缺少 appKey");
  }
  if (!Number.isFinite(result.threshold)) {
    throw new Error("配置 threshold 必须是数字");
  }
  return result;
}

export async function loadConfig() {
  const configPath = process.env.MONITOR_CONFIG
    ? path.resolve(process.env.MONITOR_CONFIG)
    : path.join(__dirname, "config.json");
  const localPath = path.join(__dirname, "config.local.json");
  const secretsPath = path.join(__dirname, "config", "secrets.local.json");

  let config = mergeDeep(DEFAULT_CONFIG, await readJsonIfExists(configPath));
  if (localPath !== configPath) {
    config = mergeDeep(config, await readJsonIfExists(localPath));
  }
  config = applyLocalSecrets(config, await readJsonIfExists(secretsPath));
  return normalizeConfig(applyEnvOverrides(config));
}

async function ensureDir(dirPath) {
  await fs.mkdir(dirPath, { recursive: true });
}

async function wait(ms) {
  if (ms <= 0) {
    return;
  }
  await new Promise((resolve) => setTimeout(resolve, ms));
}

function nowIso() {
  return new Date().toISOString();
}

function compactNumber(value) {
  return String(value || "").replace(/[,\s]/g, "");
}

function toInteger(value) {
  const normalized = compactNumber(value);
  if (!/^\d+$/.test(normalized)) {
    return null;
  }
  return Number(normalized);
}

function escapeRegExp(text) {
  return String(text).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function extractTrafficFromText(text, label, allowGlobalRatioFallback) {
  const normalized = String(text || "")
    .replace(/\u00a0/g, " ")
    .replace(/\r/g, "\n");
  const labelText = label || "应用流量";
  const labelPattern = escapeRegExp(labelText);
  const directPattern = new RegExp(
    `${labelPattern}\\s*[：:]?\\s*([\\d,\\s]+)\\/\\s*([\\d,\\s]+)(?:\\s*[（(]\\s*(?:单位\\s*[：:]\\s*)?([^）)]+)[）)])?`,
    "u"
  );
  const directMatch = normalized.match(directPattern);
  if (directMatch) {
    return {
      used: toInteger(directMatch[1]),
      limit: toInteger(directMatch[2]),
      unit: (directMatch[3] || "").trim()
    };
  }

  const labelIndex = normalized.indexOf(labelText);
  if (labelIndex >= 0) {
    const nearbyText = normalized.slice(labelIndex, labelIndex + 600);
    const ratioMatch = nearbyText.match(/([\d,\s]+)\/\s*([\d,\s]+)/u);
    const unitMatch = nearbyText.match(/单位\s*[：:]\s*([^\s）)]+)/u);
    if (ratioMatch) {
      return {
        used: toInteger(ratioMatch[1]),
        limit: toInteger(ratioMatch[2]),
        unit: (unitMatch?.[1] || "").trim()
      };
    }
  }

  if (allowGlobalRatioFallback) {
    const globalMatch = normalized.match(/([\d,\s]+)\/\s*([\d,\s]+)/u);
    if (globalMatch) {
      return {
        used: toInteger(globalMatch[1]),
        limit: toInteger(globalMatch[2]),
        unit: ""
      };
    }
  }

  return null;
}

export function parseTrafficText(text, parseConfig = {}, fallbackUnit = "次/天") {
  const parsed = extractTrafficFromText(
    text,
    parseConfig.label || "应用流量",
    Boolean(parseConfig.allowGlobalRatioFallback)
  );
  if (!parsed || parsed.used === null || parsed.limit === null) {
    return null;
  }
  return {
    used: parsed.used,
    limit: parsed.limit,
    unit: parsed.unit || fallbackUnit || "次/天"
  };
}

function buildResult(config, code, msg, data = {}) {
  return {
    code,
    msg,
    data: {
      appKey: config.appKey,
      appName: config.appName,
      threshold: config.threshold,
      checkedAt: nowIso(),
      ...data
    }
  };
}

async function getBodyText(page, timeoutMs) {
  try {
    return await page.locator("body").innerText({ timeout: timeoutMs });
  } catch {
    return await page.content();
  }
}

async function isLoginRequired(page, config) {
  const currentUrl = page.url();
  if (/login|passport|auth|login\.taobao\.com|member\.1688\.com/i.test(currentUrl)) {
    return true;
  }

  const bodyText = await getBodyText(page, config.timeouts.pageReadyMs);
  if (bodyText.includes(config.parse.label || "应用流量")) {
    return false;
  }
  const loginMarkers = [
    "请登录",
    "扫码登录",
    "密码登录",
    "登录名",
    "手机淘宝扫码",
    "安全验证"
  ];
  return loginMarkers.some((marker) => bodyText.includes(marker));
}

async function gotoWithRetry(page, url, config) {
  const attempts = Math.max(1, Number(config.retry.attempts || 1));
  let lastError;
  for (let index = 1; index <= attempts; index += 1) {
    try {
      return await page.goto(url, {
        waitUntil: "domcontentloaded",
        timeout: config.timeouts.navigationMs
      });
    } catch (error) {
      lastError = error;
      if (index < attempts) {
        await wait(Number(config.retry.intervalMs || 0));
      }
    }
  }
  throw lastError;
}

async function tryOpenFromConsole(page, config) {
  await gotoWithRetry(page, config.consoleUrl, config);
  await page.waitForLoadState("domcontentloaded", { timeout: config.timeouts.pageReadyMs }).catch(() => {});
  await wait(config.timeouts.settleMs);

  if (await isLoginRequired(page, config)) {
    return false;
  }

  const candidates = [config.appKey, config.appName].filter(Boolean);
  for (const text of candidates) {
    const locator = page.getByText(text, { exact: false }).first();
    if (await locator.count()) {
      await locator.click({ timeout: 5000 }).catch(() => {});
      await page.waitForLoadState("domcontentloaded", { timeout: config.timeouts.pageReadyMs }).catch(() => {});
      await wait(config.timeouts.settleMs);
      return true;
    }
  }
  return false;
}

function sanitizeFilename(value) {
  return String(value).replace(/[\\/:*?"<>|\s]+/g, "_").slice(0, 80);
}

function getChromeProcessesUsingProfile(profileDir) {
  if (process.platform !== "win32") {
    return [];
  }

  try {
    const script = `
$dir = [System.IO.Path]::GetFullPath($args[0])
$pattern = "*" + [System.Management.Automation.WildcardPattern]::Escape($dir) + "*"
Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" |
  Where-Object { $_.CommandLine -and $_.CommandLine -like $pattern } |
  Select-Object -First 8 -ExpandProperty ProcessId
`;
    const output = execFileSync(
      "powershell.exe",
      ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script, profileDir],
      { encoding: "utf8", timeout: 5000, windowsHide: true }
    );
    return output
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => /^\d+$/.test(line));
  } catch {
    return [];
  }
}

async function saveFailureScreenshot(page, config, result) {
  if (!page || !config.logs.screenshotOnFailure || !FAILURE_SCREENSHOT_MESSAGES.has(result.msg)) {
    return;
  }
  try {
    await ensureDir(config.logs.screenshotDir);
    const timestamp = nowIso().replace(/[:.]/g, "-");
    const fileName = `${timestamp}_${sanitizeFilename(config.appKey)}_${result.msg}.png`;
    const screenshotPath = path.join(config.logs.screenshotDir, fileName);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    result.data.screenshot = screenshotPath;
  } catch (error) {
    result.data.screenshotError = error.message;
  }
}

function classifyRuntimeError(error) {
  const message = String(error?.message || error);
  if (/spawn EPERM/i.test(message)) {
    return [
      "browser_launch_forbidden",
      500,
      "当前运行环境拒绝启动 Chrome。请在已登录桌面的用户会话中执行，或设置 MONITOR_HEADLESS=true 后重试。"
    ];
  }
  if (/Target page, context or browser has been closed/i.test(message) && /user-data-dir/i.test(message)) {
    return [
      "profile_in_use",
      409,
      "Chrome 启动后立即退出，通常是 browser-profile 仍被首次登录窗口占用。请关闭使用该目录的 Chrome 后再执行检查。"
    ];
  }
  if (/Emulation\.setDeviceMetricsOverride|Target does not support metrics override/i.test(message)) {
    return [
      "runtime_error",
      500,
      "Chrome 不支持当前 viewport emulation，已建议将 config.json 的 browser.viewport 设为 null，并优先使用有界面模式检查。"
    ];
  }
  if (/Timeout|net::|ERR_|Navigation|ECONN|ENOTFOUND|ETIMEDOUT/i.test(message)) {
    return ["network_error", 503, `1688 页面加载失败: ${message}`];
  }
  if (/Cannot find package 'playwright'|playwright/i.test(message) && /install|module|package/i.test(message)) {
    return ["runtime_error", 500, "未找到 Playwright 依赖，请先在当前目录执行 npm install"];
  }
  return ["runtime_error", 500, message];
}

function buildLaunchOptions(config, overrides = {}) {
  const browserConfig = config.browser || {};
  const launchOptions = {
    headless: overrides.headless ?? config.headless,
    viewport: null,
    locale: "zh-CN",
    args: Array.isArray(browserConfig.args) ? browserConfig.args : []
  };

  if (browserConfig.executablePath) {
    launchOptions.executablePath = browserConfig.executablePath;
  } else if (browserConfig.channel) {
    launchOptions.channel = browserConfig.channel;
  }

  if (browserConfig.enableViewportEmulation && browserConfig.viewport) {
    launchOptions.viewport = browserConfig.viewport;
  }

  return launchOptions;
}

async function launchPersistentContextWithFallback(chromium, config) {
  const primaryOptions = buildLaunchOptions(config);

  try {
    return await chromium.launchPersistentContext(config.browserProfileDir, primaryOptions);
  } catch (error) {
    const message = String(error?.message || error);
    const shouldFallbackToVisible = config.headless
      && /Target page, context or browser has been closed|Emulation\.setDeviceMetricsOverride|Target does not support metrics override/i.test(message);
    const shouldFallbackToHeadless = !config.headless && /spawn EPERM/i.test(message);

    if (!shouldFallbackToVisible && !shouldFallbackToHeadless) {
      throw error;
    }

    const fallbackHeadless = shouldFallbackToVisible ? false : true;
    try {
      return await chromium.launchPersistentContext(
        config.browserProfileDir,
        buildLaunchOptions(config, { headless: fallbackHeadless })
      );
    } catch (fallbackError) {
      fallbackError.message = `${fallbackError.message}\n首次启动错误: ${message}`;
      throw fallbackError;
    }
  }
}

async function runBrowserCheck(config) {
  let context;
  let page;
  let result;

  try {
    await ensureDir(config.browserProfileDir);
    const profilePids = getChromeProcessesUsingProfile(config.browserProfileDir);
    if (profilePids.length > 0) {
      return buildResult(config, 409, "profile_in_use", {
        message: `检测到 Chrome 正在使用 browser-profile，请先关闭首次登录窗口后再检查。占用 PID: ${profilePids.join(", ")}`
      });
    }

    const { chromium } = await import("playwright");
    context = await launchPersistentContextWithFallback(chromium, config);
    page = context.pages()[0] || await context.newPage();
    page.setDefaultTimeout(config.timeouts.pageReadyMs);
    page.setDefaultNavigationTimeout(config.timeouts.navigationMs);

    await gotoWithRetry(page, config.appDetailUrl, config);
    await page.waitForLoadState("domcontentloaded", { timeout: config.timeouts.pageReadyMs }).catch(() => {});
    await wait(config.timeouts.settleMs);

    if (await isLoginRequired(page, config)) {
      result = buildResult(config, 401, "login_required", {
        message: "1688 登录态已失效，需要人工重新登录"
      });
    } else {
      let bodyText = await getBodyText(page, config.timeouts.pageReadyMs);
      let traffic = parseTrafficText(bodyText, config.parse, config.unit);

      if (!traffic && config.consoleUrl) {
        const opened = await tryOpenFromConsole(page, config);
        if (opened && !(await isLoginRequired(page, config))) {
          bodyText = await getBodyText(page, config.timeouts.pageReadyMs);
          traffic = parseTrafficText(bodyText, config.parse, config.unit);
        }
      }

      if (!traffic) {
        result = buildResult(config, 500, "parse_failed", {
          message: "未能从页面解析应用流量，可能是页面结构变化或网络异常"
        });
      } else {
        const isWarning = traffic.used >= config.threshold;
        result = buildResult(config, 200, isWarning ? "warning" : "normal", {
          used: traffic.used,
          limit: traffic.limit,
          unit: traffic.unit,
          message: isWarning
            ? `1688 应用流量已达到或超过 ${config.threshold}，请关注`
            : "1688 应用流量正常"
        });
      }
    }
  } catch (error) {
    const [msg, code, message] = classifyRuntimeError(error);
    result = buildResult(config, code, msg, { message });
  }

  await saveFailureScreenshot(page, config, result);
  if (context) {
    await context.close().catch(() => {});
  }
  return result;
}

async function persistResult(config, result) {
  await ensureDir(config.logs.dir);
  await fs.appendFile(
    config.logs.trafficLog,
    JSON.stringify({ loggedAt: nowIso(), ...result }, null, 0) + "\n",
    "utf8"
  );
  await fs.writeFile(config.logs.latestResult, JSON.stringify(result, null, 2), "utf8");
}

function buildWebhookContent(result) {
  const data = result.data || {};
  if (data.used !== undefined && data.limit !== undefined) {
    return `**${data.appName || "1688应用"}**  应用流量：${data.used}/${data.limit}`;
  }
  return data.message || result.msg || "-";
}

async function postJson(url, payload, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal
    });
    if (!response.ok) {
      throw new Error(`Webhook 返回 HTTP ${response.status}`);
    }
  } finally {
    clearTimeout(timer);
  }
}

async function sendNotification(config, result) {
  const notify = config.notify || {};
  if (!notify.enabled) {
    return;
  }
  if (notify.onlyOnWarning && result.msg === "normal") {
    return;
  }
  const webhookUrl = process.env[notify.webhookUrlEnv || "MONITOR_WEBHOOK_URL"] || notify.webhookUrl;
  if (!webhookUrl) {
    return;
  }

  const content = buildWebhookContent(result);
  const type = String(notify.type || "wecom").toLowerCase();
  const payload = type === "dingtalk"
    ? { msgtype: "markdown", markdown: { title: "1688 应用流量监控", text: content } }
    : { msgtype: "markdown", markdown: { content } };
  await postJson(webhookUrl, payload, config.timeouts.notifyMs);
}

function printHelp() {
  console.log(`1688 应用流量监控

用法:
  node check-traffic.mjs
  node check-traffic.mjs --self-test

环境变量覆盖:
  MONITOR_CONFIG                 指定配置文件路径
  MONITOR_APP_KEY                覆盖 appKey
  MONITOR_APP_NAME               覆盖 appName
  MONITOR_APP_DETAIL_URL         覆盖应用详情页
  MONITOR_THRESHOLD              覆盖告警阈值
  MONITOR_BROWSER_PROFILE_DIR    覆盖浏览器登录态目录
  MONITOR_HEADLESS               true/false
  MONITOR_WEBHOOK_URL            企业微信或钉钉 webhook
  MONITOR_NOTIFY_ENABLED         true/false
`);
}

function runSelfTest() {
  const samples = [
    "应用流量：30049/1600000（单位：次/天）",
    "应用流量 300,049 / 1,600,000 单位：次/天"
  ];
  const parsed = samples.map((sample) => parseTrafficText(sample, DEFAULT_CONFIG.parse, DEFAULT_CONFIG.unit));
  const success = parsed[0]?.used === 30049
    && parsed[0]?.limit === 1600000
    && parsed[1]?.used === 300049
    && parsed[1]?.limit === 1600000;
  const result = {
    success,
    message: success ? "parser self-test passed" : "parser self-test failed",
    parsed
  };
  console.log(JSON.stringify(result, null, 2));
  process.exit(success ? 0 : 1);
}

async function main() {
  if (process.argv.includes("--help") || process.argv.includes("-h")) {
    printHelp();
    return;
  }
  if (process.argv.includes("--self-test")) {
    runSelfTest();
    return;
  }

  const config = await loadConfig();
  const result = await runBrowserCheck(config);
  await persistResult(config, result);
  await sendNotification(config, result).catch((error) => {
    console.error(`通知发送失败: ${error.message}`);
  });
  console.log(JSON.stringify(result));
  process.exit(result.code === 200 ? 0 : 1);
}

if (process.argv[1] && path.resolve(process.argv[1]) === __filename) {
  main().catch((error) => {
    const fallbackConfig = normalizeConfig(DEFAULT_CONFIG);
    const result = buildResult(fallbackConfig, 500, "runtime_error", {
      message: error.message
    });
    console.log(JSON.stringify(result));
    process.exit(1);
  });
}
