# 全球站 1688 应用流量监控

该目录是独立监控任务，按 `1688开放平台应用流量监控方案.md` 实现：首次人工登录 1688 开放平台后，后续定时任务复用 `browser-profile/` 中的浏览器登录态检查应用流量。

## 目录说明

```text
全球站流量监控/
  main.py                  # 独立巡检框架入口，参照 hubbuyer 的批量调度方式
  check-traffic.mjs        # 定时检查脚本，最后一行输出 JSON
  login-once.mjs           # 首次人工登录脚本
  core/                    # 调度、日志、通知
  checker/api/             # 巡检项适配层
  config/rules/            # 巡检任务配置
  config.json              # 默认配置，不保存账号密码/Cookie/AppSecret
  config.example.json      # 配置模板
  browser-profile/         # 运行时生成，保存登录态，不提交
  logs/                    # 运行日志、latest-result.json、失败截图
```

## 安装依赖

```powershell
cd D:\test_workspace\全球站巡检脚本\全球站流量监控
npm install
```

如果运行机没有可用 Chrome，可再执行：

```powershell
npx playwright install chromium
```

并把 `config.json` 里的 `browser.channel` 改为空字符串。

## 首次登录

```powershell
npm run login
```

脚本会直接启动本机系统 Chrome，并使用独立的 `browser-profile/` 目录保存登录态。人工登录 `https://open.1688.com/console`，确认能进入控制台后，先关闭这个 Chrome 窗口，再回到终端按 Enter。

如果登录页出现 `验证失败`、`安全验证` 等提示，不要继续自动重试；关闭窗口后重新执行 `npm run login`，优先使用扫码登录或短信登录。

如果脚本找不到 Chrome，可设置环境变量：

```powershell
$env:MONITOR_CHROME_PATH = "C:\Program Files\Google\Chrome\Application\chrome.exe"
npm run login
```

## 检查流量

推荐使用独立巡检框架入口：

```powershell
python main.py
```

也可以只跑底层 Node 检查：

```powershell
npm run check
```

检查脚本默认使用有界面 Chrome，并且不做 viewport emulation，避免 1688/淘宝登录态页面在 headless 或自动化视口下异常退出。若运行环境不允许启动可视浏览器，脚本会自动尝试一次 headless；也可以临时指定：

```powershell
$env:MONITOR_HEADLESS = "true"
npm run check
```

执行检查前必须先关闭 `npm run login` 打开的 Chrome 窗口，否则同一个 `browser-profile/` 会被占用，脚本会返回 `profile_in_use`。

脚本会访问：

```text
https://open.1688.com/develop/app/detail?appKey=9466082
```

解析页面中的 `应用流量：used/limit（单位：次/天）`，并按 `threshold=300000` 判断：

```text
used < 300000   normal
used >= 300000  warning
```

最后一行输出 JSON，便于计划任务、日志采集或后续接入现有巡检框架。

独立巡检框架会输出并记录：

```json
{
  "success": true,
  "message": "31276/1600000",
  "status_code": 200,
  "expected": "1688 应用流量低于阈值",
  "actual": "31276/1600000"
}
```

## 返回示例

正常：

```json
{"code":200,"msg":"normal","data":{"appKey":"9466082","appName":"樱花代购さくら代行","threshold":300000,"used":30049,"limit":1600000,"unit":"次/天","message":"1688 应用流量正常"}}
```

告警：

```json
{"code":200,"msg":"warning","data":{"appKey":"9466082","appName":"樱花代购さくら代行","threshold":300000,"used":320000,"limit":1600000,"unit":"次/天","message":"1688 应用流量已达到或超过 300000，请关注"}}
```

登录失效：

```json
{"code":401,"msg":"login_required","data":{"appKey":"9466082","message":"1688 登录态已失效，需要人工重新登录"}}
```

解析失败：

```json
{"code":500,"msg":"parse_failed","data":{"appKey":"9466082","message":"未能从页面解析应用流量，可能是页面结构变化或网络异常"}}
```

## Windows 计划任务

每 2 小时执行一次时，操作可配置为：

```text
程序/脚本: node
参数: D:\test_workspace\全球站巡检脚本\全球站流量监控\check-traffic.mjs
起始于: D:\test_workspace\全球站巡检脚本\全球站流量监控
```

## 宝塔/Linux 部署

服务器定时执行可以不展示浏览器，使用 `config.bt.example.json`：

```bash
cd /www/wwwroot/1688-monitor
npm install
npx playwright install --with-deps chromium
```

推荐检查命令：

```bash
npm run inspect:bt
```

带企业微信推送：

```bash
MONITOR_WEBHOOK_URL='企业微信机器人Webhook' MONITOR_NOTIFY_ENABLED=true npm run inspect:bt
```

宝塔计划任务建议每 2 小时执行：

```bash
cd /www/wwwroot/1688-monitor && MONITOR_WEBHOOK_URL='企业微信机器人Webhook' MONITOR_NOTIFY_ENABLED=true npm run inspect:bt >> logs/traffic.cron.log 2>&1
```

注意：首次登录仍需要人工完成。无桌面服务器上建议临时开 VNC/远程桌面，在目标服务器上执行一次 `npm run login` 并扫码登录；不要把 Windows 的 `browser-profile/` 直接拷到 Linux 作为正式方案，Chrome 登录态可能受系统加密机制影响而失效。

如果在 Linux 服务器上使用 root 执行 `npm run login`，脚本会自动为 Chrome 添加 `--no-sandbox`。

也可以尝试无界面扫码登录，规避 VNC：

```bash
npm run login:headless
```

脚本会持续刷新登录截图：

```text
logs/login/login-page.png
```

在宝塔文件管理中打开该图片，用手机扫码登录。登录成功后脚本会自动退出，并保存 `browser-profile/`。如果二维码过期，重新执行 `npm run login:headless`。

## 告警通知

默认不推送。需要企业微信或钉钉机器人时：

1. 设置环境变量 `MONITOR_WEBHOOK_URL`，不要把 webhook token 写进仓库。
2. 将 `config.json` 的 `notify.enabled` 改为 `true`。
3. 企业微信使用 `"type": "wecom"`，钉钉使用 `"type": "dingtalk"`。

当前本机也支持读取已忽略的本地文件：

```text
config/secrets.local.json
```

这个文件不会提交，`python main.py` 和 `npm run check` 都会读取它。

推送正文包含应用名和流量比值，例如：

```text
**樱花代购さくら代行**  应用流量：31276/1600000
```

## 敏感文件

`browser-profile/` 保存 Cookie、LocalStorage 等登录态信息，`logs/screenshots/` 可能包含后台页面截图，均已在 `.gitignore` 中排除，不能提交或外传。
