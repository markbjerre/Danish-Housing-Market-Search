<#
.SYNOPSIS
    One morning update for the Copenhagen apartment monitor.

.DESCRIPTION
    Fetches listings, rescores, asks Claude about anything new or repriced,
    sends instant alerts, then sends the morning digest.

    Everything is logged to kbh/data/logs. That is the point of this wrapper
    rather than pointing Task Scheduler straight at the module: a scheduled run
    has no console and nobody watching, so a failure that prints to stderr and
    dies would look exactly like a quiet market.

    Exit codes: 0 all good, 1 the run failed, 2 the run worked but the digest
    did not. The digest is deliberately non-fatal, because fresh data with no
    summary is a far better outcome than neither.

.NOTES
    The AI verdicts shell out to the claude CLI. That works under Task
    Scheduler only because kbh/ai.py resolves the npm .cmd shim to the real
    executable: a cmd.exe started from a process with no console never hands
    off to its child, so it would hang forever rather than fail. Do not
    "simplify" that resolution away.
#>

[CmdletBinding()]
param(
    # Skip the model entirely. Useful for a cheap test that the plumbing works.
    [switch]$NoAi,
    # Fetch and score but send nothing to Telegram.
    [switch]$NoAlerts
)

$ErrorActionPreference = 'Continue'

$ProjectDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Python = Join-Path $ProjectDir '.venv\Scripts\python.exe'
$LogDir = Join-Path $ProjectDir 'kbh\data\logs'

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
}

$LogFile = Join-Path $LogDir ("kbh-" + (Get-Date -Format 'yyyy-MM-dd') + ".log")

# Appending has to survive another process holding the file open, which is not
# hypothetical: a `tail` on the log was enough to make Add-Content fail. With
# ErrorActionPreference at Continue that failure is swallowed, so the run
# completed, exited 0, and wrote not one line. A scheduled job whose log can
# quietly vanish is worse than no log, because it reads as "never ran".
function Write-Log {
    param([string]$Message)
    $line = "{0}  {1}{2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message, [Environment]::NewLine
    for ($attempt = 1; $attempt -le 5; $attempt++) {
        try {
            [System.IO.File]::AppendAllText($LogFile, $line, [System.Text.Encoding]::UTF8)
            return
        } catch {
            Start-Sleep -Milliseconds (50 * $attempt)
        }
    }
    # Out of retries. Say so somewhere rather than losing the line silently.
    $fallback = [System.IO.Path]::ChangeExtension($LogFile, '.fallback.log')
    try {
        [System.IO.File]::AppendAllText($fallback, $line, [System.Text.Encoding]::UTF8)
    } catch {
        Write-Output "LOGGING FAILED: $Message"
    }
}

Write-Log "=== daily update starting ==="
Write-Log "project: $ProjectDir"

if (-not (Test-Path $Python)) {
    Write-Log "FATAL: no interpreter at $Python"
    exit 1
}

# --- The run itself -------------------------------------------------------

$runArgs = @('-m', 'kbh.pipeline', 'run')
if ($NoAi) { $runArgs += '--no-ai' }
if ($NoAlerts) { $runArgs += '--no-alerts' }
Write-Log ("running: python " + ($runArgs -join ' '))

Push-Location $ProjectDir
try {
    & $Python @runArgs 2>&1 | ForEach-Object { Write-Log $_ }
    $runExit = $LASTEXITCODE
} finally {
    Pop-Location
}

if ($runExit -ne 0) {
    Write-Log "FAILED: run exited $runExit, skipping the digest"
    exit 1
}
Write-Log "run finished cleanly"

# --- The digest -----------------------------------------------------------
# Non-fatal on purpose. If Telegram is down, the data is still fresh and the
# web app still works, and that is worth more than a red exit code.

if ($NoAlerts) {
    Write-Log "digest skipped because -NoAlerts was passed"
    Write-Log "=== daily update done ==="
    exit 0
}

Push-Location $ProjectDir
try {
    & $Python -m kbh.pipeline digest 2>&1 | ForEach-Object { Write-Log $_ }
    $digestExit = $LASTEXITCODE
} finally {
    Pop-Location
}

if ($digestExit -ne 0) {
    Write-Log "WARNING: digest exited $digestExit, but the data is fresh"
    Write-Log "=== daily update done, with a failed digest ==="
    exit 2
}

Write-Log "=== daily update done ==="

# --- Housekeeping ---------------------------------------------------------
# Keep a month of logs. Enough to see a pattern, not enough to be a problem.

Get-ChildItem -Path $LogDir -Filter 'kbh-*.log' |
    Sort-Object LastWriteTime -Descending |
    Select-Object -Skip 30 |
    Remove-Item -Force -ErrorAction SilentlyContinue

exit 0
