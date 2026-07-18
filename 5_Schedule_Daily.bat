@echo off
echo =====================================================
echo  Schedule Daily Backup at 9:00 PM
echo =====================================================
echo.
echo This will set up the backup to run automatically
echo every day at 9:00 PM.
echo.
set "RUNNER=%~dp0_run_backup_scheduled.bat"
schtasks /create /tn "TapoDriveBackup" /tr "\"%RUNNER%\"" /sc daily /st 21:00 /f
echo.
if %errorlevel% == 0 (
    echo =====================================================
    echo  SUCCESS! The backup is now scheduled to run
    echo  automatically every day at 9:00 PM.
    echo.
    echo  IMPORTANT: Do not move the TapoBackup folder
    echo  after this — the scheduled task points to its
    echo  current location.
    echo =====================================================
) else (
    echo =====================================================
    echo  ERROR: Could not create the scheduled task.
    echo  Close this window, then right-click this file
    echo  and choose "Run as administrator", and try again.
    echo =====================================================
)
echo.
pause
