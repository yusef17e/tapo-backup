@echo off
echo =====================================================
echo  Installing required Python packages...
echo =====================================================
echo.
cd /d "%~dp0tapo-drive-backup"
python -m pip install -r requirements.txt
echo.
if %errorlevel% == 0 (
    echo =====================================================
    echo  Done! All packages installed successfully.
    echo  You can close this window.
    echo =====================================================
) else (
    echo =====================================================
    echo  ERROR: Something went wrong.
    echo  Make sure Python is installed and "Add to PATH"
    echo  was checked during installation.
    echo  Then try right-clicking this file and choosing
    echo  "Run as administrator".
    echo =====================================================
)
echo.
pause
