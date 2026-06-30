import { app, BrowserWindow } from 'electron';
import { spawn } from 'node:child_process';
import { request } from 'node:http';
import path from 'node:path';
import started from 'electron-squirrel-startup';

const HERMES_DASHBOARD_URL = 'http://127.0.0.1:9119/sessions';
const WSL_DISTRIBUTION = 'Ubuntu';
const HERMES_DASHBOARD_LOG = '/tmp/hermes-dashboard.log';
const HERMES_START_COMMAND =
  'cd /home/administrator/.hermes/hermes-agent && ' +
  'if [ -f .venv/bin/activate ]; then source .venv/bin/activate; fi && ' +
  `hermes dashboard --host 127.0.0.1 --port 9119 --no-open > ${HERMES_DASHBOARD_LOG} 2>&1`;
const HERMES_CHECK_TIMEOUT_MS = 1500;
const HERMES_STARTUP_TIMEOUT_MS = 60000;
const HERMES_STARTUP_POLL_MS = 1000;

let hermesStartRequested = false;

// Handle creating/removing shortcuts on Windows when installing/uninstalling.
if (started) {
  app.quit();
}

const delay = (milliseconds: number) =>
  new Promise((resolve) => {
    setTimeout(resolve, milliseconds);
  });

const escapeHtml = (value: string) =>
  value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

const loadStatusPage = async (
  mainWindow: BrowserWindow,
  title: string,
  message: string,
) => {
  const html = `
    <!doctype html>
    <html lang="zh-CN">
      <head>
        <meta charset="UTF-8" />
        <title>${escapeHtml(title)}</title>
        <style>
          :root {
            color-scheme: dark;
            font-family: "Segoe UI", Arial, sans-serif;
            background: #061512;
            color: #e4fff4;
          }

          body {
            align-items: center;
            display: flex;
            justify-content: center;
            margin: 0;
            min-height: 100vh;
          }

          main {
            border: 1px solid rgba(91, 255, 183, 0.32);
            max-width: 560px;
            padding: 32px;
          }

          h1 {
            font-size: 26px;
            letter-spacing: 0;
            margin: 0 0 14px;
          }

          p {
            color: #b6d7cb;
            font-size: 15px;
            line-height: 1.6;
            margin: 0;
          }
        </style>
      </head>
      <body>
        <main>
          <h1>${escapeHtml(title)}</h1>
          <p>${escapeHtml(message)}</p>
        </main>
      </body>
    </html>
  `;

  if (!mainWindow.isDestroyed()) {
    await mainWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`);
  }
};

const isHermesReachable = () =>
  new Promise<boolean>((resolve) => {
    const target = new URL(HERMES_DASHBOARD_URL);
    let finished = false;

    const finish = (result: boolean) => {
      if (!finished) {
        finished = true;
        resolve(result);
      }
    };

    const checkRequest = request(
      {
        hostname: target.hostname,
        method: 'GET',
        path: `${target.pathname}${target.search}`,
        port: target.port,
        timeout: HERMES_CHECK_TIMEOUT_MS,
      },
      (response) => {
        response.resume();
        finish((response.statusCode ?? 500) < 500);
      },
    );

    checkRequest.on('timeout', () => {
      checkRequest.destroy();
      finish(false);
    });
    checkRequest.on('error', () => finish(false));
    checkRequest.end();
  });

const escapePowerShellSingleQuotedString = (value: string) =>
  value.replace(/'/g, "''");

const buildHiddenWslStartCommand = () => {
  const bashCommand = HERMES_START_COMMAND.replace(/"/g, '\\"');
  const wslArgumentList = `-d ${WSL_DISTRIBUTION} -- bash -lc "${bashCommand}"`;

  return (
    "Start-Process -FilePath 'wsl.exe' " +
    `-ArgumentList '${escapePowerShellSingleQuotedString(wslArgumentList)}' ` +
    '-WindowStyle Hidden'
  );
};

const startHermesFromWsl = () => {
  if (hermesStartRequested) {
    return;
  }

  hermesStartRequested = true;

  const executable = process.platform === 'win32' ? 'powershell.exe' : 'bash';
  const args =
    process.platform === 'win32'
      ? [
          '-NoProfile',
          '-ExecutionPolicy',
          'Bypass',
          '-WindowStyle',
          'Hidden',
          '-Command',
          buildHiddenWslStartCommand(),
        ]
      : ['-lc', HERMES_START_COMMAND];

  const child = spawn(executable, args, {
    stdio: 'ignore',
    windowsHide: true,
  });

  child.on('error', (error) => {
    console.error('Failed to start Hermes from WSL:', error);
  });
};

const loadHermesDashboard = async (mainWindow: BrowserWindow) => {
  if (await isHermesReachable()) {
    await mainWindow.loadURL(HERMES_DASHBOARD_URL);
    return;
  }

  await loadStatusPage(
    mainWindow,
    '正在启动 Hermes...',
    '正在通过 WSL 启动 Hermes Dashboard，请稍等。',
  );
  startHermesFromWsl();

  const startedAt = Date.now();
  while (Date.now() - startedAt < HERMES_STARTUP_TIMEOUT_MS) {
    if (mainWindow.isDestroyed()) {
      return;
    }

    if (await isHermesReachable()) {
      await mainWindow.loadURL(HERMES_DASHBOARD_URL);
      return;
    }

    await delay(HERMES_STARTUP_POLL_MS);
  }

  await loadStatusPage(
    mainWindow,
    'Hermes 启动失败',
    '请确认 WSL 中可以执行：cd /home/administrator/.hermes/hermes-agent && source .venv/bin/activate && hermes dashboard',
  );
};

const createWindow = () => {
  // Create the browser window.
  const mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    title: 'Hermes Desktop',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  loadHermesDashboard(mainWindow).catch((error) => {
    console.error('Failed to load Hermes Dashboard:', error);
  });
};

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.on('ready', createWindow);

// Quit when all windows are closed, except on macOS. There, it's common
// for applications and their menu bar to stay active until the user quits
// explicitly with Cmd + Q.
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  // On OS X it's common to re-create a window in the app when the
  // dock icon is clicked and there are no other windows open.
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// In this file you can include the rest of your app's specific main process
// code. You can also put them in separate files and import them here.
