@echo off
echo =====================================================
echo  Tapo Cloud Login
echo =====================================================
echo.
echo You will be asked for your TP-Link/Tapo email
echo and password. Type them and press Enter each time.
echo If asked for a verification code, check your
echo Tapo mobile app for the 6-digit code.
echo.
cd /d "%~dp0"
python tapo-cli.py login
echo.
echo =====================================================
echo  Testing connection — listing recent clips...
echo =====================================================
echo.
python tapo-cli.py list-videos --days 2
echo.
echo If you see camera clips listed above, login worked!
echo If you see an error, check your email and password
echo and run this file again.
echo.
pause
