[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("agent1", "agent2", "agent1_test_design", "agent2_test_execution")]
    [string]$Agent = "agent1",

    [string]$AgentRoot,

    [string]$WorkspaceRoot,

    [switch]$NoTranscript
)

$ErrorActionPreference = "Stop"

if (-not $AgentRoot) {
    $AgentRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
else {
    $AgentRoot = (Resolve-Path -LiteralPath $AgentRoot).Path
}

if (-not $WorkspaceRoot) {
    $WorkspaceRoot = (Split-Path -Parent $AgentRoot)
}
else {
    $WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
}

$AgentMap = @{
    agent1 = @{
        ShortName = "agent1"
        RoleId = "agent1_test_design"
        DisplayName = "Agent 1 / Test Architect"
        Role = "test_design"
        MemoryDir = "memory\agent1-test-design"
        Skill = "skills\test-design\SKILL.md"
        Workflow = "workflows\kickoff_test_engine.md"
    }
    agent1_test_design = @{
        ShortName = "agent1"
        RoleId = "agent1_test_design"
        DisplayName = "Agent 1 / Test Architect"
        Role = "test_design"
        MemoryDir = "memory\agent1-test-design"
        Skill = "skills\test-design\SKILL.md"
        Workflow = "workflows\kickoff_test_engine.md"
    }
    agent2 = @{
        ShortName = "agent2"
        RoleId = "agent2_test_execution"
        DisplayName = "Agent 2 / Test Runner"
        Role = "test_execution"
        MemoryDir = "memory\agent2-test-execution"
        Skill = "skills\test-execution\SKILL.md"
        Workflow = "workflows\run_test_suite.md"
    }
    agent2_test_execution = @{
        ShortName = "agent2"
        RoleId = "agent2_test_execution"
        DisplayName = "Agent 2 / Test Runner"
        Role = "test_execution"
        MemoryDir = "memory\agent2-test-execution"
        Skill = "skills\test-execution\SKILL.md"
        Workflow = "workflows\run_test_suite.md"
    }
}

$Profile = $AgentMap[$Agent]
$ShortName = $Profile.ShortName
$SessionRoot = Join-Path $AgentRoot "runtime\vscode-sessions\$ShortName"
$LogsRoot = Join-Path $SessionRoot "logs"
$MemoryRoot = Join-Path $AgentRoot $Profile.MemoryDir
$ExchangeRoot = Join-Path $AgentRoot "memory\exchange"
$RunsRoot = Join-Path $AgentRoot "runs"
$SkillPath = Join-Path $AgentRoot $Profile.Skill
$WorkflowPath = Join-Path $AgentRoot $Profile.Workflow

New-Item -ItemType Directory -Force -Path $SessionRoot, $LogsRoot | Out-Null

$SessionPath = Join-Path $SessionRoot "SESSION.md"
$InboxPath = Join-Path $SessionRoot "inbox.md"
$HandoffPath = Join-Path $SessionRoot "handoff.md"

function Initialize-AgentFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        Set-Content -LiteralPath $Path -Encoding UTF8 -Value $Content
    }
}

$SessionTemplate = @"
# $($Profile.DisplayName) VS Code Long-Term Session

## Identity

- Short name: $ShortName
- Role id: $($Profile.RoleId)
- Role: $($Profile.Role)
- Workspace root: $WorkspaceRoot
- Agent root: $AgentRoot
- Role memory: $MemoryRoot
- Exchange memory: $ExchangeRoot
- Runs: $RunsRoot
- Skill: $SkillPath
- Workflow: $WorkflowPath

## Current Objective

Awaiting assignment.

## Working Notes

Use this file for durable terminal/session context. Put reusable project facts into the role memory files only when they are stable and safe to store.
"@

Initialize-AgentFile -Path $SessionPath -Content $SessionTemplate
Initialize-AgentFile -Path $InboxPath -Content "# $ShortName Inbox`n`nNo pending VS Code terminal tasks yet."
Initialize-AgentFile -Path $HandoffPath -Content "# $ShortName Handoff`n`nNo handoff yet."

$env:AGENT_HOME = $AgentRoot
$env:CODEX_LONG_AGENT = $ShortName
$env:CODEX_LONG_AGENT_ROLE = $Profile.RoleId
$env:CODEX_LONG_SESSION_ROOT = $SessionRoot
$env:CODEX_LONG_WORKSPACE = $WorkspaceRoot
$env:CODEX_LONG_MEMORY_ROOT = $MemoryRoot
$env:CODEX_LONG_EXCHANGE_ROOT = $ExchangeRoot
$env:CODEX_LONG_RUNS_ROOT = $RunsRoot

Set-Location -LiteralPath $WorkspaceRoot

$TranscriptPath = $null
if (-not $NoTranscript) {
    $TranscriptPath = Join-Path $LogsRoot ("terminal-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".txt")
    try {
        Start-Transcript -Path $TranscriptPath -Append | Out-Null
    }
    catch {
        Write-Warning "Could not start transcript: $($_.Exception.Message)"
    }
}

$env:CODEX_LONG_TRANSCRIPT = $TranscriptPath

function global:Add-AgentEntry {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FileName,

        [Parameter(Mandatory = $true)]
        [string]$Heading,

        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Text
    )

    $Message = ($Text -join " ").Trim()
    if (-not $Message) {
        Write-Host "No text provided."
        return
    }

    $Path = Join-Path $env:CODEX_LONG_SESSION_ROOT $FileName
    $Entry = @(
        ""
        "## $Heading - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        $Message
    )

    Add-Content -LiteralPath $Path -Encoding UTF8 -Value $Entry
    Write-Host "Saved to $Path"
}

function global:agent-note {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Text)
    Add-AgentEntry -FileName "SESSION.md" -Heading "Note" @Text
}

function global:agent-inbox {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Text)
    Add-AgentEntry -FileName "inbox.md" -Heading "Task" @Text
}

function global:agent-handoff {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Text)
    Add-AgentEntry -FileName "handoff.md" -Heading "Handoff" @Text
}

function global:agent-status {
    Write-Host "Agent:      $env:CODEX_LONG_AGENT"
    Write-Host "Role:       $env:CODEX_LONG_AGENT_ROLE"
    Write-Host "Workspace:  $env:CODEX_LONG_WORKSPACE"
    Write-Host "Agent home: $env:AGENT_HOME"
    Write-Host "Session:    $(Join-Path $env:CODEX_LONG_SESSION_ROOT 'SESSION.md')"
    Write-Host "Inbox:      $(Join-Path $env:CODEX_LONG_SESSION_ROOT 'inbox.md')"
    Write-Host "Handoff:    $(Join-Path $env:CODEX_LONG_SESSION_ROOT 'handoff.md')"
    Write-Host "Memory:     $env:CODEX_LONG_MEMORY_ROOT"
    Write-Host "Exchange:   $env:CODEX_LONG_EXCHANGE_ROOT"
    Write-Host "Runs:       $env:CODEX_LONG_RUNS_ROOT"
    Write-Host "Transcript: $env:CODEX_LONG_TRANSCRIPT"
}

function global:stop-agent-transcript {
    try {
        Stop-Transcript | Out-Null
        Write-Host "Transcript stopped."
    }
    catch {
        Write-Warning "No active transcript to stop."
    }
}

function global:prompt {
    $LocationName = Split-Path -Leaf (Get-Location)
    "[$env:CODEX_LONG_AGENT $LocationName] PS> "
}

Write-Host ""
Write-Host "Long-term VS Code session ready: $($Profile.DisplayName)"
Write-Host "Agent home:   $AgentRoot"
Write-Host "Session root: $SessionRoot"
Write-Host "Transcript:   $TranscriptPath"
Write-Host ""
Write-Host "Helpers: agent-note, agent-inbox, agent-handoff, agent-status, stop-agent-transcript"
Write-Host ""
