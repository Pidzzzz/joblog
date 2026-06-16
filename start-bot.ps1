param(
    [switch]$Install,
    [switch]$Remove
)

$BotDir = $PSScriptRoot
$ScriptName = "SoloLeveling"

function Start-Bot {
    Write-Host "[$ScriptName] Pulling latest in background..." -ForegroundColor Cyan
    Start-Job -ScriptBlock { param($dir) git -C $dir pull } -ArgumentList $BotDir | Out-Null

    $proc = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*bot.py*" -and $_.CommandLine -like "*joblog*" }
    if ($proc) {
        Write-Host "[$ScriptName] Already running (PID: $($proc.Id))" -ForegroundColor Yellow
        return
    }

    Write-Host "[$ScriptName] Starting..." -ForegroundColor Green
    $ps = Start-Process -FilePath python -ArgumentList "$BotDir\bot.py" -WindowStyle Hidden -PassThru -RedirectStandardOutput "$BotDir\stdout.log" -RedirectStandardError "$BotDir\stderr.log"
    Write-Host "[$ScriptName] Started! PID: $($ps.Id)" -ForegroundColor Green
    & "$BotDir\opencode-context.ps1" save 2>&1 | Out-Null
}

function Install-Startup {
    $startupDir = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
    if (-not (Test-Path $startupDir)) {
        New-Item -ItemType Directory -Path $startupDir -Force | Out-Null
    }
    $shortcut = "$startupDir\SoloLeveling.lnk"
    $wshell = New-Object -ComObject WScript.Shell
    $link = $wshell.CreateShortcut($shortcut)
    $link.TargetPath = "powershell.exe"
    $link.Arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$BotDir\start-bot.ps1`""
    $link.Description = "SoloLeveling Journal Bot"
    $link.WorkingDirectory = $BotDir
    $link.Save()
    Write-Host "[$ScriptName] Startup installed!" -ForegroundColor Cyan
}

function Remove-Startup {
    $shortcut = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\SoloLeveling.lnk"
    if (Test-Path $shortcut) { Remove-Item $shortcut }
    $proc = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*joblog*" }
    if ($proc) { $proc | Stop-Process; Write-Host "[$ScriptName] Stopped." -ForegroundColor Yellow }
}

if ($Install) { Install-Startup; Start-Bot }
elseif ($Remove) { Remove-Startup }
else { Start-Bot }
