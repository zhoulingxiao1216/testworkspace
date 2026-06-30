# Playwright 环境初始化脚本 (Windows 本机)
# 用途：在 Windows 本机安装 Playwright 并验证无头模式可用
# 注意：必须在 Windows 本机运行，不要在 WSL 中运行（WSL 缺少 libnspr4 等 GUI 库）

Write-Host "=== Playwright 环境初始化 ===" -ForegroundColor Cyan

# Step 1: 检查 Python
Write-Host "`n[1/4] 检查 Python 环境..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python 未安装或不在 PATH 中" -ForegroundColor Red
    exit 1
}
Write-Host "  Python 版本: $pythonVersion" -ForegroundColor Green

# Step 2: 安装 Playwright
Write-Host "`n[2/4] 安装 Playwright..." -ForegroundColor Yellow
pip install playwright --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: pip install playwright 失败" -ForegroundColor Red
    exit 1
}
Write-Host "  Playwright 已安装" -ForegroundColor Green

# Step 3: 下载 Chromium 浏览器
Write-Host "`n[3/4] 下载 Chromium 浏览器..." -ForegroundColor Yellow
playwright install chromium
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Chromium 下载失败" -ForegroundColor Red
    exit 1
}
Write-Host "  Chromium 已就绪" -ForegroundColor Green

# Step 4: 验证无头模式
Write-Host "`n[4/4] 验证无头模式..." -ForegroundColor Yellow
$testScript = @"
from playwright.sync_api import sync_playwright
p = sync_playwright().start()
b = p.chromium.launch(headless=True)
page = b.new_page()
page.goto('https://www.google.com')
print(f'Title: {page.title()}')
print(f'URL: {page.url}')
b.close()
p.stop()
print('HEADLESS_OK')
"@

$result = python -c $testScript 2>&1
if ($result -match "HEADLESS_OK") {
    Write-Host "  无头模式验证通过!" -ForegroundColor Green
    Write-Host "`n=== 环境初始化完成 ===" -ForegroundColor Cyan
} else {
    Write-Host "  无头模式验证失败:" -ForegroundColor Red
    Write-Host "  $result" -ForegroundColor Red
    exit 1
}
