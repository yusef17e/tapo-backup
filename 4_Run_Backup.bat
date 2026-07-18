@echo off
echo =====================================================
echo  Running Tapo Backup
echo =====================================================
echo.
cd /d "%~dp0tapo-drive-backup"
python main.py
echo.
echo =====================================================
echo  Backup finished. Check your Google Drive folder
echo  to confirm the clips were uploaded.
echo  Full log is at: tapo-drive-backup\logs\backup.log
echo =====================================================
echo.
pause
