@echo off
title GRS Inventory App - LAN Server
echo ========================================================
echo        Starting GRS Inventory App on LAN Server
echo ========================================================
echo.

:: Get IPv4 address
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    set IP=%%a
)
:: Trim leading space
set IP=%IP: =%

echo Your LAN Server Address:
echo http://%IP%:8000
echo http://localhost:8000
echo.
echo Leave this window OPEN while running the application.
echo To stop the server, press Ctrl+C or close this window.
echo ========================================================
echo.

python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
