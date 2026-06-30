# -*- coding: utf-8 -*-
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ScriptArgs
)

$ErrorActionPreference = "Stop"
$ScriptDir = -join ([char[]](0x68C0, 0x6D4B, 0x767B, 0x9646, 0x811A, 0x672C))
$AppRoot = Join-Path (Join-Path $PSScriptRoot $ScriptDir) "hubbuyer_login"

Push-Location $AppRoot
try {
    & python -B ".\main.py" @ScriptArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
