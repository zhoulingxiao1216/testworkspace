#!/usr/bin/env node
import fs from "node:fs/promises";
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { once } from "node:events";
import os from "node:os";
import path from "node:path";
import { loadConfig } from "./check-traffic.mjs";

function candidateChromePaths() {
  if (process.platform === "win32") {
    const localAppData = process.env.LOCALAPPDATA || "";
    const programFiles = process.env.PROGRAMFILES || "C:\\Program Files";
    const programFilesX86 = process.env["PROGRAMFILES(X86)"] || "C:\\Program Files (x86)";
    return [
      path.join(programFiles, "Google", "Chrome", "Application", "chrome.exe"),
      path.join(programFilesX86, "Google", "Chrome", "Application", "chrome.exe"),
      path.join(localAppData, "Google", "Chrome", "Application", "chrome.exe")
    ];
  }
  if (process.platform === "darwin") {
    return ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"];
  }
  return [
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser"
  ];
}

function resolveChromePath(config) {
  const explicit = process.env.MONITOR_CHROME_PATH || config.browser?.executablePath;
  if (explicit && existsSync(explicit)) {
    return explicit;
  }

  const found = candidateChromePaths().find((item) => item && existsSync(item));
  if (found) {
    return found;
  }

  throw new Error(
    "未找到 Google Chrome。请安装 Chrome，或设置环境变量 MONITOR_CHROME_PATH 指向 chrome.exe"
  );
}

async function main() {
  const config = await loadConfig();
  await fs.mkdir(config.browserProfileDir, { recursive: true });

  const chromePath = resolveChromePath(config);
  const args = [
    `--user-data-dir=${config.browserProfileDir}`,
    "--profile-directory=Default",
    "--disable-dev-shm-usage",
    "--new-window",
    config.consoleUrl
  ];
  if (process.platform !== "win32" && process.getuid?.() === 0) {
    args.unshift("--no-sandbox");
  }

  const chrome = spawn(chromePath, args, {
    detached: true,
    stdio: "ignore"
  });
  chrome.unref();

  console.log("已使用系统 Chrome 打开 1688 开放平台登录页。");
  console.log(`Chrome 路径: ${chromePath}`);
  console.log(`浏览器登录态目录: ${path.resolve(config.browserProfileDir)}`);
  console.log("");
  console.log("请在打开的 Chrome 窗口里完成人工登录。");
  console.log("登录成功并能进入控制台后，请先关闭这个 Chrome 窗口，再回到这里按 Enter。");
  console.log("关闭窗口后，后续可执行 npm run check 复用该登录态检查流量。");

  process.stdin.resume();
  await once(process.stdin, "data");

  console.log(`登录态保存目录已准备完成：${path.resolve(config.browserProfileDir)}`);
  console.log(`当前系统用户：${os.userInfo().username}`);
}

main().catch((error) => {
  console.error(`首次登录失败: ${error.message}`);
  process.exit(1);
});
