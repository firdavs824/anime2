@echo off
chcp 65001 > nul
echo ==================================================
echo         TELEGRAM BOTNI TO'XTATISH...
echo ==================================================
echo.

wmic process where "commandline like '%%main.py%%'" call terminate >nul 2>&1
taskkill /FI "WINDOWTITLE eq Anime Telegram Bot*" /F /T >nul 2>&1

echo [OK] Bot fonda to'xtatildi.
echo.
pause
