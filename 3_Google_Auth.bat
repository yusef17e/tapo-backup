@echo off
echo =====================================================
echo  Google Drive Authorization
echo =====================================================
echo.
echo A browser window will open asking you to sign in
echo to Google. Use the same Google account that owns
echo your Drive storage.
echo.
echo You may see a warning: "Google hasn't verified this app"
echo If so, click: Advanced - then - Go to Tapo Backup (unsafe)
echo Then click Allow.
echo.
echo The browser will say "Authentication flow completed"
echo when it is done. You can close the browser tab.
echo.
cd /d "%~dp0tapo-drive-backup"
python auth_setup.py
echo.
if %errorlevel% == 0 (
    echo =====================================================
    echo  Google Drive connected successfully!
    echo  You can close this window.
    echo =====================================================
) else (
    echo =====================================================
    echo  Something went wrong. Check that:
    echo  - credentials.json is in the credentials folder
    echo  - You followed all of Step 4 in INSTRUCTIONS.txt
    echo =====================================================
)
echo.
pause
