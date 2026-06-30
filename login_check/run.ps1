# -*- coding: utf-8 -*-
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ScriptArgs
)

$ErrorActionPreference = "Stop"
$AppRoot = Join-Path $PSScriptRoot "hubbuyer_login"

Push-Location $AppRoot
try {
    & python -B ".\main.py" @ScriptArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
