$ErrorActionPreference = 'Stop'
$sourceRoot = Join-Path (Split-Path $PSScriptRoot) 'hubbuyer'
$releaseRoot = Join-Path $PSScriptRoot 'hubbuyer-patrol-20260917-r1'
$files = @(
    'checker/api/add_cart.py',
    'checker/api/purchase_order_ops.py',
    'checker/api/backend_admin_checkpoint.py',
    'checker/api/purchase_order_shipping.py',
    'tests/test_add_cart_taobao.py',
    'tests/test_purchase_order_ops_genuine.py'
)
$utf8 = New-Object System.Text.UTF8Encoding($false)
foreach ($relative in $files) {
    $source = Join-Path $sourceRoot $relative
    $target = Join-Path (Join-Path $releaseRoot 'payload') $relative
    New-Item -ItemType Directory -Force -Path (Split-Path $target) | Out-Null
    Copy-Item -LiteralPath $source -Destination $target
}
$config = Get-Content -Raw -Encoding UTF8 (Join-Path $sourceRoot 'config/data/purchase_order_ops.json') | ConvertFrom-Json
$steps = [ordered]@{}
foreach ($name in @('one_click_arrival', 'one_click_genuine', 'print_sticker', 'print_hang_tag', 'print_wash', 'print_fba', 'warehouse_in')) {
    $original = $config.steps.$name
    $step = [ordered]@{
        idempotent_codes = $original.idempotent_codes
        idempotent_message_contains = $original.idempotent_message_contains
        idempotent_message_excludes = $original.idempotent_message_excludes
    }
    if ($name -eq 'one_click_genuine') {
        $step.desc = $original.desc
        $step.url = '/admin_b2b/orderDetailUpdate/updateGenuineQty'
        $step.method = 'POST'
        $step.json = @{ offline_admin_id = 0 }
        $step.payload_mode = 'single_detail'
        $step.detail_id_field = 'order_detail_id'
    }
    $steps[$name] = $step
}
[IO.File]::WriteAllText((Join-Path $releaseRoot 'config_steps.merge.json'), (@{ steps = $steps } | ConvertTo-Json -Depth 12), $utf8)
$records = @()
$packageFiles = Get-ChildItem -LiteralPath $releaseRoot -File -Recurse | Where-Object { $_.Name -ne 'manifest.json' }
foreach ($file in $packageFiles) {
    $relative = $file.FullName.Substring($releaseRoot.Length + 1).Replace('\', '/')
    if ($file.Extension -in @('.py', '.json', '.md')) {
        $content = [IO.File]::ReadAllText($file.FullName)
        if ($content -match 'eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+' -or $content -match 'qyapi\.weixin\.qq\.com/cgi-bin/webhook/send\?key=') {
            throw "Potential credential found in $relative"
        }
    }
    $records += [ordered]@{ path = $relative; bytes = $file.Length; sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant() }
}
$manifest = [ordered]@{
    release = 'hubbuyer-patrol-20260917-r1'
    scope = 'Patrol scripts only; no Global backend code or credentials'
    source_git_head = '283572eff8d67f32fb9aee5a7de6aea7a9c8102a'
    source_state = 'Working tree snapshot; not a committed release'
    files = $records
}
[IO.File]::WriteAllText((Join-Path $releaseRoot 'manifest.json'), ($manifest | ConvertTo-Json -Depth 12), $utf8)
$zipPath = "$releaseRoot.zip"
Compress-Archive -LiteralPath $releaseRoot -DestinationPath $zipPath -Force
$hash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
[IO.File]::WriteAllText("$zipPath.sha256", "$hash  $([IO.Path]::GetFileName($zipPath))`n", $utf8)
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [IO.Compression.ZipFile]::OpenRead($zipPath)
try {
    $entries = @($zip.Entries | Where-Object { $_.Name })
    if ($entries.Count -ne ($records.Count + 1)) { throw 'Unexpected archive entries' }
    foreach ($record in $records) {
        $entry = $entries | Where-Object { $_.FullName.Replace('\', '/').EndsWith('/' + $record.path) }
        if (-not $entry) { throw "Missing archive entry: $($record.path)" }
        $stream = $entry.Open()
        $sha = [Security.Cryptography.SHA256]::Create()
        try {
            $actual = ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-', '').ToLowerInvariant()
            if ($actual -ne $record.sha256) { throw "Archive hash mismatch: $($record.path)" }
        } finally { $stream.Dispose(); $sha.Dispose() }
    }
} finally { $zip.Dispose() }
Write-Output "Verified archive: $zipPath"
Write-Output "SHA256: $hash"
Write-Output "Payload files: $($files.Count); archive files: $($records.Count + 1)"
