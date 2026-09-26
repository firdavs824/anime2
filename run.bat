@echo off
chcp 65001 > nul
cd /d "%~dp0"
title Anime Telegram Bot (Avto-Qayta Ishga Tushish Rejimi)

:loop
echo ==================================================
echo         ANIME TELEGRAM BOT ISHGA TUSHMOQDA...
echo ==================================================
echo.

if exist "C:\Users\user\AppData\Local\Programs\Python\Python311\python.exe" (
    "C:\Users\user\AppData\Local\Programs\Python\Python311\python.exe" main.py
) else (
    python main.py
)

echo.
echo [!] Bot to'xtadi yoki uzilish bo'ldi. 3 soniyadan so'ng avtomatik qayta ishga tushadi...
timeout /t 3 /nobreak > nul
goto loop

