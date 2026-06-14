param([ValidateSet('save','restore','status')][string]$Action = 'save')

$ProjectRoot = "D:\joblog"
$ContextFile = "$ProjectRoot\.opencode-context.json"

function Save-Context {
    $now = Get-Date
    $gitLog = git -C $ProjectRoot log --oneline -5 2>$null
    $gitStatus = git -C $ProjectRoot status --short 2>$null
    $gitBranch = git -C $ProjectRoot branch --show-current 2>$null

    $context = @{
        timestamp   = $now.ToString("yyyy-MM-dd HH:mm:ss")
        project     = $ProjectRoot
        branch      = $gitBranch
        last_commits = @($gitLog)
        uncommitted = @($gitStatus)
        env = @{
            BOT_TOKEN_PREFIX = (Get-Content "$ProjectRoot\.env" 2>$null | Select-String "BOT_TOKEN" | ForEach-Object { ($_ -split '=')[1].Substring(0, 15) + "..." } 2>$null)
        }
        bot_running = (Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*joblog*" }) -ne $null
        bot_pid     = @((Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*joblog*" } | ForEach-Object { $_.Id }))
    }
    $context | ConvertTo-Json -Depth 5 | Set-Content $ContextFile
    Write-Host ("[OK] Context saved: " + $ContextFile) -ForegroundColor Green
}

function Restore-Context {
    if (-not (Test-Path $ContextFile)) { Write-Host ("[ERROR] No context.") -ForegroundColor Red; return }
    $ctx = Get-Content $ContextFile | ConvertFrom-Json
    Write-Host "======= SOLO LEVELING CONTEXT =======" -ForegroundColor Yellow
    Write-Host ("Project: " + $ctx.project) -ForegroundColor Cyan
    Write-Host ("Saved at: " + $ctx.timestamp) -ForegroundColor Cyan
    Write-Host ("Branch: " + $ctx.branch) -ForegroundColor Cyan
    Write-Host ("Bot running: " + $ctx.bot_running) -ForegroundColor Cyan
    if ($ctx.bot_pid.Count -gt 0) { Write-Host ("PID: " + ($ctx.bot_pid -join ', ')) -ForegroundColor Cyan }
    Write-Host ""
    if ($ctx.last_commits.Count -gt 0) { Write-Host "--- Commits ---" -ForegroundColor Green; $ctx.last_commits | ForEach-Object { Write-Host ("  " + $_) } }
    Write-Host "================================" -ForegroundColor Yellow
}

function Show-Status {
    if (-not (Test-Path $ContextFile)) { Write-Host "No context." -ForegroundColor Yellow; return }
    $ctx = Get-Content $ContextFile | ConvertFrom-Json
    $botStatus = if ($ctx.bot_running) { 'Running' } else { 'Stopped' }
    Write-Host ("Last save: " + $ctx.timestamp) -ForegroundColor Green
    Write-Host ("Branch: " + $ctx.branch) -ForegroundColor Cyan
    Write-Host ("Bot: " + $botStatus) -ForegroundColor $(if($ctx.bot_running){'Green'}else{'Red'})
}

switch ($Action) {
    'save'    { Save-Context }
    'restore' { Restore-Context }
    'status'  { Show-Status }
}
