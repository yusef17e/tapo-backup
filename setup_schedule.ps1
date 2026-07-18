# ─────────────────────────────────────────────────────────────────────────────
# setup_schedule.ps1
# Run this ONCE (as Administrator) to schedule the nightly backup.
# Right-click this file → "Run with PowerShell" (or run from an Admin terminal).
# ─────────────────────────────────────────────────────────────────────────────

$TaskName   = "TapoBackup-Nightly"
$RunAt      = "21:00"   # 9:00 PM — change if needed
$ProjectDir = $PSScriptRoot  # folder where this script lives

# Find docker.exe
try {
    $DockerExe = (Get-Command docker -ErrorAction Stop).Source
} catch {
    Write-Host "ERROR: Docker not found. Install Docker Desktop first." -ForegroundColor Red
    Write-Host "Download from: https://www.docker.com/products/docker-desktop/"
    Read-Host "Press Enter to exit"
    exit 1
}

# Build the Docker image now so the first scheduled run is fast
Write-Host "Building Docker image (this may take a few minutes the first time)..."
Set-Location $ProjectDir
docker compose build
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker build failed. Check the error above." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Create the scheduled task
$Action   = New-ScheduledTaskAction `
    -Execute $DockerExe `
    -Argument "compose run --rm tapo-backup" `
    -WorkingDirectory $ProjectDir

$Trigger  = New-ScheduledTaskTrigger -Daily -At $RunAt

$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action   $Action `
    -Trigger  $Trigger `
    -Settings $Settings `
    -RunLevel Highest `
    -Force | Out-Null

Write-Host ""
Write-Host "Done! '$TaskName' will run every night at $RunAt." -ForegroundColor Green
Write-Host ""
Write-Host "To run a manual backup right now:"
Write-Host "  docker compose run --rm tapo-backup"
Write-Host ""
Read-Host "Press Enter to close"
