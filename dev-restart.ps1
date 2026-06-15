param(
    [switch]$Pull,
    [switch]$Install
)

$botScript = "D:\RE_Project\joblog\bot.py"
$processName = "python"
$scriptDir = "D:\RE_Project\joblog"

function Stop-Bot {
    $procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -match "joblog" -and $_.CommandLine -match "bot.py" }
    if ($procs) {
        foreach ($p in $procs) {
            Write-Host "[STOP] Killing bot PID $($p.ProcessId)..." -ForegroundColor Red
            Stop-Process -Id $p.ProcessId -Force
        }
        Start-Sleep -Seconds 1
        Write-Host "[OK] Bot stopped." -ForegroundColor Green
    } else {
        Write-Host "[INFO] No bot process found." -ForegroundColor Yellow
    }
}

function Start-Bot {
    Write-Host "[START] Starting bot..." -ForegroundColor Cyan
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "python"
    $psi.Arguments = $botScript
    $psi.WorkingDirectory = $scriptDir
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $false
    $psi.RedirectStandardOutput = $false
    $psi.RedirectStandardError = $false
    Start-Process -FilePath "python" -ArgumentList $botScript -WorkingDirectory $scriptDir -WindowStyle Normal
    Start-Sleep -Seconds 2
    Write-Host "[OK] Bot started!" -ForegroundColor Green
}

function Install-ScheduledRestart {
    $taskName = "SoloLevelingBotAutoRestart"
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -WorkingDirectory $scriptDir
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Hours 1)
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
    Write-Host "[OK] Scheduled task '$taskName' registered (every 1 hour)." -ForegroundColor Green
    Write-Host "     Bot will auto-restart and pull updates." -ForegroundColor Gray
}

# Main
Write-Host ""
Write-Host "=== SoloLeveling Bot Dev Restart ===" -ForegroundColor Cyan
Write-Host ""

Stop-Bot

if ($Pull) {
    Write-Host "[PULL] Pulling latest changes..." -ForegroundColor Cyan
    git -C $scriptDir pull
    Write-Host ""
}

Start-Bot

if ($Install) {
    Install-ScheduledRestart
}

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Green
