param(
    [string]$SessionId = "ses_136dae94affefGygYHJqZQH184"
)

$memoryRoot = "C:\Users\USer\.local\share\mimocode\memory\sessions\$SessionId"
$backupRoot = "D:\dream"

if (!(Test-Path $memoryRoot)) {
    Write-Host "[ERROR] Session not found: $SessionId" -ForegroundColor Red
    exit 1
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = "$backupRoot\$timestamp"

New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

Copy-Item "$memoryRoot\checkpoint.md" -Destination "$backupDir\" -ErrorAction SilentlyContinue
Copy-Item "$memoryRoot\notes.md" -Destination "$backupDir\" -ErrorAction SilentlyContinue
Copy-Item "$memoryRoot\tasks" -Destination "$backupDir\tasks" -Recurse -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== Dream Saved ===" -ForegroundColor Cyan
Write-Host "Session : $SessionId" -ForegroundColor Yellow
Write-Host "Backup  : $backupDir" -ForegroundColor Green
Write-Host ""
Get-ChildItem $backupDir -Recurse | ForEach-Object {
    Write-Host "  $($_.FullName.Replace($backupDir, '.'))" -ForegroundColor Gray
}
Write-Host ""
